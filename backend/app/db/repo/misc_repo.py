"""其他小資料表：batches、confirmations、idempotency_keys、rubrics（只讀）。"""

import json

from sqlalchemy import Connection, text

from app.db.repo.rows import insert_row

BATCH_COLUMNS = {"project_id", "days", "reason", "note", "task_count", "created_at"}
CONFIRMATION_COLUMNS = {"token", "task_id", "payload", "task_version", "expires_at", "used_at"}


def insert_batch(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "batches", BATCH_COLUMNS, fields)


def insert_confirmation(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "confirmations", CONFIRMATION_COLUMNS, fields)


def get_confirmation_for_update(conn: Connection, token: str) -> dict | None:
    row = conn.execute(
        text("SELECT * FROM confirmations WHERE token = :t FOR UPDATE"), {"t": token}
    ).mappings().first()
    return dict(row) if row else None


def mark_confirmation_used(conn: Connection, token: str, used_at) -> None:
    conn.execute(text("UPDATE confirmations SET used_at = :u WHERE token = :t"), {"u": used_at, "t": token})


def active_rubric_id(conn: Connection) -> int | None:
    return conn.execute(text("SELECT id FROM rubrics ORDER BY version DESC LIMIT 1")).scalar_one_or_none()


def get_idempotency(conn: Connection, key: str, since) -> dict | None:
    row = conn.execute(
        text("SELECT * FROM idempotency_keys WHERE key = :k AND created_at >= :since"),
        {"k": key, "since": since},
    ).mappings().first()
    return dict(row) if row else None


def save_idempotency(conn: Connection, key: str, endpoint: str, response: dict, now, since) -> None:
    """保存首次結果。寫入前先刪掉所有超過 24 小時的列。

    回應本文可能含原句，不能無限期留著；「刪除所有來源原文」也要一併清這張表（交接說明 Dev-B 8.6）。
    """
    conn.execute(text("DELETE FROM idempotency_keys WHERE created_at < :since"), {"since": since})
    insert_sql = text(
        "INSERT INTO idempotency_keys (key, endpoint, response, created_at) "
        "VALUES (:k, :e, CAST(:r AS jsonb), :c) ON CONFLICT (key) DO NOTHING"
    )
    conn.execute(insert_sql, {"k": key, "e": endpoint, "r": json.dumps(response, ensure_ascii=False), "c": now})
