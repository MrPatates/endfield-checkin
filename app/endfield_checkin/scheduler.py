"""Background loop: check every CHECK_INTERVAL minutes, retry sooner after errors.

Checking the status is a single light request per role, and it makes the bot
independent of the exact reset time of each server region.
"""

from __future__ import annotations

import logging
import random
import threading
import time

from .service import CheckinService

log = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, service: CheckinService, interval_s: float, retry_s: float, startup_delay_s: float):
        self.service = service
        self.interval_s = interval_s
        self.retry_s = retry_s
        self.startup_delay_s = startup_delay_s
        self.next_run: float | None = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._pending_all = False
        self._pending_ids: set[str] = set()
        self._thread = threading.Thread(target=self._loop, name="scheduler", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def trigger(self, account_id: str | None = None) -> None:
        """Run now, for one account or (None) for all of them."""
        with self._lock:
            if account_id is None:
                self._pending_all = True
            else:
                self._pending_ids.add(account_id)
        self._wake.set()

    def _next_delay(self, transient: bool) -> float:
        if transient:
            return self.retry_s
        return self.interval_s * random.uniform(0.95, 1.05)

    def _loop(self) -> None:
        scheduled_at = time.time() + self.startup_delay_s
        while not self._stop.is_set():
            self.next_run = scheduled_at
            self._wake.wait(max(0.0, scheduled_at - time.time()))
            if self._stop.is_set():
                break
            self._wake.clear()
            with self._lock:
                run_all, ids = self._pending_all, set(self._pending_ids)
                self._pending_all, self._pending_ids = False, set()
            due = time.time() >= scheduled_at - 0.5
            try:
                if due or run_all:
                    summary = self.service.run(None, reason="schedule" if due else "manual")
                    scheduled_at = time.time() + self._next_delay(summary.transient)
                elif ids:
                    summary = self.service.run(ids, reason="manual")
                    if summary.transient:
                        scheduled_at = min(scheduled_at, time.time() + self.retry_s)
            except Exception:  # never let the loop die
                log.exception("scheduler run failed")
                scheduled_at = time.time() + self.retry_s
        self.next_run = None
