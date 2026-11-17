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


def _ai_map(db: Database, ai: AIClient, header: list[str], data: list[list[str]]) -> tuple[dict | None, str, int]:
    """AI-07：只呼叫一次、不重試（SDD 2.2）。回傳 (合法的對應或 None, ai_runs.status, ai_runs.id)。"""
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
    run_id = db.run(lambda c: ai_runs_repo.insert_run(c, run))["id"]
    if mapping is None:
        log.info("AI-07 失敗 status=%s", status)
    return mapping, status, run_id


def preview(db: Database, ai: AIClient, text: str, target, column_map: dict | None) -> dict:
    header, data = table.split_table(text)
    project = db.run(lambda c: _existing_target(c, target))
    scope = project["scope"] if project else "work"   # 新專案預設工作範圍
    ai_status, extra = "ok", {}
    if column_map is not None:
        mapping = table.valid_map(column_map, len(header))
        if mapping is None:
            raise DomainError("VALIDATION_ERROR", "欄位對應不正確", {"fields": ["column_map"]})
        mapped_by = "manual"
    else:
        mapping, mapped_by = table.map_by_rule(header), "rule"
        if not table.is_complete(mapping):
            # 私人範圍不送 AI（Q4）；spec 5.3 的 ai_status 沒有「刻意不呼叫」的值，沿用 unavailable
            ai_map, run_status, run_id = (None, "error", None) if scope == "private" else _ai_map(db, ai, header, data)
            ai_status = "ok" if ai_map else ("invalid_output" if run_status == "invalid_output" else "unavailable")
            mapping, mapped_by = (ai_map, "ai") if ai_map else (mapping, None)
            if ai_map:   # 12.7 D-3：commit 時帶回，伺服器才能比對使用者有沒有改 AI 的對應
                extra = {"ai_run_id": run_id}

    out = {"ai_status": ai_status, "header": header, "column_map": mapping | {"mapped_by": mapped_by} | extra}
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


def _ai_suggestion(conn: Connection, ai_run_id: int | None, column_map: dict | None) -> dict | None:
    """12.7 D-3：讀 AI-07 當初建議的對應；未帶 ai_run_id 回 None。AI 建議只從資料庫取，不信前端。"""
    if (ai_run_id is None) != (column_map is None):
        raise DomainError("VALIDATION_ERROR", "ai_run_id 與 column_map 要一起送",
                          {"fields": ["ai_run_id", "column_map"]})
    if ai_run_id is None:
        return None
    run = ai_runs_repo.get_run(conn, ai_run_id)
    if not run or run["node_id"] != NODE or run["status"] != "ok":
        raise DomainError("VALIDATION_ERROR", "ai_run_id 不是可用的 AI-07 紀錄", {"fields": ["ai_run_id"]})
    if run["raw_output"] is None:   # preview 之後原文被清除（PR #20 B2）：照未帶 ai_run_id 處理
        return None
    # status='ok' 代表 preview 時已通過 valid_map；這裡只取四個欄位，AI 夾帶的文字不會進 detail（D-3b）
    output = json.loads(run["raw_output"])
    return {f: output.get(f) for f in table.FIELDS}


def _record_map_feedback(conn: Connection, event_id: int, ai_run_id: int, suggested: dict, final: dict) -> None:
    """一次匯入一筆回饋，錨定 baseline 事件（D-3a）；同一 ai_run_id 只寫一次（D-3c）。"""
    if ai_runs_repo.has_feedback_for_run(conn, NODE, ai_run_id):
        return
    ai_runs_repo.insert_feedback(conn, {
        "node_id": NODE, "target_type": "import_map", "target_id": event_id,
        "outcome": "accepted" if suggested == final else "changed",
        "detail": {"ai_run_id": ai_run_id, "ai": suggested, "final": final}, "created_at": get_clock().now(),
    })


def commit(conn: Connection, target, new_name: str | None, rows: list[dict],
           ai_run_id: int | None = None, column_map: dict | None = None) -> dict:
    """在呼叫端的交易內執行；任何例外都讓整筆回滾（AC-32）。"""
    if len(rows) > table.MAX_ROWS:   # 直接呼叫 commit 也不能繞過 preview 的上限（FR-IMP-01）
        raise DomainError("PAYLOAD_TOO_LARGE", details={"max_rows": table.MAX_ROWS})
    suggested = _ai_suggestion(conn, ai_run_id, column_map)
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
    if suggested is not None:
        _record_map_feedback(conn, event["id"], ai_run_id, suggested, column_map)
    return {"project_id": project["id"], "created": len(task_ids), "skipped": skipped, "event_id": event["id"]}
