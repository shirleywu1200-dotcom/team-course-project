"""初始結構：全部資料表、索引、CHECK 約束與 events 只增觸發器（spec 4.2）。

DDL 本體在同目錄的 0001_initial.sql，與 spec 4.2 內容相同。

Revision ID: 0001
Revises:
"""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_name("0001_initial.sql")

TABLES_REVERSE_ORDER = [
    "idempotency_keys", "confirmations", "reports", "ai_feedback", "events", "batches",
    "candidates", "ai_runs", "jobs", "sources", "completion_feedback", "tasks", "goals",
    "projects", "line_groups", "rubrics", "settings",
]


def _exec_script(sql: str) -> None:
    # 透過驅動直接執行整份腳本：腳本含多個陳述式與 $$ 函式本體，不能經過參數綁定。
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _exec_script(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    drops = "".join(f"DROP TABLE IF EXISTS {t} CASCADE;\n" for t in TABLES_REVERSE_ORDER)
    _exec_script(drops + "DROP FUNCTION IF EXISTS events_append_only();\n")
