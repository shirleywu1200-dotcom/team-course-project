"""週報彙整的查詢（todo 10.1）。只讀。

三個查詢各回一段的候選資料，都帶任務的 scope，私人範圍的排除與計數由 domain 層負責。
只取需要的欄位：不讀事件的備註、原因、註記與原句（資安規則 2）。
事件的日期一律以台北時區判斷（spec 8.2），不依賴連線的時區設定。
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import Connection, text

from app.clock import TZ


def done_in_range(conn: Connection, start: date, end: date) -> list[dict]:
    """done_date 落在區間內、而且有完成事件（status → done）的已完成任務，附最新一筆完成事件的 id。

    沒有完成事件的不列入（#18 G3：只讀已確認的事件）。
    """
    rows = conn.execute(text("""
        SELECT * FROM (
          SELECT t.id AS task_id, t.title, t.owner_name, t.scope, t.done_date,
                 (SELECT e.id FROM events e
                   WHERE e.task_id = t.id AND e.kind = 'status' AND e.field = 'status' AND e.to_value = 'done'
                   ORDER BY e.id DESC LIMIT 1) AS event_id
            FROM tasks t
           WHERE t.status = 'done' AND t.done_date BETWEEN :start AND :end
        ) d
         WHERE d.event_id IS NOT NULL
         ORDER BY d.done_date, d.task_id
    """), {"start": start, "end": end}).mappings()
    return [dict(r) for r in rows]


def delay_events_in_range(conn: Connection, start: date, end: date) -> list[dict]:
    """區間內（台北日期）delta_days > 0 的 due 事件，附任務目前的原訂與最新預計日。

    只取目前仍延期（latest_due > orig_due）的任務：基準更正或提前後已不延期的不列入（#18 G1）。
    """
    rows = conn.execute(text("""
        SELECT e.id AS event_id, t.id AS task_id, t.title, t.owner_name, t.scope, t.orig_due, t.latest_due
          FROM events e JOIN tasks t ON t.id = e.task_id
         WHERE e.kind = 'due' AND e.delta_days > 0 AND t.latest_due > t.orig_due
           AND e.ts >= :ts_from AND e.ts < :ts_to
         ORDER BY t.id, e.id
    """), {"ts_from": datetime.combine(start, time(), TZ),
          "ts_to": datetime.combine(end + timedelta(days=1), time(), TZ)}).mappings()
    return [dict(r) for r in rows]


def open_due_or_blocked(conn: Connection, end: date) -> list[dict]:
    """未完成、不在封存專案裡，且卡住或最新預計日不晚於 end 的任務。

    「不晚於 end」同時涵蓋下週到期與已逾期（早於下週一；#18 G6、H1）。封存專案的任務不列入（G5）。
    """
    rows = conn.execute(text("""
        SELECT t.id AS task_id, t.title, t.owner_name, t.scope, t.latest_due, t.blocked
          FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
         WHERE t.status <> 'done' AND p.archived_at IS NULL AND (t.blocked OR t.latest_due <= :end)
         ORDER BY t.latest_due, t.id
    """), {"end": end}).mappings()
    return [dict(r) for r in rows]


def work_task_ids(conn: Connection, task_ids: list[int]) -> set[int]:
    """這些任務中，目前仍存在而且是工作範圍的 id（GET 重新對帳 next 用，#18 J1）。"""
    if not task_ids:
        return set()
    rows = conn.execute(text("SELECT id FROM tasks WHERE id = ANY(:ids) AND scope = 'work'"),
                        {"ids": list(task_ids)}).scalars()
    return set(rows)


def item_tasks(conn: Connection, task_ids: list[int]) -> dict[int, dict]:
    """週報 items 可讀內容用的任務現值（spec 5.14）。只取工作範圍，只取列出的欄位。"""
    if not task_ids:
        return {}
    rows = conn.execute(text(
        "SELECT id, title, owner_name, done_date, orig_due, latest_due, blocked FROM tasks "
        "WHERE id = ANY(:ids) AND scope = 'work'"), {"ids": list(task_ids)}).mappings()
    return {r["id"]: dict(r) for r in rows}


def item_events(conn: Connection, event_ids: list[int]) -> dict[int, dict]:
    """週報 items 的事件證據（spec 5.14）：只取 id、時間與前值、後值、天數，不讀原因、備註、註記與原句。"""
    if not event_ids:
        return {}
    rows = conn.execute(text(
        "SELECT id, ts, from_value, to_value, delta_days FROM events WHERE id = ANY(:ids)"),
        {"ids": list(event_ids)}).mappings()
    return {r["id"]: dict(r) for r in rows}
