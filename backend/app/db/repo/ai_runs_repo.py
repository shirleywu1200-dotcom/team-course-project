"""AI 呼叫紀錄（ai_runs，FR-AI-02）與 AI 結果的使用者回饋（ai_feedback，FR-AI-04）。"""

from sqlalchemy import Connection, text

from app.ai.client import AIInvalidOutput, AITimeout
from app.db.repo.rows import insert_row

RUN_COLUMNS = {"node_id", "job_id", "status", "attempt", "latency_ms", "raw_output", "error", "created_at"}
FEEDBACK_COLUMNS = {"node_id", "target_type", "target_id", "outcome", "detail", "created_at"}


def insert_run(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "ai_runs", RUN_COLUMNS, fields)


def get_run(conn: Connection, run_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM ai_runs WHERE id = :id"), {"id": run_id}).mappings().first()
    return dict(row) if row else None


def clear_raw_output_before(conn: Connection, before) -> int:
    """建立時間早於 before 的輸出設為 NULL，不分節點（PR #20 B2）。"""
    return conn.execute(text(
        "UPDATE ai_runs SET raw_output = NULL WHERE created_at <= :b AND raw_output IS NOT NULL"),
        {"b": before}).rowcount


def clear_raw_output_of_purged_sources(conn: Connection) -> int:
    """連得回已清除來源的輸出設為 NULL：經背景工作的 source_ids，或經候選的 ai_run_id。

    背景工作可能在收件後很久才呼叫 AI，只靠 created_at 會比原文晚清（PR #20 審查）。
    """
    return conn.execute(text(
        "UPDATE ai_runs SET raw_output = NULL WHERE raw_output IS NOT NULL AND ("
        " job_id IN (SELECT j.id FROM jobs j WHERE EXISTS ("
        "   SELECT 1 FROM sources s WHERE s.excerpt IS NULL"
        "   AND s.id IN (SELECT jsonb_array_elements_text(j.payload->'source_ids')::bigint)))"
        " OR id IN (SELECT c.ai_run_id FROM candidates c JOIN sources s ON s.id = c.source_id"
        "   WHERE s.excerpt IS NULL AND c.ai_run_id IS NOT NULL))")).rowcount


def clear_all_raw_output(conn: Connection) -> int:
    return conn.execute(text("UPDATE ai_runs SET raw_output = NULL WHERE raw_output IS NOT NULL")).rowcount


def insert_feedback(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "ai_feedback", FEEDBACK_COLUMNS, fields)


def has_feedback_for_run(conn: Connection, node_id: str, run_id: int) -> bool:
    """detail.ai_run_id 記著回饋來自哪一筆 ai_runs（12.7 D-3c：同一筆只寫一次）。"""
    sql = text("SELECT 1 FROM ai_feedback WHERE node_id = :n AND detail->>'ai_run_id' = :r LIMIT 1")
    return conn.execute(sql, {"n": node_id, "r": str(run_id)}).first() is not None


def has_goal_link_feedback(conn: Connection, run_id: int, task_id: int) -> bool:
    """AI-03 的回饋一筆建議（ai_run_id＋task_id）只寫一次（spec 5.13）。"""
    sql = text("SELECT 1 FROM ai_feedback WHERE node_id = 'AI-03' AND detail->>'ai_run_id' = :r "
               "AND detail->>'task_id' = :t LIMIT 1")
    return conn.execute(sql, {"r": str(run_id), "t": str(task_id)}).first() is not None


def status_for(exc: Exception) -> str:
    """例外對應 ai_runs.status；子類別也正確歸類。"""
    if isinstance(exc, AITimeout):
        return "timeout"
    if isinstance(exc, AIInvalidOutput):
        return "invalid_output"
    return "error"
