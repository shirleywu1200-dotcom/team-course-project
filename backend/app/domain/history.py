"""歷程與甘特的組裝規則（Phase 5，FR-HIS-03～05、FR-PRJ-04、05）。只讀。"""

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import history_repo, projects_repo
from app.db.repo.tasks_repo import TaskRepo

# 依據標籤（Phase 5 SDD Q2）
_ORIGIN_LABELS = {
    "import": "匯入",
    "baseline_correction": "基準更正",
    "manual": "手動",
    "system": "系統",
}


def source_label(origin: str, origin_ref: int | None, batch_id: int | None) -> str:
    if origin == "candidate":
        return f"候選 #{origin_ref}"
    if origin == "bulk":
        return f"整批順延 #{batch_id if batch_id is not None else origin_ref}"
    return _ORIGIN_LABELS[origin]


def _source(row: dict) -> dict:
    purged = row["source_purged_at"] is not None
    quote = None if (row["source_id"] is None or purged) else row["source_excerpt"]
    return {"label": source_label(row["origin"], row["origin_ref"], row["batch_id"]),
            "quote": quote, "purged": purged}


def list_events(conn: Connection, filters: dict, limit: int, offset: int) -> tuple[list[dict], int]:
    """回傳 (事件列, 總筆數)；每列另附 `source` 物件（FR-HIS-04、05）。"""
    if isinstance(filters.get("project_id"), int):
        projects_repo.get(conn, filters["project_id"])   # 不存在回 NOT_FOUND
    rows, total = history_repo.search_events(conn, filters, limit, offset)
    return [r | {"source": _source(r)} for r in rows], total


def gantt_range(tasks: list[dict]) -> dict | None:
    if not tasks:
        return None
    ends = [d for t in tasks for d in (t["orig_due"], t["latest_due"], t["done_date"]) if d is not None]
    return {"from": min(t["start_date"] for t in tasks), "to": max(ends)}


def _gantt_row(t: dict) -> dict:
    return {
        "task_id": t["id"], "title": t["title"], "owner": t["owner_name"], "status": t["status"],
        "start": t["start_date"], "orig_due": t["orig_due"], "latest_due": t["latest_due"],
        "delta_days": (t["latest_due"] - t["orig_due"]).days, "done_date": t["done_date"],
        "blocked": t["blocked"], "version": t["version"],
    }


def project_gantt(conn: Connection, project_id: int) -> dict:
    projects_repo.get(conn, project_id)
    tasks = history_repo.gantt_tasks(conn, project_id)
    return {
        "range": gantt_range(tasks),
        "today": get_clock().today(),
        "summary": {
            "done": sum(1 for t in tasks if t["status"] == "done"),
            "total": len(tasks),
            "delayed": TaskRepo(conn).delayed_count(project_id),
            "open_candidates": history_repo.open_candidate_count(conn, project_id),
        },
        "rows": [_gantt_row(t) for t in tasks],
    }
