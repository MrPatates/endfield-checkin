"""Entry point: python -m endfield_checkin [--once]."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading

from . import __version__
from .config import Settings
from .notify import Notifier
from .scheduler import Scheduler
from .service import CheckinService
from .skport import SkportClient
from .store import Store
from .web import WebApp, make_server

log = logging.getLogger("endfield_checkin")


def drop_privileges(settings: Settings) -> None:
    """Started as root (Docker default): own /config files as PUID:PGID, then switch user."""
    if os.name != "posix" or os.getuid() != 0:
        return
    if settings.puid == 0:
        log.warning("PUID=0: running as root")
        return
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    owned = [settings.data_dir] + [p for p in settings.data_dir.iterdir()
                                   if p.name.startswith(("accounts.json", "state.json"))]
    for path in owned:
        try:
            os.lchown(path, settings.puid, settings.pgid)
        except OSError as exc:
            log.warning("cannot chown %s: %s", path, exc)
    os.setgroups([])
    os.setgid(settings.pgid)
    os.setuid(settings.puid)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="endfield-checkin")
    parser.add_argument("--once", action="store_true", help="check every account once, then exit")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level if level in ("DEBUG", "INFO", "WARNING", "ERROR") else "INFO",
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    settings = Settings.from_env()
    os.umask(0o077)
    drop_privileges(settings)

    store = Store(settings.data_dir, settings.env_tokens, settings.env_account_name)
    store.prune_state()
    client = SkportClient(settings.language, settings.as_base, settings.zonai_base)
    notifier = Notifier(settings.discord_webhook, settings.notify, settings.notification_language)
    service = CheckinService(store, client, notifier)
    accounts = store.list_accounts()
    log.info("Endfield Check-in %s: %d account(s), check every %d min, uid %d",
             __version__, len(accounts), settings.check_interval_min, os.getuid())

    if args.once:
        summary = service.run(reason="once")
        return 0 if all(outcome == "ok" for outcome in summary.outcomes.values()) else 1

    scheduler = Scheduler(service, settings.check_interval_min * 60, settings.retry_interval_min * 60,
                          settings.startup_delay_s)
    server = make_server(WebApp(settings, store, service, scheduler, client))

    def stop(signum: int, _frame: object) -> None:
        log.info("signal %d received, stopping", signum)
        scheduler.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    scheduler.start()
    log.info("web UI listening on port %d%s", settings.port,
             "" if accounts else " - open it to connect your SKPORT account")
    server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
