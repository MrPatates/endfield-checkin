"""Small web UI and JSON API (standard library only)."""

from __future__ import annotations

import base64
import hmac
import json
import logging
import os
import re
import secrets
import socket
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import __version__
from .config import Settings
from .scheduler import Scheduler
from .service import CheckinService, nickname_label
from .skport import AccountError, SkportClient, SkportError, normalize_token
from .store import Store

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).with_name("static")
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
                ".json": "application/json; charset=utf-8"}
ROLE_RE = re.compile(r"\d+_\d+_\d+")
MAX_BODY = 16 * 1024
CSP = ("default-src 'self'; img-src 'self' https://static.skport.com; style-src 'self'; "
       "script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")


class ApiError(Exception):
    def __init__(self, status: int, error: str, detail: str = ""):
        super().__init__(error)
        self.status, self.error, self.detail = status, error, detail


class WebApp:
    def __init__(self, settings: Settings, store: Store, service: CheckinService,
                 scheduler: Scheduler, client: SkportClient):
        self.settings = settings
        self.store = store
        self.service = service
        self.scheduler = scheduler
        self.client = client
        self.csrf = secrets.token_urlsafe(32)
        self.static = {}
        for path in STATIC_DIR.rglob("*"):  # e.g. "app.js", "lang/fr_FR.json"
            if path.is_file() and path.suffix in STATIC_TYPES:
                key = path.relative_to(STATIC_DIR).as_posix()
                self.static[key] = (path.read_bytes(), STATIC_TYPES[path.suffix])

    # --------------------------------------------------------------- views
    def public_state(self) -> dict[str, Any]:
        accounts = []
        for account in self.store.list_accounts():
            token = account.get("account_token") or ""
            accounts.append({
                "id": account["id"],
                "name": account["name"],
                "source": account.get("source", "web"),
                "token_hint": "…" + token[-4:] if len(token) > 8 else "…",
                "auto_relogin": bool(account.get("email") and account.get("password")),
                "role_override": account.get("role_override") or "",
                "created": account.get("created"),
                "state": self.store.get_state(account["id"]),
            })
        settings = self.settings
        return {
            "version": __version__,
            "csrf": self.csrf,
            "now": time.time(),
            "timezone": os.environ.get("TZ") or time.strftime("%Z"),
            "running": self.service.running,
            "next_run": self.scheduler.next_run,
            "settings": {
                "check_interval": settings.check_interval_min,
                "retry_interval": settings.retry_interval_min,
                "language": settings.language,
                "ui_language": settings.ui_language,
                "notify": settings.notify if settings.discord_webhook else "none",
                "discord": bool(settings.discord_webhook),
                "password_protected": bool(settings.webui_password),
            },
            "accounts": accounts,
            "history": self.store.history(50),
        }

    # ------------------------------------------------------------- actions
    def add_account(self, body: dict[str, Any]) -> dict[str, Any]:
        name = " ".join(str(body.get("name") or "").split())[:60]
        method = body.get("method")
        role = str(body.get("role") or "").strip()
        if role and not ROLE_RE.fullmatch(role):
            raise ApiError(400, "invalid_role")
        email = password = None
        try:
            if method == "password":
                email = str(body.get("email") or "").strip()
                password = str(body.get("password") or "")
                if not email or not password:
                    raise ApiError(400, "missing_fields")
                token = self.client.login(email, password)
                if not body.get("remember"):
                    email = password = None
            elif method == "token":
                token = normalize_token(body.get("token"))
                if len(token) < 16:
                    raise ApiError(400, "missing_token")
            else:
                raise ApiError(400, "bad_request")
            if self.store.has_token(token):
                raise ApiError(409, "duplicate")
            session = self.client.open_session(token)  # validates the token before saving it
        except AccountError as exc:
            raise ApiError(400, exc.kind, str(exc)) from exc
        except SkportError as exc:
            raise ApiError(502, exc.kind, str(exc)) from exc
        auto_name = not name
        if auto_name and not role:
            try:  # name the account after its in-game nickname(s)
                name = nickname_label([r.nickname for r in self.client.get_roles(session)])
            except SkportError as exc:
                log.debug("nickname lookup failed: %s", exc)
        if not name:
            name = f"Account {len(self.store.list_accounts()) + 1}"
        account = self.store.add_account(name, token, email, password, role, auto_name=auto_name)
        self.store.add_event("added", account["name"])
        log.info("account %r added (%s)", account["name"], method)
        self.scheduler.trigger(account["id"])
        return {"id": account["id"]}

    def delete_account(self, account_id: str) -> dict[str, Any]:
        account = self.store.get_account(account_id)
        if not account:
            raise ApiError(404, "not_found")
        if account.get("source") == "env":
            raise ApiError(400, "env_account")
        self.store.delete_account(account_id)
        self.service.forget(account_id)
        self.store.add_event("removed", account["name"])
        log.info("account %r removed", account["name"])
        return {"ok": True}

    def run_now(self, body: dict[str, Any]) -> dict[str, Any]:
        account_id = body.get("account_id")
        if account_id is not None and not self.store.get_account(str(account_id)):
            raise ApiError(404, "not_found")
        self.scheduler.trigger(str(account_id) if account_id else None)
        return {"ok": True}

    def check_password(self, header: str) -> bool:
        if not self.settings.webui_password:
            return True
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False
        password = decoded.partition(":")[2]
        return hmac.compare_digest(password.encode(), self.settings.webui_password.encode())


