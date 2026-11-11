import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from endfield_checkin.config import Settings  # noqa: E402
from endfield_checkin.notify import Notifier  # noqa: E402
from endfield_checkin.scheduler import Scheduler  # noqa: E402
from endfield_checkin.service import CheckinService  # noqa: E402
from endfield_checkin.skport import SkportClient  # noqa: E402
from endfield_checkin.store import Store  # noqa: E402
from endfield_checkin.web import WebApp, make_server  # noqa: E402

from fake_skport import VALID_TOKEN, FakeSkport  # noqa: E402

ENV_TOKEN = "ZW52LXRva2VuLWZyb20tdGVtcGxhdGU="


class WebTest(unittest.TestCase):
    password = ""

    def setUp(self):
        self.fake = FakeSkport()
        self.fake.tokens.add(ENV_TOKEN)
        self.tmp = tempfile.TemporaryDirectory()
        settings = Settings(data_dir=Path(self.tmp.name), port=0, webui_password=self.password,
                            as_base=self.fake.url, zonai_base=self.fake.url)
        self.store = Store(settings.data_dir, (ENV_TOKEN,), "Template")
        client = SkportClient("en", self.fake.url, self.fake.url, timeout=5)
        self.service = CheckinService(self.store, client, Notifier("", "none"))
        self.scheduler = Scheduler(self.service, 3600, 900, 3600)
        self.server = make_server(WebApp(settings, self.store, self.service, self.scheduler, client), "127.0.0.1")
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.fake.close()
        self.tmp.cleanup()

    def request(self, path, body=None, csrf=True, headers=None, auth=True):
        hdrs = dict(headers or {})
        if auth and self.password:
            hdrs["Authorization"] = "Basic " + base64.b64encode(f"admin:{self.password}".encode()).decode()
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
            if csrf:
                hdrs["X-CSRF-Token"] = self.csrf()
        req = urllib.request.Request(self.base + path, data=data, headers=hdrs, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read(), exc.headers

    def csrf(self):
        return json.loads(self.request("/api/state")[1])["csrf"]


class WebAppTest(WebTest):
    def test_static_and_headers(self):
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"/static/app.js", body)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        for name in ("app.js", "style.css", "icon.svg"):
            self.assertEqual(self.request(f"/static/{name}")[0], 200)
        self.assertEqual(self.request("/static/../web.py")[0], 404)
        for name in ("i18n.js", "lang/languages.json", "lang/fr_FR.json"):
            status, _, headers = self.request(f"/static/{name}")
            self.assertEqual(status, 200, name)
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(self.request("/static/lang/../app.js")[0], 404)
        self.assertEqual(json.loads(self.request("/api/state")[1])["settings"]["ui_language"], "auto")
        self.assertEqual(self.request("/healthz")[1], b"ok")

    def test_add_account_flow_and_no_secret_leak(self):
        status, body, _ = self.request("/api/accounts", {"method": "token", "name": "Main", "token": VALID_TOKEN})
        self.assertEqual(status, 201, body)
        status, body, _ = self.request("/api/accounts", {"method": "token", "token": VALID_TOKEN})
        self.assertEqual((status, json.loads(body)["error"]), (409, "duplicate"))
        status, body, _ = self.request("/api/accounts", {"method": "token", "token": "aW52YWxpZC10b2tlbi12YWx1ZQ=="})
        self.assertEqual((status, json.loads(body)["error"]), (400, "token_rejected"))
        status, body, _ = self.request("/api/accounts", {"method": "password", "email": "user@example.com",
                                                         "password": "wrong"})
        self.assertEqual((status, json.loads(body)["error"]), (400, "login_failed"))
        status, body, _ = self.request("/api/accounts", {"method": "token", "token": VALID_TOKEN, "role": "x"})
        self.assertEqual((status, json.loads(body)["error"]), (400, "invalid_role"))

        self.service.run()
        status, body, _ = self.request("/api/state")
        state = json.loads(body)
        self.assertEqual([a["name"] for a in state["accounts"]], ["Template", "Main"])
        # Both accounts share the fake's single character: the first run claims, the second sees it done.
        self.assertEqual([a["state"]["status"] for a in state["accounts"]], ["claimed", "done"])
        for secret in (VALID_TOKEN, ENV_TOKEN, "cred-", "sign-"):
            self.assertNotIn(secret.encode(), body)

    def test_account_named_after_in_game_nickname(self):
        status, body, _ = self.request("/api/accounts", {"method": "token", "token": VALID_TOKEN})
        self.assertEqual(status, 201, body)
        account = self.store.get_account(json.loads(body)["id"])
        self.assertEqual((account["name"], account["auto_name"]), ("Endmin", True))
        self.store.delete_account(account["id"])
        status, body, _ = self.request("/api/accounts", {"method": "token", "token": VALID_TOKEN, "role": "3_1_2"})
        account = self.store.get_account(json.loads(body)["id"])
        self.assertEqual(account["name"], "Account 2", "no nickname lookup with a manual role")

    def test_password_login_not_stored_unless_asked(self):
        status, _, _ = self.request("/api/accounts", {"method": "password", "email": "user@example.com",
                                                      "password": "secret"})
        self.assertEqual(status, 201)
        stored = (Path(self.tmp.name) / "accounts.json").read_text()
        self.assertNotIn("secret", stored)
        self.assertIn(VALID_TOKEN, stored)

    def test_csrf_and_content_type(self):
        self.assertEqual(self.request("/api/run", {}, csrf=False)[0], 403)
        status, _, _ = self.request("/api/run", {}, headers={"Content-Type": "text/plain", "X-CSRF-Token": self.csrf()})
        self.assertEqual(status, 415)
        status, _, _ = self.request("/api/run", {}, headers={"Origin": "http://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.request("/api/run", {})[0], 202)

    def test_env_account_cannot_be_deleted(self):
        account_id = self.store.list_accounts()[0]["id"]
        status, body, _ = self.request(f"/api/accounts/{account_id}/delete", {})
        self.assertEqual((status, json.loads(body)["error"]), (400, "env_account"))
        self.assertEqual(self.request("/api/accounts/nope/delete", {})[0], 404)


class PasswordTest(WebTest):
    password = "hunter2"

    def test_basic_auth(self):
        self.assertEqual(self.request("/", auth=False)[0], 401)
        self.assertEqual(self.request("/api/state", auth=False)[0], 401)
        self.assertEqual(self.request("/healthz", auth=False)[0], 200)
        self.assertEqual(self.request("/")[0], 200)


if __name__ == "__main__":
    unittest.main()
