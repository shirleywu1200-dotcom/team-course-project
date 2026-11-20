"""目標回報存檔：每個目標一列的部分唯一索引與 goal_id CHECK（spec 5.13「目標回報」第 1 點；#47、#86）。

DDL 本體在同目錄的 0006_goal_reports.sql。降級只刪索引與 CHECK，資料列保留。

Revision ID: 0006
Revises: 0005
"""

from pathlib import Path

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_name("0006_goal_reports.sql")

DOWNGRADE_SQL = """
ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_goal_id_check;
DROP INDEX IF EXISTS reports_goal_uq;
"""


def _exec_script(sql: str) -> None:
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _exec_script(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    _exec_script(DOWNGRADE_SQL)
