"""Settings read from environment variables (set in the Unraid template)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .skport import DEFAULT_AS_BASE, DEFAULT_ZONAI_BASE

log = logging.getLogger(__name__)

LANGUAGES = ("en", "fr_FR", "de_DE", "it_IT", "es_MX", "pt_BR", "ru_RU",
             "ja", "ko", "zh_Hans", "zh_Hant", "id_ID", "th_TH", "vi_VN")
NOTIFY_MODES = ("all", "errors", "none")
# Interface languages: the locales offered by Unraid (static/lang/languages.json).
LANG_DIR = Path(__file__).with_name("static") / "lang"
UI_LANGUAGES = tuple(json.loads((LANG_DIR / "languages.json").read_text(encoding="utf-8")))
# Discord notifications follow UI_LANGUAGE, or the reward language when the UI is on "auto".
SKPORT_TO_UI = {"en": "en_US", "fr_FR": "fr_FR", "de_DE": "de_DE", "it_IT": "it_IT", "es_MX": "es_ES",
                "pt_BR": "pt_BR", "ru_RU": "ru_RU", "ja": "ja_JA", "ko": "ko_KO", "zh_Hans": "zh_CN",
                "zh_Hant": "zh_TW"}


def _int(env: Mapping[str, str], name: str, default: int, low: int, high: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        log.warning("%s=%r is not a number, using %s", name, raw, default)
        return default
    if not low <= value <= high:
        log.warning("%s=%s out of range [%s-%s], clamped", name, value, low, high)
    return max(low, min(high, value))


def _choice(env: Mapping[str, str], name: str, default: str, choices: tuple[str, ...]) -> str:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    for choice in choices:
        if raw.lower() == choice.lower():
            return choice
    log.warning("%s=%r is not one of %s, using %s", name, raw, ", ".join(choices), default)
    return default


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("/config")
    port: int = 8080
    check_interval_min: int = 120
    retry_interval_min: int = 15
    startup_delay_s: int = 15
    language: str = "en"
    ui_language: str = "auto"
    discord_webhook: str = ""
    notify: str = "all"
    webui_password: str = ""
    env_tokens: tuple[str, ...] = ()
    env_account_name: str = ""
    puid: int = 99
    pgid: int = 100
    log_level: str = "INFO"
    as_base: str = DEFAULT_AS_BASE
    zonai_base: str = DEFAULT_ZONAI_BASE

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        webhook = env.get("DISCORD_WEBHOOK", "").strip()
        if webhook and not webhook.startswith("https://"):
            log.warning("DISCORD_WEBHOOK must start with https:// - notifications disabled")
            webhook = ""
        tokens = tuple(t.strip() for t in env.get("ACCOUNT_TOKEN", "").split(",") if t.strip())
        return cls(
            data_dir=Path(env.get("DATA_DIR", "/config")),
            port=_int(env, "WEBUI_PORT", 8080, 1, 65535),
            check_interval_min=_int(env, "CHECK_INTERVAL", 120, 30, 720),
            retry_interval_min=_int(env, "RETRY_INTERVAL", 15, 5, 240),
            startup_delay_s=_int(env, "STARTUP_DELAY", 15, 0, 3600),
            language=_choice(env, "SKPORT_LANGUAGE", "en", LANGUAGES),
            ui_language=_choice(env, "UI_LANGUAGE", "auto", ("auto",) + UI_LANGUAGES),
            discord_webhook=webhook,
            notify=_choice(env, "NOTIFY", "all", NOTIFY_MODES),
            webui_password=env.get("WEBUI_PASSWORD", ""),
            env_tokens=tokens,
            env_account_name=env.get("ACCOUNT_NAME", "").strip()[:60],
            puid=_int(env, "PUID", 99, 0, 2**31 - 1),
            pgid=_int(env, "PGID", 100, 0, 2**31 - 1),
            log_level=_choice(env, "LOG_LEVEL", "INFO", ("DEBUG", "INFO", "WARNING", "ERROR")),
            # Only used by the test suite (fake SKPORT server).
            as_base=env.get("SKPORT_AS_BASE", DEFAULT_AS_BASE),
            zonai_base=env.get("SKPORT_ZONAI_BASE", DEFAULT_ZONAI_BASE),
        )

    @property
    def notification_language(self) -> str:
        if self.ui_language != "auto":
            return self.ui_language
        return SKPORT_TO_UI.get(self.language, "en_US")
