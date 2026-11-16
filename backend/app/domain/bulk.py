"""整批順延（FR-BLK）。

預覽不寫入；commit 在單一交易內建立批次並逐項呼叫 adjust_due，任一項失敗整批回滾。
不自動推論相依，由使用者勾選（FR-BLK-03）。
"""

from datetime import timedelta

from sqlalchemy import Connection, text

from app.clock import get_clock
from app.db.repo import misc_repo, projects_repo
from app.domain.due import adjust_due
from app.domain.events import is_mine
from app.domain.reasons import check_due_reason, check_mark
from app.errors import DomainError

MAX_DAYS = 365


def _load_and_validate(conn: Connection, project_id: int, items: list[dict], days: int,
                       reason: str | None, *, lock: bool) -> list[dict]:
    projects_repo.get(conn, project_id)
    if not items:
        raise DomainError("EMPTY_SELECTION")
    if days == 0 or abs(days) > MAX_DAYS:
        raise DomainError("VALIDATION_ERROR", "天數須為非 0 整數，且絕對值不超過 365", {"fields": ["days"]})
    check_due_reason(reason, days)
    ids = [i["task_id"] for i in items]
    if len(set(ids)) != len(ids):
        raise DomainError("VALIDATION_ERROR", "清單中有重複任務", {"fields": ["items"]})
    sql = "SELECT * FROM tasks WHERE id = ANY(:ids) ORDER BY id" + (" FOR UPDATE" if lock else "")  # noqa: S608 固定字串
    tasks = {r["id"]: dict(r) for r in conn.execute(text(sql), {"ids": ids}).mappings()}
    outside = [i for i in ids if i not in tasks or tasks[i]["project_id"] != project_id]
    if outside:
        raise DomainError("VALIDATION_ERROR", "清單含不屬於此專案的任務", {"task_ids": outside})
    done = [{"task_id": i, "title": tasks[i]["title"]} for i in ids if tasks[i]["status"] == "done"]
    if done:
        raise DomainError("INCLUDES_DONE_TASK", details={"tasks": done})
    return [tasks[i] | {"expected_version": item["expected_version"]} for i, item in zip(ids, items, strict=True)]


def preview_bulk(conn: Connection, project_id: int, items: list[dict], days: int,
                 reason: str | None = None) -> dict:
    today = get_clock().today()
    rows = []
    for t in _load_and_validate(conn, project_id, items, days, reason, lock=False):
        new_due = t["latest_due"] + timedelta(days=days)
        warnings = []
        if new_due < today:
            warnings.append("BEFORE_TODAY")
        if new_due < t["start_date"]:
            warnings.append("BEFORE_START")
        rows.append({"task_id": t["id"], "title": t["title"], "owner": t["owner_name"],
                     "from": t["latest_due"], "to": new_due, "mine": is_mine(t), "warnings": warnings})
    mine_count = sum(1 for r in rows if r["mine"])
    return {"items": rows, "mine_count": mine_count, "mark_required": mine_count > 0}


def commit_bulk(conn: Connection, project_id: int, items: list[dict], days: int, reason: str | None,
                note: str | None, mark: str | None, defer_mark: bool) -> dict:
    tasks = _load_and_validate(conn, project_id, items, days, reason, lock=True)
    stale = [{"task_id": t["id"], "expected_version": t["expected_version"], "current_version": t["version"]}
             for t in tasks if t["version"] != t["expected_version"]]
    if stale:
        raise DomainError("STALE_VERSION", details={"tasks": stale})
    check_mark(mark)
    mine_count = sum(1 for t in tasks if is_mine(t))
    if mine_count and mark is None and not defer_mark:
        raise DomainError("MARK_REQUIRED", details={"mine_count": mine_count})
    batch = misc_repo.insert_batch(conn, {"project_id": project_id, "days": days, "reason": reason, "note": note,
                                          "task_count": len(tasks), "created_at": get_clock().now()})
    event_ids, mine_marked = [], 0
    for t in tasks:
        mine = is_mine(t)
        result = adjust_due(conn, t["id"], t["latest_due"] + timedelta(days=days), t["expected_version"],
                            reason, note, mark if mine else None, defer_mark if mine else False,
                            origin="bulk", batch_id=batch["id"])
        event_ids.append(result.event["id"])
        mine_marked += 1 if mine and result.event["mark"] is not None else 0
    return {"batch_id": batch["id"], "updated": len(tasks), "mine_marked": mine_marked, "events": event_ids}
