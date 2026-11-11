"""Check-in logic: for every account and every Endfield role, claim if not done today."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .notify import Notifier, format_rewards
from .skport import (AccountError, Role, Session, SessionExpired, SkportClient,
                     SkportError, resource_view)
from .store import Store

log = logging.getLogger(__name__)

SESSION_TTL = 6 * 3600  # re-login from the account token at least this often


@dataclass
class _Cached:
    session: Session
    roles: list[Role]
    created: float


@dataclass
class RoleResult:
    role: Role
    data: dict[str, Any]
    claimed: bool = False
    rewards: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RunSummary:
    outcomes: dict[str, str] = field(default_factory=dict)  # account id -> ok | transient | action

    @property
    def transient(self) -> bool:
        return "transient" in self.outcomes.values()


def _flags(items: Any) -> list[dict[str, Any]]:
    return [
        {"id": str(item.get("awardId") or ""), "done": bool(item.get("done")), "available": bool(item.get("available"))}
        for item in items or [] if isinstance(item, dict)
    ]


def role_view(result: RoleResult) -> dict[str, Any]:
    calendar = _flags(result.data.get("calendar"))
    return {
        "key": result.role.key,
        "nickname": result.role.nickname,
        "server": result.role.server,
        "level": result.role.level,
        "has_today": bool(result.data.get("hasToday")) or result.claimed,
        "done": sum(1 for day in calendar if day["done"]),
        "total": len(calendar),
        "calendar": calendar,
        "first": _flags(result.data.get("first")),
        "rewards": result.rewards,
    }


class CheckinService:
    def __init__(self, store: Store, client: SkportClient, notifier: Notifier):
        self.store = store
        self.client = client
        self.notifier = notifier
        self._run_lock = threading.Lock()
        self._cache: dict[str, _Cached] = {}
        self.running = False

    def forget(self, account_id: str) -> None:
        self._cache.pop(account_id, None)

    # ------------------------------------------------------------------ runs
    def run(self, account_ids: set[str] | None = None, reason: str = "schedule") -> RunSummary:
        summary = RunSummary()
        with self._run_lock:
            self.running = True
            try:
                accounts = [a for a in self.store.list_accounts()
                            if account_ids is None or a["id"] in account_ids]
                if accounts:
                    log.info("check-in run (%s) for %d account(s)", reason, len(accounts))
                for account in accounts:
                    summary.outcomes[account["id"]] = self._run_account(account)
            finally:
                self.running = False
        return summary

    def _run_account(self, account: dict[str, Any]) -> str:
        account_id, name = account["id"], account["name"]
        previous = self.store.get_state(account_id)
        state = dict(previous)
        state["last_check"] = time.time()
        try:
            results = self._check_account(account)
        except AccountError as exc:
            self.forget(account_id)
            return self._failed(account, previous, state, exc.kind, str(exc), action=True)
        except SkportError as exc:
            return self._failed(account, previous, state, exc.kind, str(exc), action=False)
        except Exception as exc:  # unexpected answer shape or bug: keep the scheduler alive
            log.exception("[%s] unexpected error", name)
            return self._failed(account, previous, state, "internal", repr(exc), action=False)

        roles = [role_view(r) for r in results]
        resources = dict(previous.get("resources") or {})
        for result in results:
            for key in ("calendar", "first"):
                for item in result.data.get(key) or []:
                    award_id = item.get("awardId") if isinstance(item, dict) else None
                    info = (result.data.get("resourceInfoMap") or {}).get(award_id)
                    view = resource_view(info)
                    if award_id and view:
                        resources[award_id] = view
        claimed = [view for view, result in zip(roles, results) if result.claimed]
        state.update(status="claimed" if claimed else "done", kind=None, message="",
                     roles=roles, resources=resources)
        if claimed:
            state["last_claim"] = state["last_check"]
            state["last_rewards"] = [{"role": r["nickname"] or r["server"], "rewards": r["rewards"]} for r in claimed]
            for role in claimed:
                text = format_rewards(role["rewards"], "-")
                log.info("[%s] %s: claimed %s (%s/%s)", name, role["nickname"] or role["key"], text, role["done"], role["total"])
                self.store.add_event("claimed", name, f"{role['nickname'] or role['server']}: {text}")
            self.notifier.claimed(name, claimed)
        else:
            log.info("[%s] already claimed today for %d role(s)", name, len(roles))
        if previous.get("status") in ("error", "action_required"):
            self.store.add_event("recovered", name)
            self.notifier.recovered(name)
        self.store.set_state(account_id, state)
        return "ok"

    def _failed(self, account: dict[str, Any], previous: dict[str, Any], state: dict[str, Any],
                kind: str, message: str, action: bool) -> str:
        status = "action_required" if action else "error"
        log.warning("[%s] %s: %s", account["name"], status, message)
        state.update(status=status, kind=kind, message=message)
        if previous.get("status") != status or previous.get("kind") != kind:
            self.store.add_event(status, account["name"], message)
            self.notifier.error(account["name"], message, action)
        self.store.set_state(account["id"], state)
        return "action" if action else "transient"

    # -------------------------------------------------------------- helpers
    def _check_account(self, account: dict[str, Any]) -> list[RoleResult]:
        cached = self._session_for(account)
        try:
            return [self._check_role(cached.session, role) for role in cached.roles]
        except SessionExpired:
            log.info("[%s] session expired, logging in again", account["name"])
            self.forget(account["id"])
            cached = self._session_for(account)
            return [self._check_role(cached.session, role) for role in cached.roles]

    def _session_for(self, account: dict[str, Any]) -> _Cached:
        cached = self._cache.get(account["id"])
        if cached and time.time() - cached.created < SESSION_TTL:
            return cached
        session = self._open_session(account)
        override = (account.get("role_override") or "").strip()
        roles = [Role(key=override, nickname=override)] if override else self.client.get_roles(session)
        if not roles:
            raise AccountError("no Arknights: Endfield role is bound to this SKPORT account", kind="no_role")
        cached = _Cached(session=session, roles=roles, created=time.time())
        self._cache[account["id"]] = cached
        return cached

    def _open_session(self, account: dict[str, Any]) -> Session:
        try:
            return self.client.open_session(account["account_token"])
        except AccountError:
            if not (account.get("email") and account.get("password")):
                raise
            log.info("[%s] account token rejected, logging in with the saved password", account["name"])
            token = self.client.login(account["email"], account["password"])
            self.store.update_token(account["id"], token)
            account["account_token"] = token
            return self.client.open_session(token)

    def _check_role(self, session: Session, role: Role) -> RoleResult:
        data = self.client.get_status(session, role.key)
        if data.get("hasToday"):
            return RoleResult(role=role, data=data)
        claim = self.client.claim(session, role.key)
        try:
            data = self.client.get_status(session, role.key)
        except SkportError as exc:
            log.debug("status refresh after claim failed: %s", exc)
        return RoleResult(role=role, data=data, claimed=not claim.already, rewards=claim.rewards)
