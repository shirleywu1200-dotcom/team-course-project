"""把資料列轉成 API 輸出格式。日期與時間戳交給 FastAPI 轉成 ISO 8601。"""


def task_out(t: dict) -> dict:
    return {
        "id": t["id"], "project_id": t["project_id"], "title": t["title"], "owner": t["owner_name"],
        "scope": t["scope"], "start": t["start_date"], "orig_due": t["orig_due"], "latest_due": t["latest_due"],
        "delta_days": (t["latest_due"] - t["orig_due"]).days, "status": t["status"], "blocked": t["blocked"],
        "done_date": t["done_date"], "done_when": t["done_when"], "remind": t["remind"],
        "expected_stars": t["expected_stars"], "star_source": t["star_source"], "rubric_id": t["rubric_id"],
        "goal_id": t["goal_id"], "version": t["version"],
    }


def event_out(e: dict) -> dict:
    return {k: e[k] for k in (
        "id", "ts", "project_id", "task_id", "task_title", "kind", "field", "from_value", "to_value",
        "origin", "origin_ref", "source_id", "reason", "note", "delta_days", "mark", "mine",
        "ref_event_id", "batch_id", "actor", "extra")}


def project_out(p: dict) -> dict:
    keys = ("id", "name", "scope", "audience", "line_group_id", "created_at", "updated_at", "archived_at",
            "task_count", "baseline_saved_at")
    return {k: p[k] for k in keys if k in p}


def feedback_out(f: dict) -> dict:
    """completion_feedback 列（spec 5.12 FeedbackOut）。"""
    return {k: f[k] for k in (
        "id", "task_id", "actual_stars", "energy", "invest_vs_expected", "overdue_days", "rubric_id", "created_at")}


def pending_feedback_out(r: dict) -> dict:
    """待補完成回報的一列（spec 5.12 PendingItem）。"""
    return {"task_id": r["task_id"], "title": r["title"], "owner": r["owner_name"], "project_id": r["project_id"],
            "done_date": r["done_date"], "orig_due": r["orig_due"], "overdue_days": r["overdue_days"],
            "expected_stars": r["expected_stars"], "star_source": r["star_source"]}

