"""目標關聯（FR-GOL-03；spec 5.13；#47 G1）。

關聯由使用者確認：同一交易寫一筆 goal 事件並更新 tasks.goal_id（版本加 1）。改選、改成不關聯都是新增一筆事件。
"""

from sqlalchemy import Connection

from app.db.repo import feedback_repo, goal_links_repo, goals_repo
from app.db.repo.tasks_repo import TaskRepo
from app.domain.events import write_event
from app.errors import DomainError


def _check_goal(conn: Connection, goal_id: int | None) -> None:
    """目標必須存在且未封存（B7）；null 代表不關聯。"""
    if goal_id is None:
        return
    try:
        goal = goals_repo.get(conn, goal_id)
    except DomainError:
        raise DomainError("VALIDATION_ERROR", "目標不存在", {"fields": ["goal_id"]}) from None
    if goal["archived_at"] is not None:
        raise DomainError("VALIDATION_ERROR", "目標已封存", {"fields": ["goal_id"]})


def link(conn: Connection, task_id: int, goal_id: int | None, expected_version: int) -> tuple[dict, dict]:
    """確認關聯；回傳 (任務, 事件)。檢查順序依 spec 5.13。"""
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)       # NOT_FOUND、STALE_VERSION
    if task["status"] != "done" or feedback_repo.get_by_task(conn, task_id) is None:
        raise DomainError("VALIDATION_ERROR", "只有已完成且已填完成回報的任務可以關聯目標", {"fields": ["task_id"]})
    _check_goal(conn, goal_id)
    # 第一次選「不關聯」時新舊值都是 null，仍要記下這個決定（spec 5.13）
    if goal_id == task["goal_id"] and goal_links_repo.has_decision(conn, task_id):
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    event = write_event(conn, task_id=task_id, kind="goal", field="goal_id",
                        from_value=_text(task["goal_id"]), to_value=_text(goal_id), origin="manual")
    return repo.update(task_id, {"goal_id": goal_id}), event


def _text(goal_id: int | None) -> str | None:
    return None if goal_id is None else str(goal_id)


def pending(conn: Connection) -> list[dict]:
    """待關聯清單：不呼叫 AI（#47 G3）。"""
    return goal_links_repo.pending(conn)
