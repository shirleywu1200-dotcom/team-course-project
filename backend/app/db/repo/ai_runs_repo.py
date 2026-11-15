"""AI 呼叫紀錄（ai_runs，FR-AI-02）與 AI 結果的使用者回饋（ai_feedback，FR-AI-04）。"""

from sqlalchemy import Connection

from app.db.repo.rows import insert_row

RUN_COLUMNS = {"node_id", "job_id", "status", "attempt", "latency_ms", "raw_output", "error", "created_at"}
FEEDBACK_COLUMNS = {"node_id", "target_type", "target_id", "outcome", "detail", "created_at"}


def insert_run(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "ai_runs", RUN_COLUMNS, fields)


def insert_feedback(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "ai_feedback", FEEDBACK_COLUMNS, fields)
