"""設定與啟用（todo 8.1、FR-SET-01～03；Phase 8 SDD 第 2 節）。

設定列（id=1）由系統種子遷移 0003 寫入（審查 B2，推翻 SDD Q1），程式不另補。
"""

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import settings_repo, sources_repo
from app.domain import governance


def get_settings(conn: Connection) -> dict:
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


def complete_onboarding(conn: Connection) -> dict:
    """第一次呼叫寫入完成時間，之後不改。略過時沿用種子值，不必另做處理（FR-SET-01）。"""
    row = get_settings(conn)
    if row["onboarded_at"] is None:
        row = settings_repo.update(conn, {"onboarded_at": get_clock().now()})
    return row
