"""rubrics 資料表：星數量表版本（FR-RUB-01）。只有新增與讀取，沒有更新或刪除路徑（版本不可變）。"""


from sqlalchemy import Connection, text

from app.db.repo.rows import insert_row

COLUMNS = {"version", "levels", "source", "interview", "created_at"}


def insert(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "rubrics", COLUMNS, fields)


def list_all(conn: Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(text("SELECT * FROM rubrics ORDER BY version")).mappings()]


def latest(conn: Connection) -> dict | None:
    row = conn.execute(text("SELECT * FROM rubrics ORDER BY version DESC LIMIT 1")).mappings().first()
    return dict(row) if row else None
