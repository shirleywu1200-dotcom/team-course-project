"""tasks 資料表的讀寫。"""

from datetime import date

from sqlalchemy import Connection, text

from app.clock import get_clock
from app.db.repo.rows import insert_row, update_row
from app.errors import DomainError

COLUMNS = {"project_id", "title", "owner_name", "scope", "start_date", "orig_due", "latest_due",
           "status", "blocked", "done_date", "done_when", "remind", "expected_stars", "star_source",
           "rubric_id", "goal_id", "version", "created_at", "updated_at"}


class TaskRepo:
    def __init__(self, session: Connection):
        self.conn = session

    def get(self, task_id: int) -> dict:
        row = self.conn.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id}).mappings().first()
        if row is None:
            raise DomainError("NOT_FOUND", details={"task_id": task_id})
        return dict(row)

    def get_for_update(self, task_id: int, expected_version: int) -> dict:
        """鎖定任務列並比對版本；版本不符丟 STALE_VERSION（凍結契約）。"""
        row = self.conn.execute(
            text("SELECT * FROM tasks WHERE id = :id FOR UPDATE"), {"id": task_id}
        ).mappings().first()
        if row is None:
            raise DomainError("NOT_FOUND", details={"task_id": task_id})
        if row["version"] != expected_version:
            raise DomainError("STALE_VERSION", details={
                "task_id": task_id, "expected_version": expected_version, "current_version": row["version"]})
        return dict(row)

    def insert(self, fields: dict) -> dict:
        now = get_clock().now()
        return insert_row(self.conn, "tasks", COLUMNS, {"created_at": now, "updated_at": now} | fields)

    def update(self, task_id: int, fields: dict) -> dict:
        """更新欄位並把 version 加 1。"""
        return update_row(self.conn, "tasks", COLUMNS, task_id,
                          fields | {"updated_at": get_clock().now()}, extra_set="version = version + 1")

    def list(self, *, project_id=None, single_only=False, owner=None, status=None, scope=None,
             due_before: date | None = None) -> list[dict]:
        where, params = [], {}
        if single_only:
            where.append("project_id IS NULL")
        elif project_id is not None:
            where.append("project_id = :project_id")
            params["project_id"] = project_id
        for col, val in (("owner_name", owner), ("status", status), ("scope", scope)):
            if val is not None:
                where.append(f"{col} = :{col}")
                params[col] = val
        if due_before is not None:
            where.append("latest_due < :due_before")
            params["due_before"] = due_before
        cond = " WHERE " + " AND ".join(where) if where else ""
        sql = "SELECT * FROM tasks" + cond + " ORDER BY latest_due, id"  # noqa: S608 條件為固定字串，值走參數
        return [dict(r) for r in self.conn.execute(text(sql), params).mappings()]

    def delayed_count(self, project_id: int | None, override: tuple[int, date] | None = None) -> int:
        """已延期數：latest_due > orig_due 且未完成（spec 4.4）。

        project_id 為 None 時計算全部單點任務。override=(task_id, 新原訂日) 用來試算基準更正後的值。
        """
        scope_sql = "project_id IS NULL" if project_id is None else "project_id = :pid"
        if override is None:
            orig_expr, params = "orig_due", {"pid": project_id}
        else:
            orig_expr = "CASE WHEN id = :oid THEN CAST(:odue AS date) ELSE orig_due END"
            params = {"pid": project_id, "oid": override[0], "odue": override[1]}
        sql = (f"SELECT count(*) FROM tasks WHERE {scope_sql} AND status <> 'done' "  # noqa: S608 固定字串
               f"AND latest_due > {orig_expr}")
        return self.conn.execute(text(sql), params).scalar_one()
