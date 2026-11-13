"""專案、整批順延端點（spec 5.5、5.9）。甘特與歷程查詢屬 Phase 5（Dev-B）。"""

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.api.schemas import BulkShift, ProjectCreate, ProjectPatch
from app.api.serialize import event_out, project_out
from app.db.database import Database
from app.db.repo import projects_repo
from app.domain import bulk, projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(include_archived: bool = False, db: Database = Depends(get_db)):
    items = db.run(lambda c: projects_repo.list_all(c, include_archived))
    return {"items": [project_out(p) for p in items], "total": len(items)}


@router.post("", status_code=201)
def create_project(body: ProjectCreate, db: Database = Depends(get_db)):
    return project_out(db.run(lambda c: projects.create_project(c, **body.model_dump())))


@router.get("/{project_id}")
def get_project(project_id: int, db: Database = Depends(get_db)):
    return project_out(db.run(lambda c: projects.get_project_detail(c, project_id)))


@router.patch("/{project_id}")
def patch_project(project_id: int, body: ProjectPatch, db: Database = Depends(get_db)):
    project, events = db.run(lambda c: projects.update_project(c, project_id, body.model_dump(exclude_unset=True)))
    return {"project": project_out(project), "changes": [event_out(e) for e in events]}


@router.post("/{project_id}/archive")
def archive_project(project_id: int, db: Database = Depends(get_db)):
    return project_out(db.run(lambda c: projects.archive_project(c, project_id)))


def _items(body: BulkShift) -> list[dict]:
    return [i.model_dump() for i in body.items]


@router.post("/{project_id}/bulk-shift/preview")
def bulk_preview(project_id: int, body: BulkShift, db: Database = Depends(get_db)):
    return db.run(lambda c: bulk.preview_bulk(c, project_id, _items(body), body.days, body.reason))


@router.post("/{project_id}/bulk-shift/commit")
def bulk_commit(project_id: int, body: BulkShift, db: Database = Depends(get_db)):
    return db.run(lambda c: bulk.commit_bulk(c, project_id, _items(body), body.days, body.reason, body.note,
                                             body.mark, body.defer_mark))
