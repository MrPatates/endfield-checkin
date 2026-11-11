"""Optional Discord webhook notifications."""

from __future__ import annotations

import datetime as dt
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

LANG_DIR = Path(__file__).with_name("static") / "lang"


def discord_text(language: str) -> dict[str, str]:
    """Discord strings for an Unraid locale code, falling back to English per key."""
    def load(code: str) -> dict[str, Any]:
        try:
            data = json.loads((LANG_DIR / f"{code}.json").read_text(encoding="utf-8")).get("discord")
        except (OSError, ValueError, AttributeError):
            return {}
        return data if isinstance(data, dict) else {}

    text = load("en_US")
    if language != "en_US" and "/" not in language:
        for key, value in load(language).items():
            if key in text and isinstance(value, str) and value.strip():
                text[key] = value
    return text


def format_rewards(rewards: list[dict[str, Any]], empty: str) -> str:
    parts = [f"{r['name']} x{r['count']}" if r.get("count") else r["name"] for r in rewards]
    return ", ".join(parts) or empty


class Notifier:
    def __init__(self, webhook: str, mode: str = "all", language: str = "en_US", timeout: float = 15):
        self.webhook = webhook
        self.mode = mode
        self.text = discord_text(language)
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.webhook) and self.mode != "none"

    def claimed(self, account: str, roles: list[dict[str, Any]]) -> None:
        if not self.enabled or self.mode != "all":
            return
        fields = []
        for role in roles:
            label = " · ".join(x for x in (role.get("nickname"), role.get("server")) if x) or account
            value = f"{self.text['rewards']}: {format_rewards(role.get('rewards') or [], self.text['none'])}"
            if role.get("total"):
                value += f"\n{self.text['progress']}: {role.get('done', 0)}/{role['total']}"
            fields.append({"name": label[:256], "value": value[:1024], "inline": False})
        self._send(f"✅ {self.text['claimed']} — {account}", None, 0x57F287, fields)

    def error(self, account: str, message: str, action_required: bool) -> None:
        if not self.enabled:
            return
        title = self.text["action"] if action_required else self.text["error"]
        self._send(f"⚠️ {title} — {account}", message, 0xED4245, [])

    def recovered(self, account: str) -> None:
        if not self.enabled:
            return
        self._send(f"🔁 {self.text['recovered']} — {account}", None, 0x5865F2, [])

    def _send(self, title: str, description: str | None, color: int, fields: list[dict[str, Any]]) -> None:
        embed: dict[str, Any] = {
            "title": title[:256],
            "color": color,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "footer": {"text": "Endfield Check-in"},
        }
        if description:
            embed["description"] = description[:2000]
        if fields:
            embed["fields"] = fields[:25]
        payload = json.dumps({"username": "Endfield Check-in", "embeds": [embed]}).encode()
        request = urllib.request.Request(
            self.webhook, data=payload, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "endfield-checkin"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout):
                pass
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log.warning("Discord notification failed: %s", getattr(exc, "reason", exc))
