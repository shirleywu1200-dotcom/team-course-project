"""系統種子：settings（id=1）與量表 v0（PR #1 審查 B2、AC-59）。

SQL 本體在同目錄的 0003_seed.sql，冪等。

降級不刪除種子：量表受 0002 的不可修改觸發器保護，也不該被刪；
再升級時 ON CONFLICT DO NOTHING，兩表仍各 1 列。

Revision ID: 0003
Revises: 0002
"""

from pathlib import Path

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_name("0003_seed.sql")


def upgrade() -> None:
    raw = op.get_bind().connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    pass
