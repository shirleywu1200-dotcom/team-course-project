"""資料控制用的查詢：冪等快取清除、匯出時列出與讀取資料表（FR-GOV-02、03）。"""

from sqlalchemy import Connection, text


def delete_idempotency_before(conn: Connection, before) -> int:
    return conn.execute(text("DELETE FROM idempotency_keys WHERE created_at < :b"), {"b": before}).rowcount


def delete_all_idempotency(conn: Connection) -> int:
    return conn.execute(text("DELETE FROM idempotency_keys")).rowcount


def begin_snapshot(conn: Connection) -> None:
    """必須是交易內第一個陳述式：之後所有讀取看到同一個時間點。"""
    conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))


def table_names(conn: Connection) -> list[str]:
    return list(conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
        "AND table_type = 'BASE TABLE' AND table_name <> 'alembic_version' ORDER BY table_name")).scalars())


def dump_table(conn: Connection, table: str) -> list[dict]:
    sql = f'SELECT * FROM "{table}" ORDER BY 1'  # noqa: S608 表名來自系統目錄
    return [dict(r) for r in conn.execute(text(sql)).mappings()]


def schema_version(conn: Connection) -> str | None:
    return conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
