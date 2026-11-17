"""spec 1.3 衡量值的查詢（todo 13.8 埋點檢查，資料面）。

只讀。每個函式回傳 {"numerator", "denominator", "rate"}；分母為 0 時 rate 為 None。
定義依 #34 裁定（2026-11-17），見 docs/metrics.md。衡量值 1 的查詢待 PR #23 合併後補。
"""

from sqlalchemy import Connection, text

from app.db.repo import events_repo


def _rate(num: int, den: int) -> dict:
    return {"numerator": num, "denominator": den, "rate": (num / den) if den else None}


def candidate_confirm_rate(conn: Connection) -> dict:
    """衡量值 3：AI 建議被原樣接受率＝（accepted＋edited）÷ 已處理的候選（#34 裁定 3(b)）。

    讀 AI-01 對候選的回饋：每個候選處理時寫一筆（inbox/confirm.py 的 _close）；open 沒有回饋，不計。
    改建新任務（changed）不算接受、仍在分母；含修改後確認（edited）。
    """
    row = conn.execute(text(
        "SELECT count(*) FILTER (WHERE outcome IN ('accepted','edited')) AS a, count(*) AS d "
        "  FROM ai_feedback WHERE node_id = 'AI-01' AND target_type = 'candidate'"
    )).mappings().one()
    return _rate(row["a"], row["d"])


def mark_completion_rate(conn: Connection) -> dict:
    """衡量值 4：我的日期調整註記完成率＝有效註記非空 ÷ 全部。

    母體與有效註記沿用時間管理統計的查詢（mine、delta≠0 的 due 事件；FR-MRK-05、06），兩處口徑只有一份。
    """
    rows = events_repo.mine_due_events_with_effective_mark(conn)
    return _rate(sum(1 for r in rows if r["effective_mark"] is not None), len(rows))


def feedback_fill_rate(conn: Connection) -> dict:
    """衡量值 5：完成回報填寫率＝有完成回報的已完成任務 ÷ 已完成任務。"""
    row = conn.execute(text(
        "SELECT count(cf.id) AS filled, count(*) AS done "
        "  FROM tasks t LEFT JOIN completion_feedback cf ON cf.task_id = t.id WHERE t.status = 'done'"
    )).mappings().one()
    return _rate(row["filled"], row["done"])


def daily_confirm_span_minutes(conn: Connection) -> list[dict]:
    """衡量值 2 的近似值：每天第一筆到最後一筆候選處理時間的分鐘數。

    不是實際確認時間（中間可能離開），只能當上限參考；正式量測需要 FR-INB-16 的使用時間紀錄。
    """
    rows = conn.execute(text("""
        SELECT (decided_at AT TIME ZONE 'Asia/Taipei')::date AS day,
               round(extract(epoch FROM max(decided_at) - min(decided_at)) / 60.0, 1) AS span_min,
               count(*) AS decisions
          FROM candidates WHERE decided_at IS NOT NULL
         GROUP BY 1 ORDER BY 1
    """)).mappings()
    return [dict(r) for r in rows]