def make_handler(app: WebApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "EndfieldCheckin"
        sys_version = ""

        def log_message(self, fmt: str, *args: Any) -> None:
            log.debug("%s - %s", self.address_string(), fmt % args)

        # ---------------------------------------------------------- output
        def _send(self, status: int, body: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, payload: Any) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def _guard(self) -> bool:
            if app.check_password(self.headers.get("Authorization", "")):
                return True
            time.sleep(0.5)  # slow down password guessing
            self._send(HTTPStatus.UNAUTHORIZED, b"Authentication required", "text/plain; charset=utf-8",
                       {"WWW-Authenticate": 'Basic realm="Endfield Check-in", charset="UTF-8"'})
            return False

        # ---------------------------------------------------------- routes
        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path == "/healthz":
                return self._send(200, b"ok", "text/plain; charset=utf-8")
            if not self._guard():
                return
            if path in ("/", "/index.html"):
                return self._send(200, *app.static["index.html"])
            if path.startswith("/static/") and path[8:] in app.static:
                return self._send(200, *app.static[path[8:]])
            if path == "/api/state":
                return self._json(200, app.public_state())
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if not self._guard():
                return
            try:
                body = self._read_body()
                path = urllib.parse.urlsplit(self.path).path
                if path == "/api/accounts":
                    return self._json(201, app.add_account(body))
                match = re.fullmatch(r"/api/accounts/([A-Za-z0-9-]{1,40})/delete", path)
                if match:
                    return self._json(200, app.delete_account(match.group(1)))
                if path == "/api/run":
                    return self._json(202, app.run_now(body))
                raise ApiError(404, "not_found")
            except ApiError as exc:
                self._json(exc.status, {"error": exc.error, "detail": exc.detail})

        def _read_body(self) -> dict[str, Any]:
            origin = self.headers.get("Origin")
            if origin and urllib.parse.urlsplit(origin).netloc != self.headers.get("Host"):
                raise ApiError(403, "bad_origin")
            if not hmac.compare_digest(self.headers.get("X-CSRF-Token", "").encode(), app.csrf.encode()):
                raise ApiError(403, "bad_csrf")
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                raise ApiError(415, "json_required")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 <= length <= MAX_BODY:
                raise ApiError(413, "too_large")
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError as exc:
                raise ApiError(400, "bad_json") from exc
            if not isinstance(body, dict):
                raise ApiError(400, "bad_json")
            return body

    return Handler


class DualStackServer(ThreadingHTTPServer):
    """Listens on IPv6 and IPv4 at once (port mappings may forward either)."""

    address_family = socket.AF_INET6
    daemon_threads = True

    def server_bind(self) -> None:
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def make_server(app: WebApp, host: str | None = None) -> ThreadingHTTPServer:
    handler = make_handler(app)
    if host is None:
        try:
            return DualStackServer(("::", app.settings.port), handler)
        except OSError as exc:  # IPv6 disabled in the container
            log.debug("IPv6 unavailable (%s), listening on IPv4 only", exc)
            host = "0.0.0.0"
    server = ThreadingHTTPServer((host, app.settings.port), handler)
    server.daemon_threads = True
    return server
