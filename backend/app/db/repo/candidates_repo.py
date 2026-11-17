"""candidates 資料表，以及 AI-01 比對用的任務清單（FR-INB-06、09）。"""

from sqlalchemy import Connection, bindparam, text

from app.db.repo.rows import insert_row, update_row
from app.errors import DomainError

COLUMNS = {"source_id", "kind", "certainty", "task_id", "proposed", "suggest", "note", "state",
           "decision", "decided_at", "ai_run_id", "created_at"}

# 候選連同原句與對應任務，供 API 輸出
_DETAIL = """
    SELECT c.*, s.speaker, s.spoken_at, s.excerpt, s.purged_at,
           t.title AS task_title, t.latest_due AS task_latest_due, t.orig_due AS task_orig_due,
           t.version AS task_version
      FROM candidates c
      JOIN sources s ON s.id = c.source_id
      LEFT JOIN tasks t ON t.id = c.task_id
"""


def insert(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "candidates", COLUMNS, fields)


def update(conn: Connection, candidate_id: int, fields: dict) -> dict:
    return update_row(conn, "candidates", COLUMNS, candidate_id, fields)


def get_for_update(conn: Connection, candidate_id: int) -> dict:
    row = conn.execute(text("SELECT * FROM candidates WHERE id = :id FOR UPDATE"),
                       {"id": candidate_id}).mappings().first()
    if row is None:
        raise DomainError("NOT_FOUND", details={"candidate_id": candidate_id})
    return dict(row)


def list_detail(conn: Connection, state: str) -> list[dict]:
    rows = conn.execute(text(_DETAIL + " WHERE c.state = :state ORDER BY c.id"), {"state": state}).mappings()
    return [dict(r) for r in rows]


def get_detail_many(conn: Connection, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    sql = text(_DETAIL + " WHERE c.id IN :ids ORDER BY c.id").bindparams(bindparam("ids", expanding=True))
    return [dict(r) for r in conn.execute(sql, {"ids": ids}).mappings()]


def tasks_for_matching(conn: Connection, project_id: int | None) -> list[dict]:
    """送給 AI-01 比對的任務：未完成、工作範圍（私人範圍不送 AI，CLAUDE.md 資安 2）。"""
    sql = ("SELECT id, title, owner_name, latest_due FROM tasks"
           " WHERE status <> 'done' AND scope = 'work'")
    params = {}
    if project_id is not None:
        sql += " AND project_id = :pid"
        params["pid"] = project_id
    return [dict(r) for r in conn.execute(text(sql + " ORDER BY id"), params).mappings()]
