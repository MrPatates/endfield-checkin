import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from endfield_checkin.scheduler import Scheduler  # noqa: E402
from endfield_checkin.service import RunSummary  # noqa: E402


class StubService:
    def __init__(self, outcomes=("ok",)):
        self.calls = []
        self.outcomes = list(outcomes)
        self.event = threading.Event()

    def run(self, account_ids=None, reason="schedule"):
        self.calls.append((account_ids, reason))
        outcome = self.outcomes.pop(0) if self.outcomes else "ok"
        self.event.set()
        return RunSummary({"a": outcome})

    def wait(self, count, timeout=3):
        deadline = time.time() + timeout
        while len(self.calls) < count and time.time() < deadline:
            time.sleep(0.01)
        return len(self.calls) >= count


class SchedulerTest(unittest.TestCase):
    def test_startup_run_then_interval(self):
        service = StubService()
        scheduler = Scheduler(service, interval_s=3600, retry_s=900, startup_delay_s=0.05)
        scheduler.start()
        self.assertTrue(service.wait(1))
        time.sleep(0.05)
        self.assertEqual(service.calls, [(None, "schedule")])
        self.assertGreater(scheduler.next_run - time.time(), 3600 * 0.9)
        scheduler.stop()

    def test_transient_error_uses_retry_delay(self):
        service = StubService(outcomes=("transient",))
        scheduler = Scheduler(service, interval_s=3600, retry_s=0.05, startup_delay_s=0)
        scheduler.start()
        self.assertTrue(service.wait(2))
        scheduler.stop()

    def test_manual_triggers(self):
        service = StubService()
        scheduler = Scheduler(service, interval_s=3600, retry_s=900, startup_delay_s=3600)
        scheduler.start()
        planned = None
        for _ in range(100):
            planned = scheduler.next_run
            if planned:
                break
            time.sleep(0.01)
        scheduler.trigger("acc1")
        self.assertTrue(service.wait(1))
        self.assertEqual(service.calls[0], ({"acc1"}, "manual"))
        time.sleep(0.05)
        self.assertEqual(scheduler.next_run, planned, "single-account run keeps the schedule")
        scheduler.trigger()
        self.assertTrue(service.wait(2))
        self.assertEqual(service.calls[1], (None, "manual"))
        scheduler.stop()


if __name__ == "__main__":
    unittest.main()
