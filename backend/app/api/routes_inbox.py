"""收件與候選端點（spec 5.11；todo Phase 7，Dev-B）。`/webhooks/line`（7.12）本版不做。"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import Field

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.responses import CandidateListOut, DecideOut, IngestAsyncOut, IngestJobOut, IngestSyncOut
from app.api.schemas import Strict, Versioned
from app.api.serialize import event_out, task_out
from app.db.database import Database
from app.db.repo import candidates_repo, jobs_repo
from app.domain.inbox import confirm as cand
from app.domain.inbox.ingest import ingest as run_ingest

router = APIRouter(tags=["inbox"])

IngestOut = Annotated[IngestSyncOut | IngestAsyncOut, Field(discriminator="mode")]


class IngestIn(Strict):
    text: str
    project_id: int | None = None


class ConfirmIn(Versioned):
    new_due: date | None = None


class CreateTaskIn(Strict):
    title: str
    due: date
    owner: str | None = None
    project_id: int | None = None


def candidate_out(c: dict) -> dict:
    task = None if c["task_id"] is None else {
        "id": c["task_id"], "title": c["task_title"], "latest_due": c["task_latest_due"],
        "orig_due": c["task_orig_due"], "version": c["task_version"]}
    return {"id": c["id"], "kind": c["kind"], "certainty": c["certainty"], "state": c["state"], "task": task,
            "proposed": c["proposed"], "quote": None if c["purged_at"] else c["excerpt"],
            "speaker": c["speaker"], "spoken_at": c["spoken_at"], "note": c["note"], "suggest": c["suggest"]}


def _detail(db: Database, ids: list[int]) -> list[dict]:
    return [candidate_out(c) for c in db.run(lambda c: candidates_repo.get_detail_many(c, ids))]


def _decided(db: Database, out: dict) -> dict:
    """確認類端點的共同輸出：候選（含原句）＋任務＋事件。"""
    body = {k: v for k, v in out.items() if k not in ("candidate", "task", "event")}
    body["candidate"] = _detail(db, [out["candidate"]["id"]])[0]
    if "task" in out:
        body["task"] = task_out(out["task"])
    if "event" in out:
        body["event"] = event_out(out["event"])
    return body


@router.post("/ingest", response_model=IngestOut)
def ingest(body: IngestIn, db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    out = run_ingest(db, ai, body.text, body.project_id)
    if out["mode"] == "sync":
        out["candidates"] = _detail(db, out.pop("candidate_ids"))
    return out


@router.get("/ingest/jobs/{job_id}", response_model=IngestJobOut)
def get_job(job_id: int, db: Database = Depends(get_db)):
    job = db.run(lambda c: jobs_repo.get(c, job_id))
    return {"id": job["id"], "status": job["status"], "attempts": job["attempts"], "result": job["result"],
            "error": job["error"]}


@router.get("/candidates", response_model=CandidateListOut, response_model_exclude_unset=True)
def list_candidates(state: Literal["open", "confirmed", "ignored"] = "open", db: Database = Depends(get_db)):
    items = [candidate_out(c) for c in db.run(lambda c: candidates_repo.list_detail(c, state))]
    return {"items": items, "total": len(items)}


@router.post("/candidates/{candidate_id}/confirm", response_model=DecideOut, response_model_exclude_unset=True)
def confirm(candidate_id: int, body: ConfirmIn, db: Database = Depends(get_db)):
    return _decided(db, db.run(lambda c: cand.confirm(c, candidate_id, body.new_due, body.expected_version)))


@router.post("/candidates/{candidate_id}/clarify", response_model=DecideOut, response_model_exclude_unset=True)
def clarify(candidate_id: int, body: ConfirmIn, db: Database = Depends(get_db)):
    return _decided(db, db.run(lambda c: cand.clarify(c, candidate_id, body.new_due, body.expected_version)))


@router.post("/candidates/{candidate_id}/create-task", status_code=201, response_model=DecideOut,
             response_model_exclude_unset=True)
def create_task(candidate_id: int, body: CreateTaskIn, db: Database = Depends(get_db)):
    return _decided(db, db.run(lambda c: cand.create_task_from(c, candidate_id, **body.model_dump(exclude_unset=True))))


@router.post("/candidates/{candidate_id}/ignore", response_model=DecideOut, response_model_exclude_unset=True)
def ignore(candidate_id: int, db: Database = Depends(get_db)):
    return _decided(db, db.run(lambda c: cand.ignore(c, candidate_id)))
