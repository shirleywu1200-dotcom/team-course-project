"""sources 資料表：收件訊息的必要摘錄（FR-INB-03、04）。"""

from sqlalchemy import Connection, bindparam, text

COLUMNS = {"channel", "line_group_id", "speaker", "spoken_at", "excerpt", "excerpt_hash",
           "received_at", "expires_at", "purged_at"}
DEFAULT_RETENTION_DAYS = 30


def insert_if_new(conn: Connection, fields: dict) -> int | None:
    """同雜湊已存在（含同時送出的另一筆收件）就不寫，回 None（FR-INB-04）。"""
    cols = sorted(fields)
    unknown = set(cols) - COLUMNS
    if unknown:
        raise ValueError(f"sources 沒有欄位：{unknown}")
    sql = (f"INSERT INTO sources ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)}) "  # noqa: S608 欄位名稱來自白名單
           "ON CONFLICT (excerpt_hash) DO NOTHING RETURNING id")
    return conn.execute(text(sql), fields).scalar_one_or_none()


def existing_hashes(conn: Connection, hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    sql = text("SELECT excerpt_hash FROM sources WHERE excerpt_hash IN :h").bindparams(bindparam("h", expanding=True))
    return set(conn.execute(sql, {"h": hashes}).scalars())


def get_many(conn: Connection, ids: list[int]) -> list[dict]:
    sql = text("SELECT * FROM sources WHERE id IN :ids ORDER BY id").bindparams(bindparam("ids", expanding=True))
    return [dict(r) for r in conn.execute(sql, {"ids": ids}).mappings()]


def retention_days(conn: Connection) -> int:
    """設定的保存天數；尚未完成啟用（沒有 settings 列）時用預設值。"""
    days = conn.execute(text("SELECT retention_days FROM settings WHERE id = 1")).scalar_one_or_none()
    return days or DEFAULT_RETENTION_DAYS
