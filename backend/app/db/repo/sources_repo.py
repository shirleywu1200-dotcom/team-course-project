"""sources 資料表：收件訊息的必要摘錄（FR-INB-03、04）。"""

from sqlalchemy import Connection, bindparam, text

COLUMNS = {"channel", "line_group_id", "speaker", "spoken_at", "excerpt", "excerpt_hash",
           "received_at", "expires_at", "purged_at"}


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


def recompute_expiry(conn: Connection, days: int) -> int:
    """保存期限改變時，尚未清除的來源改用新天數重算期限（spec 6.7）。"""
    return conn.execute(text(
        "UPDATE sources SET expires_at = received_at + make_interval(days => :d) WHERE excerpt IS NOT NULL"),
        {"d": days}).rowcount


def purge_expired(conn: Connection, now) -> int:
    """到期的原文設為 NULL（FR-GOV-01）。已清除的不再動。"""
    return conn.execute(text(
        "UPDATE sources SET excerpt = NULL, purged_at = :now WHERE expires_at <= :now AND excerpt IS NOT NULL"),
        {"now": now}).rowcount


def purge_all(conn: Connection, now) -> int:
    """所有原文設為 NULL（FR-GOV-03）。"""
    return conn.execute(text(
        "UPDATE sources SET excerpt = NULL, purged_at = :now WHERE excerpt IS NOT NULL"), {"now": now}).rowcount
