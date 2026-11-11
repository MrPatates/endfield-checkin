import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from endfield_checkin.notify import Notifier  # noqa: E402
from endfield_checkin.service import CheckinService  # noqa: E402
from endfield_checkin.skport import SkportClient  # noqa: E402
from endfield_checkin.store import Store  # noqa: E402

from fake_skport import VALID_TOKEN, FakeSkport  # noqa: E402


class RecordingNotifier(Notifier):
    def __init__(self):
        super().__init__("https://example.invalid/webhook", "all")
        self.sent = []

    def _send(self, title, description, color, fields):
        self.sent.append(title)


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSkport()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.notifier = RecordingNotifier()
        self.service = CheckinService(self.store, SkportClient("en", self.fake.url, self.fake.url, timeout=5), self.notifier)

    def tearDown(self):
        self.fake.close()
        self.tmp.cleanup()

    def test_claims_once_per_day(self):
        account = self.store.add_account("Main", VALID_TOKEN)
        summary = self.service.run()
        self.assertEqual(summary.outcomes, {account["id"]: "ok"})
        state = self.store.get_state(account["id"])
        self.assertEqual(state["status"], "claimed")
        self.assertEqual(state["roles"][0]["done"], 1)
        self.assertEqual(state["roles"][0]["total"], 30)
        self.assertEqual(len(state["roles"][0]["first"]), 3)
        self.assertEqual(state["last_rewards"][0]["rewards"][0]["name"], "Intermediate Combat Record")
        self.assertIn("endfield_attendance_7_3000", state["resources"])
        self.assertEqual(self.fake.count("claim"), 1)
        self.assertEqual(len(self.notifier.sent), 1)

        self.service.run()  # same day: status only, no second claim
        self.assertEqual(self.fake.count("claim"), 1)
        self.assertEqual(self.store.get_state(account["id"])["status"], "done")
        self.assertEqual(self.fake.count("grant"), 1, "session is cached between runs")

        self.fake.new_day()
        self.service.run()
        self.assertEqual(self.fake.count("claim"), 2)
        self.assertEqual([e["code"] for e in self.store.history()], ["claimed", "claimed"])

    def test_session_expiry_relogs(self):
        self.store.add_account("Main", VALID_TOKEN)
        self.service.run()
        self.fake.expire_creds()
        self.fake.new_day()
        summary = self.service.run()
        self.assertEqual(list(summary.outcomes.values()), ["ok"])
        self.assertEqual(self.fake.count("grant"), 2)
        self.assertEqual(self.fake.count("claim"), 2)

    def test_rejected_token_needs_action_and_notifies_once(self):
        account = self.store.add_account("Old", "b2xkLXRva2Vu")
        for _ in range(3):
            summary = self.service.run()
        self.assertEqual(summary.outcomes[account["id"]], "action")
        self.assertFalse(summary.transient)
        state = self.store.get_state(account["id"])
        self.assertEqual((state["status"], state["kind"]), ("action_required", "token_rejected"))
        self.assertEqual(len(self.notifier.sent), 1)
        self.assertEqual(len(self.store.history()), 1)

    def test_saved_password_renews_token(self):
        account = self.store.add_account("Pw", "ZXhwaXJlZA==", "user@example.com", "secret")
        summary = self.service.run()
        self.assertEqual(summary.outcomes[account["id"]], "ok")
        self.assertEqual(self.fake.count("login"), 1)
        self.assertEqual(self.store.get_account(account["id"])["account_token"], VALID_TOKEN)

    def test_server_error_is_transient_then_recovers(self):
        account = self.store.add_account("Main", VALID_TOKEN)
        self.fake.fail_attendance = 1
        summary = self.service.run()
        self.assertTrue(summary.transient)
        self.assertEqual(self.store.get_state(account["id"])["status"], "error")
        summary = self.service.run()
        self.assertFalse(summary.transient)
        self.assertEqual(self.store.get_state(account["id"])["status"], "claimed")
        self.assertEqual([e["code"] for e in self.store.history()], ["recovered", "claimed", "error"])

    def test_multiple_roles_and_no_role(self):
        self.fake.roles.append({"roleId": "77", "serverId": "3", "nickname": "Alt", "serverName": "Americas/Europe"})
        account = self.store.add_account("Main", VALID_TOKEN)
        self.service.run()
        state = self.store.get_state(account["id"])
        self.assertEqual([r["key"] for r in state["roles"]], ["3_4605473178_2", "3_77_3"])
        self.assertEqual(self.fake.claimed, {"3_4605473178_2", "3_77_3"})

        self.fake.roles.clear()
        self.service.forget(account["id"])
        self.service.run()
        self.assertEqual(self.store.get_state(account["id"])["kind"], "no_role")

    def test_role_override_skips_binding(self):
        self.store.add_account("Main", VALID_TOKEN, role_override="3_999_2")
        self.service.run()
        self.assertEqual(self.fake.count("binding"), 0)
        self.assertEqual(self.fake.claimed, {"3_999_2"})

    def test_env_accounts_and_persistence(self):
        store = Store(Path(self.tmp.name), (VALID_TOKEN,), "Unraid")
        account = store.list_accounts()[0]
        self.assertEqual((account["name"], account["source"]), ("Unraid", "env"))
        self.assertFalse(store.delete_account(account["id"]))
        web = store.add_account("Web", "d2Vi")
        reloaded = Store(Path(self.tmp.name))
        self.assertEqual([a["id"] for a in reloaded.list_accounts()], [web["id"]])
        self.assertEqual((Path(self.tmp.name) / "accounts.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
