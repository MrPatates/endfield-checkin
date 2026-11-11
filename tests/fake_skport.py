"""In-process fake of the SKPORT / Gryphline endpoints used by the bot."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from endfield_checkin.skport import SKPORT_APP_CODE, compute_sign  # noqa: E402

FIXTURE = json.loads((Path(__file__).with_name("fixtures") / "attendance_status.json").read_text())
VALID_TOKEN = "dGhpcy1pcy1hLXZhbGlkLWFjY291bnQtdG9rZW4="


class FakeSkport:
    def __init__(self):
        self.tokens = {VALID_TOKEN}
        self.users = {"user@example.com": ("secret", VALID_TOKEN)}
        self.roles = [{"roleId": "4605473178", "serverId": "2", "nickname": "Endmin", "level": 42, "serverName": "Asia"}]
        self.codes: set[str] = set()
        self.creds: dict[str, str] = {}  # cred -> sign token
        self.claimed: set[str] = set()  # sk-game-role keys claimed "today"
        self.calls: dict[str, int] = {}
        self.fail_attendance = 0  # number of next attendance calls answering HTTP 500
        self.lock = threading.Lock()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def expire_creds(self):
        with self.lock:
            self.creds.clear()

    def new_day(self):
        with self.lock:
            self.claimed.clear()

    def count(self, name: str) -> int:
        return self.calls.get(name, 0)

    # ------------------------------------------------------------------
    def _handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, payload, status=200):
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                return json.loads(raw) if raw else {}

            def _count(self, name):
                with fake.lock:
                    fake.calls[name] = fake.calls.get(name, 0) + 1

            def _check_sign(self, path):
                cred = self.headers.get("cred", "")
                sign_token = fake.creds.get(cred)
                if not sign_token:
                    self._reply({"code": 10002, "message": "user not logged in"})
                    return False
                expected = compute_sign(path, "", self.headers.get("timestamp", ""), sign_token,
                                        self.headers.get("platform", ""), self.headers.get("vName", ""))
                if self.headers.get("sign") != expected:
                    self._reply({"code": 10003, "message": "sign error"})
                    return False
                return True

            def do_POST(self):
                path = self.path
                body = self._body()
                if path == "/user/auth/v1/token_by_email_password":
                    self._count("login")
                    user = fake.users.get(body.get("email"))
                    if user and user[0] == body.get("password"):
                        return self._reply({"status": 0, "msg": "OK", "data": {"token": user[1]}})
                    return self._reply({"status": 104, "msg": "Login failed. Incorrect email address or password.", "type": "C1"})
                if path == "/user/oauth2/v2/grant":
                    self._count("grant")
                    if body.get("appCode") != SKPORT_APP_CODE or body.get("type") != 0:
                        return self._reply({"status": 1, "msg": "bad app"})
                    if body.get("token") not in fake.tokens:
                        return self._reply({"status": 3, "msg": "Login status has expired", "type": "A"})
                    code = f"code-{fake.count('grant')}"
                    fake.codes.add(code)
                    return self._reply({"status": 0, "type": "A", "msg": "OK", "data": {"code": code, "uid": "1"}})
                if path == "/web/v1/user/auth/generate_cred_by_code":
                    self._count("cred")
                    code = body.get("code")
                    if body.get("kind") != 1 or code not in fake.codes:
                        return self._reply({"code": 10001, "message": "Server desertion"})
                    fake.codes.discard(code)
                    cred, sign_token = f"cred-{code}", f"sign-{code}"
                    fake.creds[cred] = sign_token
                    return self._reply({"code": 0, "message": "OK", "data": {"cred": cred, "token": sign_token, "userId": "1"}})
                if path == "/web/v1/game/endfield/attendance":
                    self._count("claim")
                    if fake.fail_attendance:
                        fake.fail_attendance -= 1
                        return self._reply({"message": "boom"}, 500)
                    if not self._check_sign(path):
                        return
                    role = self.headers.get("sk-game-role", "")
                    if role in fake.claimed:
                        return self._reply({"code": 10001, "message": "Please do not sign in again"})
                    fake.claimed.add(role)
                    return self._reply({"code": 0, "message": "OK", "data": {
                        "awardIds": [{"id": "endfield_attendance_1_2", "type": 1}],
                        "resourceInfoMap": {"endfield_attendance_1_2": FIXTURE["data"]["resourceInfoMap"]["endfield_attendance_1_2"]},
                    }})
                self._reply({"message": "not found"}, 404)

            def do_GET(self):
                path = self.path
                if path == "/api/v1/game/player/binding":
                    self._count("binding")
                    if not self._check_sign(path):
                        return
                    return self._reply({"code": 0, "message": "OK", "data": {"list": [
                        {"appCode": "arknights", "bindingList": [{"roles": [{"roleId": "1", "serverId": "1"}]}]},
                        {"appCode": "endfield", "bindingList": [{"uid": "u1", "gameId": 3, "roles": fake.roles,
                                                                 "defaultRole": fake.roles[0] if fake.roles else None}]},
                    ]}})
                if path == "/web/v1/game/endfield/attendance":
                    self._count("status")
                    if fake.fail_attendance:
                        fake.fail_attendance -= 1
                        return self._reply({"message": "boom"}, 500)
                    if not self._check_sign(path):
                        return
                    role = self.headers.get("sk-game-role", "")
                    data = json.loads(json.dumps(FIXTURE["data"]))
                    done = role in fake.claimed
                    data["hasToday"] = done
                    data["calendar"][0]["done"] = done
                    data["calendar"][0]["available"] = not done
                    return self._reply({"code": 0, "message": "OK", "data": data})
                self._reply({"message": "not found"}, 404)

        return Handler
