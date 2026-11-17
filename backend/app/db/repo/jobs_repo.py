"""jobs 資料表：收件背景工作（FR-INB-05、08）。"""

from sqlalchemy import Connection, text

from app.db.repo.rows import insert_row, update_row
from app.errors import DomainError

COLUMNS = {"kind", "status", "attempts", "payload", "result", "error", "created_at", "updated_at"}


def insert(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "jobs", COLUMNS, fields)


def get(conn: Connection, job_id: int) -> dict:
    row = conn.execute(text("SELECT * FROM jobs WHERE id = :id"), {"id": job_id}).mappings().first()
    if row is None:
        raise DomainError("NOT_FOUND", details={"job_id": job_id})
    return dict(row)


def update(conn: Connection, job_id: int, fields: dict) -> dict:
    return update_row(conn, "jobs", COLUMNS, job_id, fields)


def claim_next(conn: Connection, now) -> dict | None:
    """取最舊的 queued 工作並改成 running；SKIP LOCKED 讓同時取件的行程不會拿到同一筆。"""
    row = conn.execute(text(
        "SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
    )).first()
    if row is None:
        return None
    return update(conn, row.id, {"status": "running", "updated_at": now})


def reset_running(conn: Connection, now) -> int:
    """服務重啟時把 running 重設為 queued，attempts 保留（spec 6.1）。回傳重設筆數。"""
    result = conn.execute(text(
        "UPDATE jobs SET status = 'queued', updated_at = :now WHERE status = 'running'"
    ), {"now": now})
    return result.rowcount
