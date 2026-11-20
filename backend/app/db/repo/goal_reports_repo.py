"""目標回報（reports, kind='goal'）的讀寫（todo 9.10；遷移 0006；spec 5.13「目標回報」）。

每個目標一列由部分唯一索引保證；寫入一律用 INSERT … ON CONFLICT，同時產生也不會撞號。
AI 欄位與人工版分開更新：AI 寫入不碰 manual_text，人工版寫入不碰 AI 欄位（比照 AC-51）。
"""

import json
from datetime import datetime

from sqlalchemy import Connection, text

from app.errors import DomainError


def find(conn: Connection, goal_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM reports WHERE kind = 'goal' AND goal_id = :g"),
                       {"g": goal_id}).mappings().first()
    return dict(row) if row else None


def get(conn: Connection, goal_id: int) -> dict:
    """沒有列是「尚未產生」：回 NOT_FOUND，details 只放 goal_id（spec 5.13 第 2 點）。"""
    row = find(conn, goal_id)
    if row is None:
        raise DomainError("NOT_FOUND", details={"goal_id": goal_id})
    return row


def save_success(conn: Connection, goal_id: int, draft: str, figures: list[dict], excluded_private: int,
                 now: datetime) -> None:
    conn.execute(text("""
        INSERT INTO reports (kind, goal_id, ai_draft, ai_items, ai_status, excluded_private, created_at, updated_at)
        VALUES ('goal', :g, :draft, CAST(:items AS jsonb), 'ok', :ex, :now, :now)
        ON CONFLICT (goal_id) WHERE kind = 'goal' DO UPDATE SET
          ai_draft = EXCLUDED.ai_draft, ai_items = EXCLUDED.ai_items, ai_status = 'ok',
          excluded_private = EXCLUDED.excluded_private, updated_at = EXCLUDED.updated_at
    """), {"g": goal_id, "draft": draft, "items": json.dumps(figures), "ex": excluded_private, "now": now})


def save_failure(conn: Connection, goal_id: int, ai_status: str, excluded_private: int, now: datetime) -> None:
    """AI 失敗、R3 失敗或依規則不呼叫：第一次建一列；已有成功初稿時整列不動（比照週報 FR-RPT-04）。"""
    conn.execute(text("""
        INSERT INTO reports (kind, goal_id, ai_status, excluded_private, created_at, updated_at)
        VALUES ('goal', :g, :st, :ex, :now, :now)
        ON CONFLICT (goal_id) WHERE kind = 'goal' DO UPDATE SET
          ai_status = EXCLUDED.ai_status, excluded_private = EXCLUDED.excluded_private,
          updated_at = EXCLUDED.updated_at
        WHERE reports.ai_status IS DISTINCT FROM 'ok'
    """), {"g": goal_id, "st": ai_status, "ex": excluded_private, "now": now})


def save_manual(conn: Connection, goal_id: int, manual_text: str | None, now: datetime) -> None:
    """人工版：沒有列時建一列（AI 欄位為 NULL），已有列只改 manual_text 與 updated_at（spec 5.13 第 6 點）。"""
    conn.execute(text("""
        INSERT INTO reports (kind, goal_id, manual_text, created_at, updated_at)
        VALUES ('goal', :g, :t, :now, :now)
        ON CONFLICT (goal_id) WHERE kind = 'goal' DO UPDATE SET
          manual_text = EXCLUDED.manual_text, updated_at = EXCLUDED.updated_at
    """), {"g": goal_id, "t": manual_text, "now": now})
