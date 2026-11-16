"""AI 呼叫紀錄（ai_runs，FR-AI-02）的寫入，週報 AI-05 用。

暫時模組：Dev-B 的 PR #20 有同功能的 `ai_runs_repo.insert_run`。為了不和 #20 同時新增同一個檔案而衝突，
先放在這裡；#20 合併後改用 `ai_runs_repo`，並刪除本檔（#22 協議）。
"""

from sqlalchemy import Connection

from app.db.repo.rows import insert_row

COLUMNS = {"node_id", "job_id", "status", "attempt", "latency_ms", "raw_output", "error", "created_at"}


def insert(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "ai_runs", COLUMNS, fields)
