"""專案：建立、編輯、封存（FR-PRJ-01～03）。"""

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import events_repo, projects_repo
from app.domain.events import write_event
from app.errors import DomainError

EDITABLE = ("name", "scope", "audience")


def _clean_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise DomainError("VALIDATION_ERROR", details={"fields": ["name"]})
    return name


def create_project(conn: Connection, *, name: str, scope: str = "work", audience: str = "manager",
                   line_group_id: int | None = None) -> dict:
    project = projects_repo.insert(conn, {"name": _clean_name(name), "scope": scope, "audience": audience,
                                          "line_group_id": line_group_id})
    write_event(conn, project_id=project["id"], kind="project", field="created",
                to_value=project["name"], origin="manual")
    return project


def get_project_detail(conn: Connection, project_id: int) -> dict:
    project = projects_repo.get(conn, project_id)
    return project | {
        "task_count": projects_repo.task_count(conn, project_id),
        "baseline_saved_at": events_repo.latest_baseline_ts(conn, project_id),
    }


def update_project(conn: Connection, project_id: int, changes: dict) -> tuple[dict, list[dict]]:
    """逐欄比較，每個實際變更的欄位各寫一筆 project 事件；沒有變更不寫（FR-PRJ-02、AC-26）。"""
    project = projects_repo.get(conn, project_id, for_update=True)
    if "name" in changes:
        changes = changes | {"name": _clean_name(changes["name"])}
    diff = {k: v for k, v in changes.items() if k in EDITABLE and v is not None and v != project[k]}
    if not diff:
        return project, []
    updated = projects_repo.update(conn, project_id, diff)
    events = [
        write_event(conn, project_id=project_id, kind="project", field=k,
                    from_value=str(project[k]), to_value=str(v), origin="manual")
        for k, v in sorted(diff.items())
    ]
    return updated, events


def archive_project(conn: Connection, project_id: int) -> dict:
    project = projects_repo.get(conn, project_id, for_update=True)
    if project["archived_at"] is not None:
        return project
    now = get_clock().now()
    updated = projects_repo.update(conn, project_id, {"archived_at": now})
    write_event(conn, project_id=project_id, kind="project", field="archived_at",
                to_value=now.isoformat(), origin="manual")
    return updated
