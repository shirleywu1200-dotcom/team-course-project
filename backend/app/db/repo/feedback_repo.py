"""completion_feedback 資料表：完成回報（FR-FBK、spec 5.12）。只有新增與讀取；修改回報（9.3）依 D-05 不做。"""

from sqlalchemy import Connection, text


def insert_if_absent(conn: Connection, fields: dict) -> dict | None:
    """新增一筆；該任務已有回報時不寫入、回 None。task_id 有唯一限制，同時送出也不會變成 500。"""
    row = conn.execute(text(
        "INSERT INTO completion_feedback (task_id, actual_stars, energy, invest_vs_expected, overdue_days, rubric_id, "
        "created_at) VALUES (:task_id, :actual_stars, :energy, :invest_vs_expected, :overdue_days, :rubric_id, "
        ":created_at) ON CONFLICT (task_id) DO NOTHING RETURNING *"), fields).mappings().first()
    return dict(row) if row else None


def get_by_task(conn: Connection, task_id: int) -> dict | None:
    row = conn.execute(text("SELECT * FROM completion_feedback WHERE task_id = :t"), {"t": task_id}).mappings().first()
    return dict(row) if row else None


def pending_tasks(conn: Connection) -> list[dict]:
    """已完成但還沒有完成回報的任務，依完成日、任務 id 由舊到新（spec 5.12）。不篩選範圍或負責人。"""
    return [dict(r) for r in conn.execute(text("""
        SELECT t.id AS task_id, t.title, t.owner_name, t.project_id, t.done_date, t.orig_due, t.expected_stars,
               t.star_source
          FROM tasks t
         WHERE t.status = 'done'
           AND NOT EXISTS (SELECT 1 FROM completion_feedback cf WHERE cf.task_id = t.id)
         ORDER BY t.done_date, t.id
    """)).mappings()]

