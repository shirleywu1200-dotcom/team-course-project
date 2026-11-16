"""週報存檔：reports 加 ai_items、ai_status，每週一列的部分唯一索引與週次 CHECK（#18 第 1 點 (b)、J8）。

DDL 本體在同目錄的 0004_weekly_reports.sql。降級會刪除這兩個欄位與索引（欄位內的 AI 初稿項目一併消失）。

Revision ID: 0004
Revises: 0003
"""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_name("0004_weekly_reports.sql")

DOWNGRADE_SQL = """
ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_weekly_period_check;
DROP INDEX IF EXISTS reports_weekly_period_uq;
ALTER TABLE reports DROP COLUMN IF EXISTS ai_status;
ALTER TABLE reports DROP COLUMN IF EXISTS ai_items;
"""


def _exec_script(sql: str) -> None:
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _exec_script(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    _exec_script(DOWNGRADE_SQL)
