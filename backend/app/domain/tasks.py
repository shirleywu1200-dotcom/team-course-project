"""任務：建立、負責人、狀態、卡住、完成（FR-TSK-01～07）。

日期調整在 due.py，不在這裡。
"""

from datetime import date

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import events_repo, misc_repo, projects_repo
from app.db.repo.tasks_repo import TaskRepo
from app.domain.due import check_date_range  # 開始日與預計完成日共用同一個允許範圍
from app.domain.events import OWNER_ME, write_event
from app.domain.text import required_texts
from app.errors import DomainError


def star_source_for(expected_stars: int, suggested_stars: int | None) -> str:
    """伺服器判定預設星數來源（FR-TSK-03）；前端不能直接指定。"""
    if suggested_stars is None:
        return "self"
    return "ai_accepted" if suggested_stars == expected_stars else "ai_edited"


def _ensure_not_done(task: dict) -> None:
    if task["status"] == "done":
        raise DomainError("TASK_DONE", details={"task_id": task["id"]})


def create_task(conn: Connection, *, title: str, due: date, owner: str = OWNER_ME, scope: str | None = None,
                project_id: int | None = None, start: date | None = None, done_when: str = "",
                remind: str = "morning", goal_id: int | None = None, expected_stars: int = 3,
                suggested_stars: int | None = None, origin: str = "manual", origin_ref: int | None = None,
                source_id: int | None = None) -> dict:
    """建立任務並寫 created 事件。

    origin、origin_ref、source_id 記錄建立依據（FR-HIS-04）；例如收件匣從待配對候選建立任務時，
    帶 origin="candidate"、origin_ref=候選 id、source_id=原句來源（Issue #2、FR-INB-14）。
    """
    title = required_texts({"title": title})["title"]
    owner = (owner or "").strip() or OWNER_ME
    if start is not None and start > due:
        raise DomainError("VALIDATION_ERROR", "開始日不可晚於期限", {"fields": ["start"]})   # FR-TSK-08、AC-61
    if project_id is not None:
        project = projects_repo.get(conn, project_id)
        scope = scope or project["scope"]
    today = get_clock().today()
    if start is None:
        start = min(today, due)   # docs/decisions.md DA-07
    task = TaskRepo(conn).insert({
        "project_id": project_id, "title": title, "owner_name": owner, "scope": scope or "work",
        "start_date": start, "orig_due": due, "latest_due": due, "done_when": done_when or "",
        "remind": remind, "goal_id": goal_id, "expected_stars": expected_stars,
        "star_source": star_source_for(expected_stars, suggested_stars),
        "rubric_id": misc_repo.active_rubric_id(conn),
    })
    write_event(conn, task_id=task["id"], kind="task", field="created", to_value=title, origin=origin,
                origin_ref=origin_ref, source_id=source_id)
    return task


def get_task_detail(conn: Connection, task_id: int) -> dict:
    task = TaskRepo(conn).get(task_id)
    return {"task": task, "events": events_repo.list_for_task(conn, task_id)}


def change_owner(conn: Connection, task_id: int, owner: str, expected_version: int) -> tuple[dict, dict]:
    """改負責人；舊事件的 mine 與 task_title 不變（FR-TSK-06、AC-29）。"""
    owner = (owner or "").strip()
    if not owner:
        raise DomainError("VALIDATION_ERROR", details={"fields": ["owner"]})
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)
    if owner == task["owner_name"]:
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    event = write_event(conn, task_id=task_id, kind="task", field="owner_name",
                        from_value=task["owner_name"], to_value=owner, origin="manual")
    return repo.update(task_id, {"owner_name": owner}), event


def set_status(conn: Connection, task_id: int, status: str, expected_version: int) -> tuple[dict, dict]:
    """todo 與 doing 之間切換（docs/decisions.md DA-08）；完成走 complete_task。"""
    if status not in ("todo", "doing"):
        raise DomainError("VALIDATION_ERROR", details={"fields": ["status"]})
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)
    _ensure_not_done(task)
    if task["status"] == status:
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    event = write_event(conn, task_id=task_id, kind="status", field="status",
                        from_value=task["status"], to_value=status, origin="manual")
    return repo.update(task_id, {"status": status}), event


def set_blocked(conn: Connection, task_id: int, blocked: bool, expected_version: int, *,
                origin: str = "manual", origin_ref: int | None = None,
                source_id: int | None = None) -> tuple[dict, dict]:
    """標為卡住或取消；已完成任務不可再標卡住（FR-TSK-07）。"""
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)
    if blocked:
        _ensure_not_done(task)
    if task["blocked"] == blocked:
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    event = write_event(conn, task_id=task_id, kind="status", field="blocked",
                        from_value=str(task["blocked"]).lower(), to_value=str(blocked).lower(),
                        origin=origin, origin_ref=origin_ref, source_id=source_id)
    return repo.update(task_id, {"blocked": blocked}), event


def adjust_start(conn: Connection, task_id: int, new_start: date, expected_version: int,
                 note: str | None = None) -> tuple[dict, dict, list[str]]:
    """調整開始日（FR-TSK-09、AC-62）：只改 start_date，不問原因與註記，不進時間管理統計。"""
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)
    _ensure_not_done(task)
    if new_start == task["start_date"]:
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    check_date_range(new_start, get_clock().today())
    warnings = ["START_AFTER_DUE"] if new_start > task["latest_due"] else []
    event = write_event(conn, task_id=task_id, kind="task", field="start_date",
                        from_value=task["start_date"].isoformat(), to_value=new_start.isoformat(),
                        note=note, origin="manual")
    return repo.update(task_id, {"start_date": new_start}), event, warnings


def complete_task(conn: Connection, task_id: int, expected_version: int, done_date: date | None = None, *,
                  origin: str = "manual", origin_ref: int | None = None,
                  source_id: int | None = None) -> tuple[dict, dict, bool]:
    """標為完成。完成日預設今天、不可晚於今天；回傳是否需要完成回報。"""
    today = get_clock().today()
    done_date = done_date or today
    if done_date > today:
        raise DomainError("VALIDATION_ERROR", "完成日不可晚於今天", {"fields": ["done_date"]})
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)
    _ensure_not_done(task)   # docs/decisions.md DA-16
    event = write_event(conn, task_id=task_id, kind="status", field="status",
                        from_value=task["status"], to_value="done", origin=origin,
                        origin_ref=origin_ref, source_id=source_id,
                        extra={"done_date": done_date.isoformat()})
    updated = repo.update(task_id, {"status": "done", "done_date": done_date})
    return updated, event, True
