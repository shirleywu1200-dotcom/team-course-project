"""週報彙整的查詢（todo 10.1）。只讀。

三個查詢各回一段的候選資料，都帶任務的 scope，私人範圍的排除與計數由 domain 層負責。
只取需要的欄位：不讀事件的備註、原因、註記與原句（資安規則 2）。
事件的日期一律以台北時區判斷（spec 8.2），不依賴連線的時區設定。
"""

from datetime import date

from sqlalchemy import Connection, text

TZ_NAME = "Asia/Taipei"


def done_in_range(conn: Connection, start: date, end: date) -> list[dict]:
    """done_date 落在區間內的已完成任務，附最新一筆完成事件（status → done）的 id。"""
    rows = conn.execute(text("""
        SELECT t.id AS task_id, t.title, t.owner_name, t.scope, t.done_date,
               (SELECT e.id FROM events e
                 WHERE e.task_id = t.id AND e.kind = 'status' AND e.field = 'status' AND e.to_value = 'done'
                 ORDER BY e.id DESC LIMIT 1) AS event_id
          FROM tasks t
         WHERE t.status = 'done' AND t.done_date BETWEEN :start AND :end
         ORDER BY t.done_date, t.id
    """), {"start": start, "end": end}).mappings()
    return [dict(r) for r in rows]


def delay_events_in_range(conn: Connection, start: date, end: date) -> list[dict]:
    """區間內（台北日期）delta_days > 0 的 due 事件，附任務目前的原訂與最新預計日。"""
    rows = conn.execute(text("""
        SELECT e.id AS event_id, t.id AS task_id, t.title, t.owner_name, t.scope, t.orig_due, t.latest_due
          FROM events e JOIN tasks t ON t.id = e.task_id
         WHERE e.kind = 'due' AND e.delta_days > 0
           AND (e.ts AT TIME ZONE :tz)::date BETWEEN :start AND :end
         ORDER BY t.id, e.id
    """), {"start": start, "end": end, "tz": TZ_NAME}).mappings()
    return [dict(r) for r in rows]


def open_due_or_blocked(conn: Connection, start: date, end: date) -> list[dict]:
    """未完成，且卡住或最新預計日落在區間內的任務。"""
    rows = conn.execute(text("""
        SELECT t.id AS task_id, t.title, t.owner_name, t.scope, t.latest_due, t.blocked
          FROM tasks t
         WHERE t.status <> 'done' AND (t.blocked OR t.latest_due BETWEEN :start AND :end)
         ORDER BY t.latest_due, t.id
    """), {"start": start, "end": end}).mappings()
    return [dict(r) for r in rows]
