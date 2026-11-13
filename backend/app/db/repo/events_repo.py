"""events 資料表的讀取與新增。events 只增不改，這裡沒有更新或刪除函式。"""

from sqlalchemy import Connection, text

from app.db.repo.rows import insert_row
from app.errors import DomainError

COLUMNS = {"ts", "project_id", "task_id", "task_title", "kind", "field", "from_value", "to_value",
           "origin", "origin_ref", "source_id", "reason", "note", "delta_days", "mark", "mine",
           "ref_event_id", "batch_id", "actor", "extra"}


def insert(conn: Connection, fields: dict) -> dict:
    return insert_row(conn, "events", COLUMNS, fields)


def get(conn: Connection, event_id: int) -> dict:
    row = conn.execute(text("SELECT * FROM events WHERE id = :id"), {"id": event_id}).mappings().first()
    if row is None:
        raise DomainError("NOT_FOUND", details={"event_id": event_id})
    return dict(row)


def list_for_task(conn: Connection, task_id: int, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        text("SELECT * FROM events WHERE task_id = :tid ORDER BY ts DESC, id DESC LIMIT :lim"),
        {"tid": task_id, "lim": limit},
    ).mappings()
    return [dict(r) for r in rows]


def latest_annotation(conn: Connection, event_id: int) -> dict | None:
    row = conn.execute(
        text("SELECT * FROM events WHERE kind = 'annotation' AND ref_event_id = :eid "
             "ORDER BY id DESC LIMIT 1"),
        {"eid": event_id},
    ).mappings().first()
    return dict(row) if row else None


def count_due_events(conn: Connection, task_id: int) -> int:
    return conn.execute(
        text("SELECT count(*) FROM events WHERE task_id = :tid AND kind = 'due'"), {"tid": task_id}
    ).scalar_one()


def latest_baseline_ts(conn: Connection, project_id: int):
    return conn.execute(
        text("SELECT max(ts) FROM events WHERE project_id = :pid AND kind = 'baseline'"), {"pid": project_id}
    ).scalar_one()


def mine_due_events_with_effective_mark(conn: Connection, date_from=None, date_to=None) -> list[dict]:
    """時間管理統計的母體：mine、delta≠0 的 due 事件，附有效註記（FR-MRK-05、06）。"""
    where = ["e.kind = 'due'", "e.mine", "e.delta_days <> 0"]
    params = {}
    if date_from is not None:
        where.append("e.ts >= CAST(:dfrom AS date)")
        params["dfrom"] = date_from
    if date_to is not None:
        where.append("e.ts < CAST(:dto AS date) + 1")
        params["dto"] = date_to
    sql = f"""
        SELECT e.id, e.task_id, e.delta_days,
               COALESCE(
                 (SELECT a.mark FROM events a
                   WHERE a.kind = 'annotation' AND a.ref_event_id = e.id
                   ORDER BY a.id DESC LIMIT 1),
                 e.mark) AS effective_mark
          FROM events e
         WHERE {' AND '.join(where)}
    """  # noqa: S608 條件為固定字串
    return [dict(r) for r in conn.execute(text(sql), params).mappings()]
