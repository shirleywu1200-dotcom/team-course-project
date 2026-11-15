"""任務、日期調整、基準更正端點（spec 5.7、5.10）。

suggest-stars（AI-02）待 D-01 決議，屬 Dev-C 9.11，不在此實作。
"""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_db
from app.api.responses import (
    AdjustDueOut,
    BaselinePreviewOut,
    CompleteOut,
    TaskDetailOut,
    TaskEventOut,
    TaskListOut,
    TaskOut,
)
from app.api.schemas import (
    AdjustDue,
    BaselineCommit,
    BaselinePreview,
    BlockChange,
    Complete,
    OwnerChange,
    StatusChange,
    TaskCreate,
)
from app.api.serialize import event_out, task_out
from app.db.database import Database
from app.db.repo.tasks_repo import TaskRepo
from app.domain import baseline, tasks
from app.domain.due import adjust_due

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListOut)
def list_tasks(project_id: str | None = Query(None, pattern=r"^(none|\d+)$"), owner: str | None = None,
               status: str | None = None, scope: str | None = None, due_before: date | None = None,
               db: Database = Depends(get_db)):
    single = project_id == "none"
    pid = int(project_id) if project_id not in (None, "none") else None
    items = db.run(lambda c: TaskRepo(c).list(project_id=pid, single_only=single, owner=owner, status=status,
                                             scope=scope, due_before=due_before))
    return {"items": [task_out(t) for t in items], "total": len(items)}


@router.post("", status_code=201, response_model=TaskOut)
def create_task(body: TaskCreate, db: Database = Depends(get_db)):
    return task_out(db.run(lambda c: tasks.create_task(c, **body.model_dump())))


@router.get("/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: int, db: Database = Depends(get_db)):
    detail = db.run(lambda c: tasks.get_task_detail(c, task_id))
    return {"task": task_out(detail["task"]), "events": [event_out(e) for e in detail["events"]]}


@router.patch("/{task_id}/owner", response_model=TaskEventOut)
def change_owner(task_id: int, body: OwnerChange, db: Database = Depends(get_db)):
    task, event = db.run(lambda c: tasks.change_owner(c, task_id, body.owner, body.expected_version))
    return {"task": task_out(task), "event": event_out(event)}


@router.post("/{task_id}/status", response_model=TaskEventOut)
def set_status(task_id: int, body: StatusChange, db: Database = Depends(get_db)):
    task, event = db.run(lambda c: tasks.set_status(c, task_id, body.status, body.expected_version))
    return {"task": task_out(task), "event": event_out(event)}


@router.post("/{task_id}/block", response_model=TaskEventOut)
def set_blocked(task_id: int, body: BlockChange, db: Database = Depends(get_db)):
    task, event = db.run(lambda c: tasks.set_blocked(c, task_id, body.blocked, body.expected_version))
    return {"task": task_out(task), "event": event_out(event)}


@router.post("/{task_id}/complete", response_model=CompleteOut)
def complete(task_id: int, body: Complete, db: Database = Depends(get_db)):
    task, event, required = db.run(lambda c: tasks.complete_task(c, task_id, body.expected_version, body.done_date))
    return {"task": task_out(task), "event": event_out(event), "feedback_required": required}


@router.post("/{task_id}/adjust-due", response_model=AdjustDueOut)
def adjust(task_id: int, body: AdjustDue, db: Database = Depends(get_db)):
    r = db.run(lambda c: adjust_due(c, task_id, body.new_due, body.expected_version, body.reason, body.note,
                                    body.mark, body.defer_mark, origin="manual"))
    return {"task": task_out(r.task), "event": event_out(r.event), "warnings": r.warnings,
            "needs_mark": r.needs_mark}


@router.post("/{task_id}/baseline-correction/preview", response_model=BaselinePreviewOut)
def baseline_preview(task_id: int, body: BaselinePreview, db: Database = Depends(get_db)):
    return db.run(lambda c: baseline.preview_baseline(c, task_id, body.new_orig_due, body.type, body.reason,
                                                      body.expected_version))


@router.post("/{task_id}/baseline-correction/commit", response_model=TaskEventOut)
def baseline_commit(task_id: int, body: BaselineCommit, db: Database = Depends(get_db)):
    task, event = db.run(lambda c: baseline.commit_baseline(c, task_id, body.confirmation_token, body.ack))
    return {"task": task_out(task), "event": event_out(event)}
