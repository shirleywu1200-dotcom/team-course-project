"""週報（reports, kind='weekly'）的讀寫（todo 10.4；遷移 0005）。

每週一列由部分唯一索引保證；寫入一律用 INSERT … ON CONFLICT，同一週同時產生也不會撞號。
AI 欄位與人工版分開更新：AI 寫入不碰 manual_text，人工版寫入不碰 AI 欄位（AC-51）。
"""

import json
from datetime import date, datetime

from sqlalchemy import Connection, text

from app.errors import DomainError


def get_weekly(conn: Connection, report_id: int) -> dict:
    row = conn.execute(text("SELECT * FROM reports WHERE id = :id AND kind = 'weekly'"),
                       {"id": report_id}).mappings().first()
    if row is None:
        raise DomainError("NOT_FOUND", details={"report_id": report_id})
    return dict(row)


def save_success(conn: Connection, week_start: date, draft: str, items: list[dict], excluded_private: int,
                 now: datetime) -> int:
    """AI 初稿通過對帳：存 ai_draft、ai_items、ai_status='ok'。"""
    return conn.execute(text("""
        INSERT INTO reports (kind, period_start, ai_draft, ai_items, ai_status, excluded_private,
                             created_at, updated_at)
        VALUES ('weekly', :ws, :draft, CAST(:items AS jsonb), 'ok', :ex, :now, :now)
        ON CONFLICT (period_start) WHERE kind = 'weekly' DO UPDATE SET
          ai_draft = EXCLUDED.ai_draft, ai_items = EXCLUDED.ai_items, ai_status = 'ok',
          excluded_private = EXCLUDED.excluded_private, updated_at = EXCLUDED.updated_at
        RETURNING id
    """), {"ws": week_start, "draft": draft, "items": json.dumps(items, ensure_ascii=False),
           "ex": excluded_private, "now": now}).scalar_one()


def save_failure(conn: Connection, week_start: date, ai_status: str, excluded_private: int, now: datetime) -> int:
    """AI 失敗或對帳失敗：第一次產生就建一列；已有成功初稿時整列不動（#18 H2、J4）。"""
    rid = conn.execute(text("""
        INSERT INTO reports (kind, period_start, ai_status, excluded_private, created_at, updated_at)
        VALUES ('weekly', :ws, :st, :ex, :now, :now)
        ON CONFLICT (period_start) WHERE kind = 'weekly' DO UPDATE SET
          ai_status = EXCLUDED.ai_status, excluded_private = EXCLUDED.excluded_private,
          updated_at = EXCLUDED.updated_at
        WHERE reports.ai_status IS DISTINCT FROM 'ok'
        RETURNING id
    """), {"ws": week_start, "st": ai_status, "ex": excluded_private, "now": now}).scalar_one_or_none()
    if rid is None:   # 已有成功初稿，沒有更新
        rid = conn.execute(text("SELECT id FROM reports WHERE kind = 'weekly' AND period_start = :ws"),
                           {"ws": week_start}).scalar_one()
    return rid


def save_manual(conn: Connection, report_id: int, manual_text: str | None, now: datetime) -> None:
    updated = conn.execute(text(
        "UPDATE reports SET manual_text = :t, updated_at = :now WHERE id = :id AND kind = 'weekly'"),
        {"t": manual_text, "now": now, "id": report_id}).rowcount
    if updated == 0:
        raise DomainError("NOT_FOUND", details={"report_id": report_id})
