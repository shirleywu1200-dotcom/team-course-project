"""基準更正（FR-BAS）：兩段式確認後覆蓋 orig_due，舊值只留在歷程。

preview 產生綁定任務版本與內容的確認憑證（10 分鐘、單次使用）；
commit 必須帶憑證與 ack=true。既有日期事件與註記不重算（FR-BAS-07）。
"""

import secrets
from datetime import date, timedelta

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import events_repo, misc_repo
from app.db.repo.tasks_repo import TaskRepo
from app.domain.events import write_event
from app.domain.reasons import BASELINE_REASONS, BASELINE_TYPES
from app.errors import DomainError

TOKEN_TTL = timedelta(minutes=10)


def _validate(task: dict, new_orig_due: date, type_: str, reason: str | None) -> None:
    if task["status"] == "done":
        raise DomainError("TASK_DONE", details={"task_id": task["id"]})
    if type_ not in BASELINE_TYPES:
        raise DomainError("VALIDATION_ERROR", details={"fields": ["type"]})
    if reason not in BASELINE_REASONS:
        raise DomainError("VALIDATION_ERROR", "請選擇更正原因", {"fields": ["reason"]})
    if new_orig_due == task["orig_due"]:
        raise DomainError("NO_CHANGE", details={"task_id": task["id"]})


def preview_baseline(conn: Connection, task_id: int, new_orig_due: date, type_: str, reason: str | None,
                     expected_version: int) -> dict:
    repo = TaskRepo(conn)
    task = repo.get(task_id)
    _validate(task, new_orig_due, type_, reason)
    if task["version"] != expected_version:
        raise DomainError("STALE_VERSION", details={"task_id": task_id, "expected_version": expected_version,
                                                     "current_version": task["version"]})
    now = get_clock().now()
    token = secrets.token_urlsafe(24)
    expires_at = now + TOKEN_TTL
    misc_repo.insert_confirmation(conn, {
        "token": token, "task_id": task_id, "task_version": task["version"], "expires_at": expires_at,
        "payload": {"new_orig_due": new_orig_due.isoformat(), "type": type_, "reason": reason,
                    "orig_due": task["orig_due"].isoformat()},
    })
    return {
        "confirmation_token": token,
        "expires_at": expires_at,
        "impact": {
            "orig_due": {"from": task["orig_due"], "to": new_orig_due},
            "gap_days": {"from": (task["latest_due"] - task["orig_due"]).days,
                         "to": (task["latest_due"] - new_orig_due).days},
            "project_delayed_count": {
                "from": repo.delayed_count(task["project_id"]),
                "to": repo.delayed_count(task["project_id"], override=(task_id, new_orig_due)),
            },
            "past_due_events_kept": events_repo.count_due_events(conn, task_id),
            "old_value_kept_in_history": True,
        },
    }


def commit_baseline(conn: Connection, task_id: int, confirmation_token: str, ack: bool) -> tuple[dict, dict]:
    if ack is not True:
        raise DomainError("ACK_REQUIRED")
    now = get_clock().now()
    conf = misc_repo.get_confirmation_for_update(conn, confirmation_token)
    if conf is None or conf["task_id"] != task_id or conf["used_at"] is not None or conf["expires_at"] <= now:
        raise DomainError("CONFIRMATION_INVALID")
    repo = TaskRepo(conn)
    task = repo.get(task_id)
    payload = conf["payload"]
    new_orig_due = date.fromisoformat(payload["new_orig_due"])
    _validate(task, new_orig_due, payload["type"], payload["reason"])
    if task["version"] != conf["task_version"] or task["orig_due"].isoformat() != payload["orig_due"]:
        raise DomainError("CONFIRMATION_INVALID")
    task = repo.get_for_update(task_id, conf["task_version"])
    misc_repo.mark_confirmation_used(conn, confirmation_token, now)
    event = write_event(
        conn, task_id=task_id, kind="baseline", field="orig_due", from_value=task["orig_due"].isoformat(),
        to_value=new_orig_due.isoformat(), reason=payload["reason"], origin="baseline_correction",
        extra={"type": payload["type"], "confirmation": "two_step"},
    )
    return repo.update(task_id, {"orig_due": new_orig_due}), event
