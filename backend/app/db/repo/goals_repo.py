"""goals 資料表：目標（FR-GOL-01、02；spec 5.13）。不刪除，只封存。"""

from sqlalchemy import Connection, text

from app.db.repo.rows import insert_row, update_row
from app.errors import DomainError

COLUMNS = {"type", "title", "period", "definition", "target", "energy_plan", "project_id", "created_at",
           "archived_at"}


def get(conn: Connection, goal_id: int, *, for_update: bool = False) -> dict:
    sql = "SELECT * FROM goals WHERE id = :id" + (" FOR UPDATE" if for_update else "")  # noqa: S608 固定字串
    row = conn.execute(text(sql), {"id": goal_id}).mappings().first()
    if row is None:
        raise DomainError("NOT_FOUND", details={"goal_id": goal_id})
    return dict(row)


def insert(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "goals", COLUMNS, fields)


def update(conn: Connection, goal_id: int, fields: dict) -> dict:
    return update_row(conn, "goals", COLUMNS, goal_id, fields)


def list_all(conn: Connection, include_archived: bool) -> list[dict]:
    where = "" if include_archived else " WHERE archived_at IS NULL"
    sql = "SELECT * FROM goals" + where + " ORDER BY id"  # noqa: S608 固定字串
    return [dict(r) for r in conn.execute(text(sql)).mappings()]
