"""候選加 project_id：待配對候選建任務時沿用收件的專案（PR #20 審查 B5、FR-INB-14）。

DDL 本體在同目錄的 0004_candidates_project.sql。降級會刪除欄位與索引（候選上記的專案一併消失）。

Revision ID: 0004
Revises: 0003
"""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_name("0004_candidates_project.sql")

DOWNGRADE_SQL = """
DROP INDEX IF EXISTS ix_candidates_project;
ALTER TABLE candidates DROP COLUMN IF EXISTS project_id;
"""


def _exec_script(sql: str) -> None:
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    _exec_script(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    _exec_script(DOWNGRADE_SQL)
