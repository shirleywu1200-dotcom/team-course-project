"""結構變更：移除 AI-08、rubrics 不可修改觸發器（PR #1 審查 A1、B5）。

DDL 本體在同目錄的 0002_structure.sql。

Revision ID: 0002
Revises: 0001
"""

from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_name("0002_structure.sql")

DOWNGRADE_SQL = """
DROP TRIGGER IF EXISTS rubrics_no_truncate ON rubrics;
DROP TRIGGER IF EXISTS rubrics_no_delete ON rubrics;
DROP TRIGGER IF EXISTS rubrics_no_update ON rubrics;
DROP FUNCTION IF EXISTS rubrics_immutable();
ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_node_id_check;
ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_node_id_check
  CHECK (node_id IN ('AI-01','AI-02','AI-03','AI-04','AI-05','AI-06','AI-07','AI-08'));
"""


def _exec_script(sql: str) -> None:
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _exec_script(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    _exec_script(DOWNGRADE_SQL)
