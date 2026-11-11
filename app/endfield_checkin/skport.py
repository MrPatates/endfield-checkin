"""Minimal client for the SKPORT attendance API used by Arknights: Endfield.

Authentication flow (same as the official web page):

1. ACCOUNT_TOKEN (browser cookie, or email/password login)
2. POST as.gryphline.com/user/oauth2/v2/grant           -> one-time OAuth code
3. POST zonai.skport.com/web/v1/user/auth/generate_cred_by_code -> cred + sign token
4. GET  zonai.skport.com/api/v1/game/player/binding     -> game roles (sk-game-role)
5. GET  zonai.skport.com/web/v1/game/endfield/attendance -> status (hasToday)
6. POST zonai.skport.com/web/v1/game/endfield/attendance -> claim

Requests to zonai are signed: md5(hmac_sha256(sign_token, path + query|body +
timestamp + '{"platform":..,"timestamp":..,"dId":..,"vName":..}')).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_AS_BASE = "https://as.gryphline.com"
DEFAULT_ZONAI_BASE = "https://zonai.skport.com"

SKPORT_APP_CODE = "6eb76d4e13aa36e6"
ENDFIELD_GAME_ID = "3"
PLATFORM = "3"
VNAME = "1.0.0"

LOGIN_PATH = "/user/auth/v1/token_by_email_password"
GRANT_PATH = "/user/oauth2/v2/grant"
CRED_PATH = "/web/v1/user/auth/generate_cred_by_code"
REFRESH_PATH = "/web/v1/auth/refresh"
BINDING_PATH = "/api/v1/game/player/binding"
ATTENDANCE_PATH = "/web/v1/game/endfield/attendance"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# zonai codes meaning "cred / sign token no longer valid".
SESSION_CODES = {10000, 10002, 10003}
# zonai code returned by the attendance POST when today's reward was already taken.
ALREADY_CODE = 10001
ICON_PREFIX = "https://static.skport.com/"


class SkportError(Exception):
    """Temporary problem (network, server, unexpected answer): retry later."""

    kind = "api_error"

    def __init__(self, message: str, *, kind: str | None = None):
        super().__init__(message)
        if kind:
            self.kind = kind


class NetworkError(SkportError):
    kind = "network"


class SessionExpired(SkportError):
    """The cred / sign token was rejected; a fresh login usually fixes it."""

    kind = "session_expired"


class AccountError(SkportError):
    """Needs user action: rejected token, wrong password, no Endfield role..."""

    kind = "token_rejected"


@dataclass
class Session:
    cred: str
    sign_token: str


@dataclass
class Role:
    key: str  # "<gameId>_<roleId>_<serverId>", sent as the sk-game-role header
    nickname: str = ""
    server: str = ""
    level: int | None = None


@dataclass
class ClaimResult:
    already: bool
    rewards: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


def compute_sign(path: str, query_or_body: str, timestamp: str, sign_token: str,
                 platform: str = PLATFORM, vname: str = VNAME, device_id: str = "") -> str:
    header = json.dumps(
        {"platform": platform, "timestamp": timestamp, "dId": device_id, "vName": vname},
        separators=(",", ":"),
    )
    source = f"{path}{query_or_body}{timestamp}{header}"
    digest = hmac.new(sign_token.encode(), source.encode(), hashlib.sha256).hexdigest()
    return hashlib.md5(digest.encode()).hexdigest()


def normalize_token(raw: Any) -> str:
    """Accept a pasted cookie value, "ACCOUNT_TOKEN=..." or a URL-encoded value."""
    token = str(raw or "").strip().strip('"').strip("'").strip()
    if token.upper().startswith("ACCOUNT_TOKEN="):
        token = token.split("=", 1)[1].split(";", 1)[0].strip()
    if "%" in token:
        token = urllib.parse.unquote(token)
    return "".join(token.split())


def reward_name(name: Any) -> str:
    # Some names hold variants separated by "|" ("Talosian Credit Notes|T-Creds").
    return str(name or "").split("|", 1)[0].strip()


def resource_view(info: Any) -> dict[str, Any] | None:
    if not isinstance(info, dict):
        return None
    icon = info.get("icon")
    return {
        "name": reward_name(info.get("name")) or str(info.get("id") or "?"),
        "count": info.get("count") if isinstance(info.get("count"), int) else None,
        "icon": icon if isinstance(icon, str) and icon.startswith(ICON_PREFIX) else None,
    }


def rewards_from_claim(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    resources = data.get("resourceInfoMap") or {}
    rewards = []
    for award in data.get("awardIds") or []:
        award_id = award.get("id") if isinstance(award, dict) else award
        view = resource_view(resources.get(award_id)) if isinstance(resources, dict) else None
        if view:
            rewards.append(view)
        elif award_id:
            rewards.append({"name": str(award_id), "count": None, "icon": None})
    return rewards


class SkportClient:
    def __init__(self, language: str = "en", as_base: str = DEFAULT_AS_BASE,
                 zonai_base: str = DEFAULT_ZONAI_BASE, timeout: float = 30):
        self.language = language
        self.as_base = as_base.rstrip("/")
        self.zonai_base = zonai_base.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ HTTP
    def _request(self, method: str, url: str, headers: dict[str, str] | None = None,
                 body: Any = None, raw_body: bytes | None = None) -> tuple[int, Any]:
        all_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://game.skport.com",
            "Referer": "https://game.skport.com/",
        }
        all_headers.update(headers or {})
        data = raw_body
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode()
        if data is not None:
            all_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=all_headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            with exc:
                status, raw = exc.code, exc.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise NetworkError(f"{urllib.parse.urlsplit(url).netloc}: {reason}") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            payload = None
        log.debug("%s %s -> HTTP %s", method, urllib.parse.urlsplit(url).path, status)
        return status, payload

    @staticmethod
    def _message(payload: Any, status: int) -> str:
        if isinstance(payload, dict):
            for key in ("msg", "message"):
                if payload.get(key):
                    return str(payload[key])
        return f"HTTP {status}"

    # ------------------------------------------------------------ account auth
    def login(self, email: str, password: str) -> str:
        """Email/password login on Gryphline; returns an ACCOUNT_TOKEN."""
        status, payload = self._request("POST", self.as_base + LOGIN_PATH,
                                        body={"email": email, "password": password})
        if status >= 500 or status == 429 or not isinstance(payload, dict):
            raise SkportError(f"login: {self._message(payload, status)}")
        token = (payload.get("data") or {}).get("token") if payload.get("status") == 0 else None
        if not token:
            raise AccountError(f"login refused: {self._message(payload, status)}", kind="login_failed")
        return token

    def grant_code(self, account_token: str) -> str:
        status, payload = self._request(
            "POST", self.as_base + GRANT_PATH,
            body={"token": account_token, "appCode": SKPORT_APP_CODE, "type": 0},
        )
        if status >= 500 or status == 429 or not isinstance(payload, dict):
            raise SkportError(f"grant: {self._message(payload, status)}")
        code = (payload.get("data") or {}).get("code") if payload.get("status") == 0 else None
        if not code:
            raise AccountError(f"account token rejected: {self._message(payload, status)}")
        return code

    def generate_cred(self, code: str) -> Session:
        status, payload = self._request("POST", self.zonai_base + CRED_PATH,
                                        body={"kind": 1, "code": code})
        data = payload.get("data") if isinstance(payload, dict) and payload.get("code") == 0 else None
        if not isinstance(data, dict) or not data.get("cred"):
            raise SkportError(f"generate_cred: {self._message(payload, status)}")
        sign_token = data.get("token") or self.refresh_sign_token(data["cred"])
        return Session(cred=data["cred"], sign_token=sign_token)

    def refresh_sign_token(self, cred: str) -> str:
        headers = {"cred": cred, "platform": PLATFORM, "vName": VNAME,
                   "timestamp": str(int(time.time())), "sk-language": self.language}
        status, payload = self._request("GET", self.zonai_base + REFRESH_PATH, headers=headers)
        token = (payload.get("data") or {}).get("token") if isinstance(payload, dict) and payload.get("code") == 0 else None
        if not token:
            raise SkportError(f"auth refresh: {self._message(payload, status)}")
        return token

    def open_session(self, account_token: str) -> Session:
        return self.generate_cred(self.grant_code(account_token))

    # --------------------------------------------------------- signed requests
    def _signed(self, session: Session, method: str, path: str, role: str | None = None) -> dict[str, Any]:
        timestamp = str(int(time.time()))
        headers = {
            "cred": session.cred,
            "platform": PLATFORM,
            "vName": VNAME,
            "timestamp": timestamp,
            "sk-language": self.language,
            "sign": compute_sign(path, "", timestamp, session.sign_token),
        }
        if role:
            headers["sk-game-role"] = role
        status, payload = self._request(method, self.zonai_base + path, headers=headers,
                                        raw_body=b"" if method == "POST" else None)
        code = payload.get("code") if isinstance(payload, dict) else None
        if status == 401 or code in SESSION_CODES:
            raise SessionExpired(f"session rejected: {self._message(payload, status)}")
        if not isinstance(payload, dict):
            raise SkportError(f"{path}: unexpected answer (HTTP {status})")
        return payload

    def get_roles(self, session: Session) -> list[Role]:
        payload = self._signed(session, "GET", BINDING_PATH)
        if payload.get("code") != 0:
            raise SkportError(f"binding: {self._message(payload, 0)}")
        roles: dict[str, Role] = {}
        for app in (payload.get("data") or {}).get("list") or []:
            if not isinstance(app, dict) or app.get("appCode") != "endfield":
                continue
            for binding in app.get("bindingList") or []:
                if not isinstance(binding, dict):
                    continue
                candidates = list(binding.get("roles") or [])
                if isinstance(binding.get("defaultRole"), dict):
                    candidates.append(binding["defaultRole"])
                for item in candidates:
                    if not isinstance(item, dict):
                        continue
                    role_id, server_id = item.get("roleId"), item.get("serverId")
                    if role_id in (None, "") or server_id in (None, ""):
                        continue
                    key = f"{ENDFIELD_GAME_ID}_{role_id}_{server_id}"
                    if key in roles:
                        continue
                    level = item.get("level")
                    roles[key] = Role(
                        key=key,
                        nickname=str(item.get("nickname") or item.get("nickName") or ""),
                        server=str(item.get("serverName") or server_id),
                        level=level if isinstance(level, int) else None,
                    )
        return list(roles.values())

    def get_status(self, session: Session, role: str) -> dict[str, Any]:
        payload = self._signed(session, "GET", ATTENDANCE_PATH, role)
        if payload.get("code") != 0 or not isinstance(payload.get("data"), dict):
            raise SkportError(f"attendance status: {self._message(payload, 0)}")
        return payload["data"]

    def claim(self, session: Session, role: str) -> ClaimResult:
        payload = self._signed(session, "POST", ATTENDANCE_PATH, role)
        code = payload.get("code")
        message = self._message(payload, 0)
        if code == 0:
            return ClaimResult(already=False, rewards=rewards_from_claim(payload.get("data")), message=message)
        lowered = message.lower()
        if code == ALREADY_CODE or "already" in lowered or "again" in lowered or "重复" in message:
            return ClaimResult(already=True, message=message)
        raise SkportError(f"attendance claim: {message} (code {code})")
