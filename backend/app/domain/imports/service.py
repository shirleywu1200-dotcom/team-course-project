"""匯入 preview 與 commit（FR-IMP-01～07，todo 6.4～6.6）。

preview 不寫業務資料（只寫 AI-07 的 ai_runs）。commit 不相信前端的診斷結果，每列重新驗證，
全部寫入在呼叫端的單一交易內完成（Database.run），任一步失敗就整筆回滾。
"""

import json
import logging
import time

from sqlalchemy import Connection

from app.ai.client import AIClient
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import ai_runs_repo, misc_repo, projects_repo
from app.db.repo.tasks_repo import TaskRepo
from app.domain.events import write_event
from app.domain.imports import table
from app.domain.imports.diagnose import Row, diagnose
from app.domain.projects import create_project
from app.errors import DomainError

log = logging.getLogger(__name__)
NODE = "AI-07"
AI_SAMPLE_ROWS = 2


def _cell(row: list[str], idx: int | None) -> str:
    return row[idx] if idx is not None and idx < len(row) else ""


def _existing_target(conn: Connection, target) -> dict | None:
    """target="new" 回 None；既有專案確認存在且未封存。"""
    if target == "new":
        return None
    project = projects_repo.get(conn, target)
    if project["archived_at"] is not None:
        raise DomainError("VALIDATION_ERROR", "專案已封存", {"fields": ["target"]})
    return project


def _ai_map(db: Database, ai: AIClient, header: list[str], data: list[list[str]]) -> tuple[dict | None, str]:
    """AI-07：只呼叫一次、不重試（SDD 2.2）。回傳 (合法的對應或 None, ai_runs.status)。"""
    started = time.monotonic()
    output, status, error = None, "ok", None
    try:
        output = ai.call(NODE, {"headers": header, "samples": data[:AI_SAMPLE_ROWS]})
        mapping = table.valid_map(output, len(header))
        if mapping is None:
            status = "invalid_output"
    except Exception as exc:   # 任何供應商錯誤都走退路：使用者手動指定
        mapping, error, status = None, type(exc).__name__, ai_runs_repo.status_for(exc)
    run = {"node_id": NODE, "status": status, "attempt": 1, "created_at": get_clock().now(),
           "latency_ms": int((time.monotonic() - started) * 1000), "error": error,
           "raw_output": None if output is None else json.dumps(output, ensure_ascii=False, default=str)}
    db.run(lambda c: ai_runs_repo.insert_run(c, run))
    if mapping is None:
        log.info("AI-07 失敗 status=%s", status)
    return mapping, status


def preview(db: Database, ai: AIClient, text: str, target, column_map: dict | None) -> dict:
    header, data = table.split_table(text)
    project = db.run(lambda c: _existing_target(c, target))
    scope = project["scope"] if project else "work"   # 新專案預設工作範圍
    ai_status = "ok"
    if column_map is not None:
        mapping = table.valid_map(column_map, len(header))
        if mapping is None:
            raise DomainError("VALIDATION_ERROR", "欄位對應不正確", {"fields": ["column_map"]})
        mapped_by = "manual"
    else:
        mapping, mapped_by = table.map_by_rule(header), "rule"
        if not table.is_complete(mapping):
            # 私人範圍不送 AI（Q4）；spec 5.3 的 ai_status 沒有「刻意不呼叫」的值，沿用 unavailable
            ai_map, run_status = (None, "error") if scope == "private" else _ai_map(db, ai, header, data)
            ai_status = "ok" if ai_map else ("invalid_output" if run_status == "invalid_output" else "unavailable")
            mapping, mapped_by = (ai_map, "ai") if ai_map else (mapping, None)

    out = {"ai_status": ai_status, "header": header, "column_map": mapping | {"mapped_by": mapped_by}}
    if mapped_by is None:   # 必填欄位對應不到，無法診斷；等使用者手動指定
        return out | {"rows": [], "summary": {"importable": 0, "blocking": 0}}
    today, seen = get_clock().today(), set()
    rows = [diagnose(i, _cell(r, mapping["title"]), _cell(r, mapping["owner"]), _cell(r, mapping["start"]),
                     _cell(r, mapping["end"]), today, seen) for i, r in enumerate(data)]
    blocking = sum(r.blocking for r in rows)
    return out | {"rows": [r.out() for r in rows],
                  "summary": {"importable": len(rows) - blocking, "blocking": blocking}}


def _revalidate(rows: list[dict]) -> tuple[list[Row], int]:
    today, seen = get_clock().today(), set()
    checked, skipped, bad = [], 0, []
    for r in rows:
        if r.get("skip"):
            skipped += 1
            continue
        row = diagnose(r["index"], r.get("title"), r.get("owner"), r.get("start"), r.get("end"), today, seen)
        if row.blocking:
            bad.append(row.index)
        checked.append(row)
    if bad:
        raise DomainError("VALIDATION_ERROR", "有未處理的錯誤列", {"rows": bad})
    if not checked:
        raise DomainError("EMPTY_SELECTION", "沒有可匯入的列")
    return checked, skipped


def commit(conn: Connection, target, new_name: str | None, rows: list[dict]) -> dict:
    """在呼叫端的交易內執行；任何例外都讓整筆回滾（AC-32）。"""
    checked, skipped = _revalidate(rows)
    project = _existing_target(conn, target) or create_project(conn, name=new_name or "")
    repo, rubric_id = TaskRepo(conn), misc_repo.active_rubric_id(conn)
    task_ids = [repo.insert({
        "project_id": project["id"], "title": r.title, "owner_name": r.owner, "scope": project["scope"],
        "start_date": r.start, "orig_due": r.end, "latest_due": r.end, "star_source": "import_default",
        "rubric_id": rubric_id,
    })["id"] for r in checked]
    event = write_event(conn, project_id=project["id"], kind="baseline", field="import", origin="import",
                        to_value=str(len(task_ids)),
                        extra={"created": len(task_ids), "skipped": skipped, "task_ids": task_ids})
    return {"project_id": project["id"], "created": len(task_ids), "skipped": skipped, "event_id": event["id"]}
