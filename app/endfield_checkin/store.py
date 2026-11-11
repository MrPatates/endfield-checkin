"""JSON persistence in the /config volume (accounts, last results, history)."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from .skport import normalize_token

log = logging.getLogger(__name__)

HISTORY_SIZE = 200


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:12]


class Store:
    def __init__(self, data_dir: Path, env_tokens: tuple[str, ...] = (), env_name: str = ""):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.accounts_path = self.dir / "accounts.json"
        self.state_path = self.dir / "state.json"
        self._lock = threading.RLock()
        self._accounts: list[dict[str, Any]] = [
            a for a in self._load(self.accounts_path).get("accounts", [])
            if isinstance(a, dict) and a.get("id") and a.get("account_token")
        ]
        state = self._load(self.state_path)
        self._state: dict[str, dict[str, Any]] = state.get("accounts", {}) if isinstance(state.get("accounts"), dict) else {}
        self._history: list[dict[str, Any]] = state.get("history", []) if isinstance(state.get("history"), list) else []
        # Accounts from the ACCOUNT_TOKEN variable live only in memory.
        self._env_accounts = []
        for index, raw in enumerate(env_tokens, start=1):
            token = normalize_token(raw)
            if not token:
                continue
            name = env_name or "Unraid"
            if len(env_tokens) > 1:
                name = f"{name} {index}"
            self._env_accounts.append({
                "id": "env-" + token_fingerprint(token),
                "name": name,
                "source": "env",
                "account_token": token,
                "created": None,
            })

    # ------------------------------------------------------------- file I/O
    def _load(self, path: Path) -> dict[str, Any]:
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            backup = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
            log.error("cannot read %s (%s); moved aside to %s", path, exc, backup.name)
            try:
                os.replace(path, backup)
            except OSError:
                pass
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, path: Path, data: Any) -> None:
        tmp = path.with_name(path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)

    def _save_accounts(self) -> None:
        self._write(self.accounts_path, {"version": 1, "accounts": self._accounts})

    def _save_state(self) -> None:
        self._write(self.state_path, {"version": 1, "accounts": self._state, "history": self._history})

    # ------------------------------------------------------------- accounts
    def list_accounts(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._env_accounts + self._accounts)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        with self._lock:
            for account in self._env_accounts + self._accounts:
                if account["id"] == account_id:
                    return copy.deepcopy(account)
        return None

    def has_token(self, token: str) -> bool:
        with self._lock:
            return any(a["account_token"] == token for a in self._env_accounts + self._accounts)

    def add_account(self, name: str, token: str, email: str | None = None,
                    password: str | None = None, role_override: str = "") -> dict[str, Any]:
        with self._lock:
            account = {
                "id": secrets.token_hex(6),
                "name": name,
                "source": "web",
                "account_token": token,
                "role_override": role_override,
                "created": time.time(),
            }
            if email and password:
                account["email"] = email
                account["password"] = password
            self._accounts.append(account)
            self._save_accounts()
            return copy.deepcopy(account)

    def update_token(self, account_id: str, token: str) -> None:
        with self._lock:
            for account in self._accounts:
                if account["id"] == account_id:
                    account["account_token"] = token
                    self._save_accounts()
                    return

    def delete_account(self, account_id: str) -> bool:
        with self._lock:
            before = len(self._accounts)
            self._accounts = [a for a in self._accounts if a["id"] != account_id]
            if len(self._accounts) == before:
                return False
            self._save_accounts()
            self._state.pop(account_id, None)
            self._save_state()
            return True

    # ---------------------------------------------------------------- state
    def get_state(self, account_id: str) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state.get(account_id, {}))

    def set_state(self, account_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self._state[account_id] = copy.deepcopy(state)
            self._save_state()

    def add_event(self, code: str, account: str, detail: str = "") -> None:
        """code: claimed | error | action_required | recovered | added | removed."""
        with self._lock:
            self._history.append({"ts": time.time(), "code": code, "account": account, "detail": detail})
            del self._history[:-HISTORY_SIZE]
            self._save_state()

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._history[-limit:][::-1])

    def prune_state(self) -> None:
        """Forget results of accounts that no longer exist (e.g. removed env token)."""
        with self._lock:
            known = {a["id"] for a in self._env_accounts + self._accounts}
            stale = [key for key in self._state if key not in known]
            for key in stale:
                del self._state[key]
            if stale:
                self._save_state()
