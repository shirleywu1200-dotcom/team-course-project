"""時間管理註記：補註記、有效註記、統計（FR-MRK-04～07）。

原事件永遠不改；補註記與改註記都新增一筆 annotation 事件。
"""

from datetime import date

from sqlalchemy import Connection, text

from app.db.repo import events_repo
from app.domain.events import write_event
from app.domain.reasons import check_due_reason, check_mark
from app.errors import DomainError

MIN_SAMPLE = 5


def effective_mark(session: Connection, event_id: int) -> str | None:
    """指向該日期事件的最新 annotation；沒有則取原事件的註記（FR-MRK-05）。"""
    latest = events_repo.latest_annotation(session, event_id)
    if latest is not None:
        return latest["mark"]
    return events_repo.get(session, event_id)["mark"]


def annotate(session: Connection, event_id: int, mark: str, reason: str | None = None,
             note: str | None = None) -> tuple[dict, str]:
    if mark is None:
        raise DomainError("VALIDATION_ERROR", details={"fields": ["mark"]})
    check_mark(mark)
    target = events_repo.get(session, event_id)
    if target["kind"] != "due" or not target["mine"] or not target["delta_days"]:
        raise DomainError("ANNOTATION_NOT_ALLOWED", details={"event_id": event_id})
    check_due_reason(reason, target["delta_days"])   # docs/decisions.md DA-13
    previous = effective_mark(session, event_id)
    annotation = write_event(
        session, task_id=target["task_id"], project_id=target["project_id"], mine=target["mine"],
        kind="annotation", field="mark", from_value=previous, to_value=mark, mark=mark,
        reason=reason, note=note, ref_event_id=event_id, origin="manual",
    )
    return annotation, mark


def _energy_of_tasks(session: Connection, task_ids: set[int]) -> dict[str, int]:
    dist = {"high": 0, "mid": 0, "low": 0, "not_done": 0}
    if not task_ids:
        return dist
    rows = session.execute(
        text("SELECT t.id, cf.energy FROM tasks t LEFT JOIN completion_feedback cf ON cf.task_id = t.id "
             "WHERE t.id = ANY(:ids)"),
        {"ids": list(task_ids)},
    ).mappings()
    for r in rows:
        dist[r["energy"] or "not_done"] += 1   # 沒有完成回報一律算 not_done（DA-12）
    return dist


def time_mgmt_stats(session: Connection, date_from: date | None = None, date_to: date | None = None) -> dict:
    """統計口徑：mine、delta≠0、有效註記非空（FR-MRK-06）。未註記與不計入不進變好／變差。"""
    rows = events_repo.mine_due_events_with_effective_mark(session, date_from, date_to)
    better = [r for r in rows if r["effective_mark"] == "better"]
    worse = [r for r in rows if r["effective_mark"] == "worse"]
    return {
        "better": {"count": len(better), "days": sum(abs(r["delta_days"]) for r in better)},
        "worse": {"count": len(worse), "days": sum(abs(r["delta_days"]) for r in worse)},
        "none": sum(1 for r in rows if r["effective_mark"] == "none"),
        "unmarked": sum(1 for r in rows if r["effective_mark"] is None),
        "worse_by_energy": _energy_of_tasks(session, {r["task_id"] for r in worse}),
        "min_sample": MIN_SAMPLE,
        "judgement": None,   # 5 筆以上的判讀規則 spec 未定義（DA-12）
    }
