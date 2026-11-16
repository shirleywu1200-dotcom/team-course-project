"""事件寫入的唯一入口（凍結契約：todo 5.7）。

所有變更都寫成一筆 events（FR-HIS-01）。呼叫端與任務更新放在同一個交易內，
由 `Database.run` 統一 commit 或 rollback。
"""

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import events_repo
from app.db.repo.tasks_repo import TaskRepo

OWNER_ME = "我"
EVENT_FIELDS = events_repo.COLUMNS - {"ts"}


def is_mine(task: dict) -> bool:
    return task["owner_name"] == OWNER_ME


def write_event(session: Connection, **fields) -> dict:
    """新增一筆事件並回傳整列。

    有 task_id 時，未指定的 task_title、mine、project_id 從任務當下的狀態快照（FR-HIS-07）。
    非任務事件的 task_title 寫空字串（docs/decisions.md DA-05）。ts 由伺服器時鐘決定。
    """
    unknown = set(fields) - EVENT_FIELDS
    if unknown:
        raise ValueError(f"events 沒有欄位：{sorted(unknown)}")
    task_id = fields.get("task_id")
    if task_id is not None and not {"task_title", "mine", "project_id"} <= fields.keys():
        task = TaskRepo(session).get(task_id)
        fields.setdefault("task_title", task["title"])
        fields.setdefault("mine", is_mine(task))
        fields.setdefault("project_id", task["project_id"])
    fields.setdefault("task_title", "")
    return events_repo.insert(session, fields | {"ts": get_clock().now()})
