"""spec 1.3 衡量值的查詢（todo 13.8 埋點檢查，資料面）。

只讀。每個函式回傳 {"numerator", "denominator", "rate"}；分母為 0 時 rate 為 None。
衡量值 1（週報對得上歷程）與 2（每日確認時間）目前資料不足，見 docs/metrics.md。
"""

from sqlalchemy import Connection, text


def _rate(num: int, den: int) -> dict:
    return {"numerator": num, "denominator": den, "rate": (num / den) if den else None}


def candidate_confirm_rate(conn: Connection) -> dict:
    """衡量值 3：候選確認率（含修改後確認）＝ confirmed ÷（confirmed＋ignored）。open 不計。"""
    row = conn.execute(text(
        "SELECT count(*) FILTER (WHERE state = 'confirmed') AS c, "
        "       count(*) FILTER (WHERE state IN ('confirmed','ignored')) AS d FROM candidates"
    )).mappings().one()
    return _rate(row["c"], row["d"])


def mark_completion_rate(conn: Connection) -> dict:
    """衡量值 4：我的日期調整註記完成率＝有效註記非空 ÷ 全部（mine、delta≠0 的 due 事件）。"""
    row = conn.execute(text("""
        SELECT count(*) FILTER (WHERE COALESCE(
                 (SELECT a.mark FROM events a WHERE a.kind = 'annotation' AND a.ref_event_id = e.id
                   ORDER BY a.id DESC LIMIT 1), e.mark) IS NOT NULL) AS marked,
               count(*) AS total
          FROM events e
         WHERE e.kind = 'due' AND e.mine AND e.delta_days <> 0
    """)).mappings().one()
    return _rate(row["marked"], row["total"])


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
