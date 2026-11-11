import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from endfield_checkin import skport  # noqa: E402
from endfield_checkin.skport import (AccountError, SkportClient, compute_sign,  # noqa: E402
                                     normalize_token, resource_view, rewards_from_claim)

from fake_skport import VALID_TOKEN, FakeSkport  # noqa: E402

FIXTURE = json.loads((Path(__file__).with_name("fixtures") / "attendance_status.json").read_text())

NODE_SIGN = """
const crypto = require("crypto");
const [path, ts, key] = process.argv.slice(1);
const src = path + "" + ts + JSON.stringify({platform: "3", timestamp: ts, dId: "", vName: "1.0.0"});
const h = crypto.createHmac("sha256", key).update(src).digest("hex");
process.stdout.write(crypto.createHash("md5").update(h).digest("hex"));
"""


class SignTest(unittest.TestCase):
    def test_known_vector(self):
        # Reference value computed with the JavaScript implementation used by the web page.
        self.assertEqual(
            compute_sign("/web/v1/game/endfield/attendance", "", "1794426889", "sign-token-éxample"),
            "b8b8925d7faa0716ae8d070dc59b5391",
        )

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_matches_node_implementation(self):
        for path, ts, key in [("/api/v1/game/player/binding", "1700000000", "abc"),
                              ("/web/v1/game/endfield/attendance", "1794426889", "x" * 64)]:
            node = subprocess.run(["node", "-e", NODE_SIGN, path, ts, key], capture_output=True, text=True, check=True)
            self.assertEqual(compute_sign(path, "", ts, key), node.stdout)


class HelpersTest(unittest.TestCase):
    def test_normalize_token(self):
        self.assertEqual(normalize_token("  abc+/=  "), "abc+/=")
        self.assertEqual(normalize_token('"abc%2B%2F%3D"'), "abc+/=")
        self.assertEqual(normalize_token("ACCOUNT_TOKEN=abc%3D; Path=/"), "abc=")
        self.assertEqual(normalize_token("ab\ncd"), "abcd")
        self.assertEqual(normalize_token(None), "")

    def test_resource_view_from_real_answer(self):
        info = FIXTURE["data"]["resourceInfoMap"]["endfield_attendance_7_2000"]
        view = resource_view(info)
        self.assertEqual(view["name"], "Talosian Credit Notes")
        self.assertEqual(view["count"], 2000)
        self.assertTrue(view["icon"].startswith("https://static.skport.com/"))
        self.assertIsNone(resource_view({"id": "x", "icon": "https://evil.example/x.png"})["icon"])

    def test_rewards_from_claim(self):
        data = {"awardIds": [{"id": "endfield_attendance_8_80"}, {"id": "unknown"}],
                "resourceInfoMap": FIXTURE["data"]["resourceInfoMap"]}
        rewards = rewards_from_claim(data)
        self.assertEqual(rewards[0]["name"], "Oroberyl")
        self.assertEqual(rewards[0]["count"], 80)
        self.assertEqual(rewards[1]["name"], "unknown")
        self.assertEqual(rewards_from_claim(None), [])


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = FakeSkport()

    @classmethod
    def tearDownClass(cls):
        cls.fake.close()

    def client(self):
        return SkportClient("en", self.fake.url, self.fake.url, timeout=5)

    def test_full_flow(self):
        client = self.client()
        session = client.open_session(VALID_TOKEN)
        roles = client.get_roles(session)
        self.assertEqual([r.key for r in roles], ["3_4605473178_2"])
        self.assertEqual(roles[0].nickname, "Endmin")
        status = client.get_status(session, roles[0].key)
        self.assertFalse(status["hasToday"])
        result = client.claim(session, roles[0].key)
        self.assertFalse(result.already)
        self.assertEqual(result.rewards[0]["count"], 2)
        self.assertTrue(client.claim(session, roles[0].key).already)
        self.assertTrue(client.get_status(session, roles[0].key)["hasToday"])

    def test_bad_token_and_login(self):
        client = self.client()
        with self.assertRaises(AccountError):
            client.open_session("bm9wZQ==")
        with self.assertRaises(AccountError) as ctx:
            client.login("user@example.com", "wrong")
        self.assertEqual(ctx.exception.kind, "login_failed")
        self.assertEqual(client.login("user@example.com", "secret"), VALID_TOKEN)

    def test_network_error(self):
        client = SkportClient("en", "http://127.0.0.1:9", "http://127.0.0.1:9", timeout=2)
        with self.assertRaises(skport.NetworkError):
            client.open_session(VALID_TOKEN)


if __name__ == "__main__":
    unittest.main()
