"""歷程查詢與甘特資料的讀取（Phase 5，spec 5.5、5.8）。只讀，不寫任何資料。"""

from sqlalchemy import Connection, text

# 有效註記（FR-MRK-05）：只對 due 事件計算，其他類型為 NULL
_EFFECTIVE_MARK = """
    CASE WHEN e.kind = 'due' THEN COALESCE(
      (SELECT a.mark FROM events a
        WHERE a.kind = 'annotation' AND a.ref_event_id = e.id
        ORDER BY a.id DESC LIMIT 1),
      e.mark) END
"""


def _where(filters: dict) -> tuple[str, dict]:
    """filters 鍵：project_id（int 或 'none'）、kind、task_id、batch_id、date_from、date_to。值為 None 的不篩。"""
    where, params = [], {}
    if filters.get("project_id") == "none":
        where.append("e.project_id IS NULL")
    elif filters.get("project_id") is not None:
        where.append("e.project_id = :project_id")
        params["project_id"] = filters["project_id"]
    for col in ("kind", "task_id", "batch_id"):
        if filters.get(col) is not None:
            where.append(f"e.{col} = :{col}")
            params[col] = filters[col]
    if filters.get("date_from") is not None:
        where.append("e.ts >= CAST(:dfrom AS date)")
        params["dfrom"] = filters["date_from"]
    if filters.get("date_to") is not None:
        where.append("e.ts < CAST(:dto AS date) + 1")
        params["dto"] = filters["date_to"]
    return (" WHERE " + " AND ".join(where) if where else ""), params


def search_events(conn: Connection, filters: dict, limit: int, offset: int) -> tuple[list[dict], int]:
    cond, params = _where(filters)
    total = conn.execute(text("SELECT count(*) FROM events e" + cond), params).scalar_one()  # noqa: S608 固定字串
    sql = f"""
        SELECT e.*, p.name AS project_name, {_EFFECTIVE_MARK} AS effective_mark,
               s.excerpt AS source_excerpt, s.purged_at AS source_purged_at, cand.kind AS candidate_kind
          FROM events e
          LEFT JOIN projects p ON p.id = e.project_id
          LEFT JOIN sources s ON s.id = e.source_id
          LEFT JOIN candidates cand ON e.origin = 'candidate' AND cand.id = e.origin_ref
          {cond}
         ORDER BY e.ts DESC, e.id DESC
         LIMIT :limit OFFSET :offset
    """  # noqa: S608 條件為固定字串，值走參數
    rows = conn.execute(text(sql), params | {"limit": limit, "offset": offset}).mappings()
    return [dict(r) for r in rows], total


def gantt_tasks(conn: Connection, project_id: int) -> list[dict]:
    rows = conn.execute(
        text("SELECT * FROM tasks WHERE project_id = :pid ORDER BY start_date, id"), {"pid": project_id}
    ).mappings()
    return [dict(r) for r in rows]


def open_candidate_count(conn: Connection, project_id: int) -> int:
    """對應任務屬於該專案的 open 候選數；unmatched（無任務）不計入專案（Phase 5 SDD Q1）。"""
    return conn.execute(
        text("SELECT count(*) FROM candidates c JOIN tasks t ON t.id = c.task_id "
             "WHERE c.state = 'open' AND t.project_id = :pid"),
        {"pid": project_id},
    ).scalar_one()
