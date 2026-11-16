"""預計完成日調整（FR-DUE、FR-MRK-01～02）。

`adjust_due` 是凍結契約：整批順延（Phase 4）與確認延期候選（Dev-B Phase 7）都直接呼叫它。
只改 latest_due，不動 orig_due；我的任務必須給註記或選稍後註記。
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo.tasks_repo import TaskRepo
from app.domain.events import is_mine, write_event
from app.domain.reasons import check_due_reason, check_mark
from app.errors import DomainError

PAST_LIMIT_DAYS = 365
FUTURE_LIMIT_DAYS = 730


@dataclass
class DueResult:
    task: dict
    event: dict
    mine: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def needs_mark(self) -> bool:
        """我的任務、這次沒有註記（選了稍後註記）。docs/decisions.md DA-04。"""
        return self.mine and self.event["mark"] is None


def check_date_range(new_due: date, today: date) -> None:
    if not (today - timedelta(days=PAST_LIMIT_DAYS) <= new_due <= today + timedelta(days=FUTURE_LIMIT_DAYS)):
        raise DomainError("DATE_OUT_OF_RANGE", details={
            "min": (today - timedelta(days=PAST_LIMIT_DAYS)).isoformat(),
            "max": (today + timedelta(days=FUTURE_LIMIT_DAYS)).isoformat()})


def adjust_due(session: Connection, task_id: int, new_due: date, expected_version: int,
               reason: str | None, note: str | None, mark: str | None, defer_mark: bool, *,
               origin: str, batch_id: int | None = None, origin_ref: int | None = None,
               source_id: int | None = None) -> DueResult:
    repo = TaskRepo(session)
    task = repo.get_for_update(task_id, expected_version)
    if task["status"] == "done":
        raise DomainError("TASK_DONE", details={"task_id": task_id})
    if new_due == task["latest_due"]:
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    check_date_range(new_due, get_clock().today())
    delta_days = (new_due - task["latest_due"]).days
    check_due_reason(reason, delta_days)
    check_mark(mark)

    warnings: list[str] = []
    mine = is_mine(task)
    if mine:
        if mark is not None and defer_mark:
            raise DomainError("VALIDATION_ERROR", "註記與稍後註記只能擇一", {"fields": ["mark", "defer_mark"]})
        if mark is None and not defer_mark:
            raise DomainError("MARK_REQUIRED", details={"task_id": task_id})
    elif mark is not None:
        warnings.append("MARK_IGNORED")   # docs/decisions.md DA-11
        mark = None
    if new_due < task["start_date"]:
        warnings.append("BEFORE_START")

    event = write_event(
        session, task_id=task_id, project_id=task["project_id"], task_title=task["title"], mine=mine,
        kind="due", field="latest_due", from_value=task["latest_due"].isoformat(),
        to_value=new_due.isoformat(), delta_days=delta_days, reason=reason, note=note, mark=mark,
        origin=origin, origin_ref=batch_id if origin_ref is None and batch_id is not None else origin_ref,
        source_id=source_id, batch_id=batch_id,
    )
    updated = repo.update(task_id, {"latest_due": new_due})
    return DueResult(task=updated, event=event, mine=mine, warnings=warnings)
