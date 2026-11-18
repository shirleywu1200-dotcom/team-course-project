"""目標：建立、編輯、封存（FR-GOL-01、02；spec 5.13；比照專案 FR-PRJ-01～03）。

每個變更都寫一筆 `kind='goal'` 事件（task_id 為 null，extra 帶 goal_id），和任務的關聯事件以 task_id 分辨。
"""

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import goals_repo, projects_repo
from app.domain.events import write_event
from app.domain.text import required_texts
from app.errors import DomainError

EDITABLE = ("title", "period", "definition", "target", "energy_plan")


def _check_project(goal_type: str, project_id: int | None, conn: Connection) -> None:
    """expectation 必須對應存在的專案；其他類型不可帶專案（spec 5.13、#47 B4）。"""
    if goal_type == "expectation":
        if project_id is None:
            raise DomainError("VALIDATION_ERROR", "績效期待目標需要對應專案", {"fields": ["project_id"]})
        try:
            project = projects_repo.get(conn, project_id)
        except DomainError:
            raise DomainError("VALIDATION_ERROR", "專案不存在", {"fields": ["project_id"]}) from None
        if project["archived_at"] is not None:
            raise DomainError("VALIDATION_ERROR", "專案已封存", {"fields": ["project_id"]})
    elif project_id is not None:
        raise DomainError("VALIDATION_ERROR", "只有績效期待目標可以對應專案", {"fields": ["project_id"]})


def _event(conn: Connection, goal: dict, field: str, from_value, to_value) -> dict:
    return write_event(conn, project_id=goal["project_id"], kind="goal", field=field, from_value=from_value,
                       to_value=to_value, origin="manual", extra={"goal_id": goal["id"]})


def create_goal(conn: Connection, *, type: str, title: str, period: str, energy_plan: str, definition: str = "",
                target: int = 0, project_id: int | None = None) -> dict:
    texts = required_texts({"title": title, "period": period})
    title, period = texts["title"], texts["period"]
    _check_project(type, project_id, conn)
    goal = goals_repo.insert(conn, {
        "type": type, "title": title, "period": period, "definition": definition,
        "target": 0 if type == "expectation" else target,   # expectation 不用 target（B4）
        "energy_plan": energy_plan, "project_id": project_id, "created_at": get_clock().now(),
    })
    _event(conn, goal, "created", None, goal["title"])
    return goal


def update_goal(conn: Connection, goal_id: int, changes: dict) -> tuple[dict, list[dict]]:
    """逐欄比較，每個實際變更的欄位各寫一筆事件；沒有變更不寫。type、project_id 不可改。"""
    goal = goals_repo.get(conn, goal_id, for_update=True)
    changes = {k: v for k, v in changes.items() if k in EDITABLE}
    nulls = sorted(k for k, v in changes.items() if v is None)
    if nulls:   # 明確送 null 不當成沒有變更
        raise DomainError("VALIDATION_ERROR", details={"fields": nulls})
    changes |= required_texts({k: changes[k] for k in ("title", "period") if k in changes})
    if goal["type"] == "expectation":
        changes.pop("target", None)
    diff = {k: v for k, v in changes.items() if v != goal[k]}
    if not diff:
        return goal, []
    updated = goals_repo.update(conn, goal_id, diff)
    events = [_event(conn, goal, k, str(goal[k]), str(v)) for k, v in sorted(diff.items())]
    return updated, events


def archive_goal(conn: Connection, goal_id: int) -> dict:
    goal = goals_repo.get(conn, goal_id, for_update=True)
    if goal["archived_at"] is not None:
        return goal
    now = get_clock().now()
    updated = goals_repo.update(conn, goal_id, {"archived_at": now})
    _event(conn, goal, "archived_at", None, now.isoformat())
    return updated
