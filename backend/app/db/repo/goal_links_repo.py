"""目標關聯的查詢（spec 5.13；todo 9.6、9.8、9.9）。

任務目前關聯的目標存在 tasks.goal_id（#47 G1，單一事實來源）；關聯決定的歷程是 field='goal_id' 的 goal 事件。
"""

from sqlalchemy import Connection, text

# 統計母體：已完成、有完成回報的任務（spec 5.13 stats）
_LINKED = """
    SELECT t.goal_id, t.expected_stars, cf.actual_stars, cf.energy, cf.overdue_days
      FROM tasks t
      JOIN completion_feedback cf ON cf.task_id = t.id
     WHERE t.status = 'done' AND t.goal_id IS NOT NULL
"""


def has_decision(conn: Connection, task_id: int) -> bool:
    """這個任務是否做過關聯決定（有過 field='goal_id' 的 goal 事件，含選「不關聯」）。"""
    return conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM events WHERE kind = 'goal' AND field = 'goal_id' AND task_id = :t)"
    ), {"t": task_id}).scalar_one()


def pending(conn: Connection) -> list[dict]:
    """已完成、有回報、從未做過關聯決定的任務；依完成日、任務 id 由新到舊，不篩選範圍或專案。"""
    return [dict(r) for r in conn.execute(text("""
        SELECT t.id AS task_id, t.title, t.project_id, t.scope, t.done_date, t.version
          FROM tasks t
         WHERE t.status = 'done'
           AND EXISTS (SELECT 1 FROM completion_feedback cf WHERE cf.task_id = t.id)
           AND NOT EXISTS (SELECT 1 FROM events e
                            WHERE e.kind = 'goal' AND e.field = 'goal_id' AND e.task_id = t.id)
         ORDER BY t.done_date DESC, t.id DESC
    """)).mappings()]


def linked_rows(conn: Connection, goal_id: int | None = None) -> list[dict]:
    """統計母體的逐筆資料；goal_id 為 None 時回所有目標的（矩陣用）。"""
    if goal_id is None:
        return [dict(r) for r in conn.execute(text(_LINKED)).mappings()]
    return [dict(r) for r in conn.execute(text(_LINKED + " AND t.goal_id = :g"), {"g": goal_id}).mappings()]


def project_progress(conn: Connection, project_id: int) -> tuple[int, int]:
    """專案的（完成數, 全部任務數），供 expectation 目標的進度（#47 B4）。"""
    row = conn.execute(text(
        "SELECT count(*) FILTER (WHERE status = 'done') AS done, count(*) AS total FROM tasks WHERE project_id = :p"
    ), {"p": project_id}).mappings().one()
    return row["done"], row["total"]
