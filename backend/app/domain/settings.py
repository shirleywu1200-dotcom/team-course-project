"""設定與啟用（todo 8.1、FR-SET-01～03；Phase 8 SDD 第 2 節）。

設定列由程式補上（SDD Q1）：還沒有資料列時以 DDL 預設值＋下方三句精力定義建立。
"""

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import settings_repo, sources_repo
from app.domain import governance, rubrics

DEFAULT_ENERGY = {
    "high": "需要整段專注，做完會明顯疲累",
    "mid": "正常節奏可以完成",
    "low": "零碎時間就能處理",
}


def ensure(conn: Connection) -> None:
    settings_repo.insert_default(conn, DEFAULT_ENERGY)


def get_settings(conn: Connection) -> dict:
    ensure(conn)
    return settings_repo.get(conn)


def update_settings(conn: Connection, fields: dict) -> dict:
    """部分更新。保存期限改變時重算未清除來源的期限，已到期的立刻清除（SDD Q2）。"""
    current = get_settings(conn)
    if not fields:
        return current
    row = settings_repo.update(conn, fields)
    if row["retention_days"] != current["retention_days"]:
        sources_repo.recompute_expiry(conn, row["retention_days"])
        governance.purge_expired(conn)
    return row


def complete_onboarding(conn: Connection, skipped: bool) -> dict:
    """第一次呼叫寫入完成時間，之後不改。略過時採預設值並確保量表 v0 存在（FR-SET-01）。"""
    row = get_settings(conn)
    if row["onboarded_at"] is None:
        row = settings_repo.update(conn, {"onboarded_at": get_clock().now()})
    if skipped:
        rubrics.ensure_v0(conn)
    return row
