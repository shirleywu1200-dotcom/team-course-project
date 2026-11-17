"""收件流程（FR-INB-03～08、spec 6.1）。

AI 呼叫可能很久，不放在資料庫交易裡：先用一個交易寫 sources（必要時建 jobs），
再在交易外呼叫 AI-01，每次結果各用一個短交易寫 ai_runs（成功時連同 candidates）。
同步與背景工作共用 `process_sources`。
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import Connection

from app.ai.client import AIClient, AIInvalidOutput, AIUnavailable
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import ai_runs_repo, candidates_repo, jobs_repo, projects_repo, sources_repo
from app.domain import settings
from app.domain.inbox import r2
from app.domain.inbox.parse import Message, parse_text
from app.errors import DomainError

log = logging.getLogger(__name__)

NODE = "AI-01"
MAX_CHARS = 20_000
SYNC_LINE_LIMIT = 30
MAX_ATTEMPTS = 3                 # 1 次＋續跑 2 次（FR-INB-08）
FAILED_MESSAGE = "AI 解析失敗，可在收件匣手動建立任務"
PRIVATE_MESSAGE = "私人專案不送 AI 解析，可在收件匣手動建立任務"


@dataclass
class Outcome:
    ai_status: str                # ok／unavailable／invalid_output（spec 5.3）
    attempts: int
    candidate_ids: list[int] = field(default_factory=list)
    skipped: int = 0
    message: str = FAILED_MESSAGE   # 沒有成功時給使用者看的說明


def _store_sources(conn: Connection, messages: list[Message]) -> tuple[list[int], int]:
    """寫入新訊息，回傳 (新 source id, 重複數)。重複只計數，不合併（FR-INB-04）。"""
    seen = sources_repo.existing_hashes(conn, [m.hash for m in messages])
    now = get_clock().now()
    expires = now + timedelta(days=settings.get_settings(conn)["retention_days"])
    ids, duplicates = [], 0
    for m in messages:
        if m.hash in seen:
            duplicates += 1
            continue
        seen.add(m.hash)
        source_id = sources_repo.insert_if_new(conn, {
            "channel": "paste", "speaker": m.speaker, "spoken_at": m.spoken_at, "excerpt": m.text,
            "excerpt_hash": m.hash, "received_at": now, "expires_at": expires})
        if source_id is None:
            duplicates += 1
        else:
            ids.append(source_id)
    return ids, duplicates


def ingest(db: Database, ai: AIClient, text: str, project_id: int | None) -> dict:
    if len(text) > MAX_CHARS:
        raise DomainError("PAYLOAD_TOO_LARGE", details={"max_chars": MAX_CHARS})
    parsed = parse_text(text)

    def stage(conn: Connection):
        if project_id is not None:
            projects_repo.get(conn, project_id)
        source_ids, duplicates = _store_sources(conn, parsed.messages)
        job = None
        if parsed.line_count > SYNC_LINE_LIMIT and source_ids:
            now = get_clock().now()
            job = jobs_repo.insert(conn, {
                "kind": "ingest", "status": "queued", "created_at": now, "updated_at": now,
                "payload": {"source_ids": source_ids, "project_id": project_id, "duplicates": duplicates,
                            "unparsed_lines": parsed.unparsed_lines}})
        return source_ids, duplicates, job

    source_ids, duplicates, job = db.run(stage)
    if job is not None:
        return {"mode": "async", "job_id": job["id"], "status": "queued"}

    outcome = (process_sources(db, ai, source_ids, project_id) if source_ids
               else Outcome(ai_status="ok", attempts=0))
    result = result_summary(outcome, duplicates, parsed.unparsed_lines)
    return {"mode": "sync", "ai_status": outcome.ai_status, "result": result,
            "candidate_ids": outcome.candidate_ids}


def result_summary(outcome: Outcome, duplicates: int, unparsed_lines: list[int]) -> dict:
    return {"created": len(outcome.candidate_ids), "skipped": outcome.skipped + len(unparsed_lines),
            "duplicates": duplicates, "unparsed_lines": unparsed_lines}


def _payload(conn: Connection, source_ids: list[int], project_id: int | None) -> tuple[dict, dict, set[int]]:
    # 排隊期間原文可能已被清除（FR-GOV-01、03），這些訊息不送 AI，計入略過
    sources = [s for s in sources_repo.get_many(conn, source_ids) if s["excerpt"] is not None]
    tasks = candidates_repo.tasks_for_matching(conn, project_id)
    payload = {
        "today": get_clock().today().isoformat(),
        "messages": [{"ref": s["id"], "speaker": s["speaker"], "spoken_at": s["spoken_at"], "text": s["excerpt"]}
                     for s in sources],
        "tasks": [{"id": t["id"], "title": t["title"], "owner": t["owner_name"],
                   "latest_due": t["latest_due"].isoformat()} for t in tasks],
    }
    return payload, {s["id"]: s["excerpt"] for s in sources}, {t["id"] for t in tasks}


def process_sources(db: Database, ai: AIClient, source_ids: list[int], project_id: int | None, *,
                    job_id: int | None = None, attempts_done: int = 0) -> Outcome:
    """呼叫 AI-01 並把結果寫成 open 候選；失敗則續跑，總嘗試次數不超過 MAX_ATTEMPTS。"""
    if project_id is not None and db.run(lambda c: projects_repo.get(c, project_id))["scope"] == "private":
        # 私人專案的原文不送 AI（資安規則 2、PR #20 B1）；原文已存，可在收件匣手動建任務
        return Outcome("unavailable", attempts_done, skipped=len(source_ids), message=PRIVATE_MESSAGE)
    payload, texts, task_ids = db.run(lambda c: _payload(c, source_ids, project_id))
    ai_status, attempt = "unavailable", attempts_done
    while attempt < MAX_ATTEMPTS:
        attempt += 1
        if job_id is not None:
            db.run(lambda c, n=attempt: jobs_repo.update(c, job_id, {"attempts": n, "updated_at": get_clock().now()}))
        started = time.monotonic()
        output, drafts, error = None, [], None
        try:
            output = ai.call(NODE, payload)
            drafts = r2.apply(output, texts, task_ids, get_clock().today())
        except Exception as exc:   # 供應商可能丟出非 AIError 的例外，一律算這次失敗（FR-INB-08）
            error = exc
        run = {"node_id": NODE, "job_id": job_id, "attempt": attempt, "created_at": get_clock().now(),
               "latency_ms": int((time.monotonic() - started) * 1000),
               "status": "ok" if error is None else ai_runs_repo.status_for(error),
               "error": None if error is None else type(error).__name__,
               "raw_output": None if output is None else json.dumps(output, ensure_ascii=False, default=str)}
        if error is None:
            ids = db.run(lambda c, r=run, d=drafts: _save_candidates(c, r, d, project_id))
            return Outcome("ok", attempt, ids, skipped=len(source_ids) - len(ids))
        db.run(lambda c, r=run: ai_runs_repo.insert_run(c, r))
        log.info("AI-01 失敗 job=%s attempt=%s status=%s", job_id, attempt, run["status"])
        ai_status = "invalid_output" if isinstance(error, AIInvalidOutput) else "unavailable"
        if isinstance(error, AIUnavailable):
            break   # 供應商不可用時續跑沒有意義（續跑只針對逾時與不合格式）
    return Outcome(ai_status, attempt, skipped=len(source_ids))


def _save_candidates(conn: Connection, run: dict, drafts: list[r2.Draft], project_id: int | None) -> list[int]:
    """候選記住收件時的專案，建任務時由伺服器帶入（PR #20 B5）。"""
    run_id = ai_runs_repo.insert_run(conn, run)["id"]
    now = get_clock().now()
    return [candidates_repo.insert(conn, {
        "source_id": d.source_id, "kind": d.kind, "certainty": d.certainty, "task_id": d.task_id,
        "proposed": d.proposed, "suggest": d.suggest, "state": "open", "ai_run_id": run_id, "created_at": now,
        "project_id": project_id,
    })["id"] for d in drafts]
