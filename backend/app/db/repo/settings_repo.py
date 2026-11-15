"""settings 資料表：單列（id = 1）的使用者設定（FR-SET-02）。"""

from sqlalchemy import Connection, text

from app.db.repo.rows import update_row

COLUMNS = {"default_scope", "role", "report_audience", "confirm_time", "confirm_cap_min", "remind_default",
           "retention_days", "energy_def_high", "energy_def_mid", "energy_def_low", "goal_types_enabled",
           "onboarded_at"}


def insert_default(conn: Connection, energy: dict) -> None:
    """沒有設定列時建立；其他欄位用 DDL 的預設值。已存在就不動。"""
    conn.execute(text(
        "INSERT INTO settings (id, energy_def_high, energy_def_mid, energy_def_low) "
        "VALUES (1, :high, :mid, :low) ON CONFLICT (id) DO NOTHING"), energy)


def get(conn: Connection) -> dict:
    return dict(conn.execute(text("SELECT * FROM settings WHERE id = 1")).mappings().one())


def update(conn: Connection, fields: dict) -> dict:
    return update_row(conn, "settings", COLUMNS, 1, fields)
