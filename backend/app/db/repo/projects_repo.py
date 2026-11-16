"""projects 資料表的讀寫。專案不刪除，只封存（FR-PRJ-03）。"""

from sqlalchemy import Connection, text

from app.clock import get_clock
from app.db.repo.rows import insert_row, update_row
from app.errors import DomainError

COLUMNS = {"name", "scope", "audience", "line_group_id", "created_at", "updated_at", "archived_at"}


def get(conn: Connection, project_id: int, *, for_update: bool = False) -> dict:
    sql = "SELECT * FROM projects WHERE id = :id" + (" FOR UPDATE" if for_update else "")  # noqa: S608 固定字串
    row = conn.execute(text(sql), {"id": project_id}).mappings().first()
    if row is None:
        raise DomainError("NOT_FOUND", details={"project_id": project_id})
    return dict(row)


def insert(conn: Connection, fields: dict) -> dict:
    now = get_clock().now()
    return insert_row(conn, "projects", COLUMNS, {"created_at": now, "updated_at": now} | fields)


def update(conn: Connection, project_id: int, fields: dict) -> dict:
    return update_row(conn, "projects", COLUMNS, project_id, fields | {"updated_at": get_clock().now()})


def list_all(conn: Connection, include_archived: bool) -> list[dict]:
    where = "" if include_archived else " WHERE archived_at IS NULL"
    sql = "SELECT * FROM projects" + where + " ORDER BY id"  # noqa: S608 固定字串
    return [dict(r) for r in conn.execute(text(sql)).mappings()]


def task_count(conn: Connection, project_id: int) -> int:
    return conn.execute(text("SELECT count(*) FROM tasks WHERE project_id = :pid"), {"pid": project_id}).scalar_one()
