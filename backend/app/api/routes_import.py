"""專案匯入端點（spec 5.6；todo Phase 6，Dev-B）。在 main.py 中排在專案路由之前註冊。"""

from typing import Literal

from fastapi import APIRouter, Depends

from app.ai.client import AIClient
from app.api.deps import get_ai, get_db
from app.api.schemas import Strict
from app.db.database import Database
from app.domain.imports import service

router = APIRouter(prefix="/projects/import", tags=["import"])

Target = Literal["new"] | int


class ColumnMap(Strict):
    title: int
    end: int
    owner: int | None = None
    start: int | None = None


class PreviewIn(Strict):
    text: str
    target: Target = "new"
    new_name: str | None = None
    column_map: ColumnMap | None = None


class CommitRow(Strict):
    index: int
    title: str | None = None
    owner: str | None = None
    start: str | None = None
    end: str | None = None
    skip: bool = False


class CommitIn(Strict):
    target: Target = "new"
    new_name: str | None = None
    rows: list[CommitRow]


@router.post("/preview")
def preview(body: PreviewIn, db: Database = Depends(get_db), ai: AIClient = Depends(get_ai)):
    cmap = body.column_map.model_dump() if body.column_map else None
    return service.preview(db, ai, body.text, body.target, cmap)


@router.post("/commit", status_code=201)
def commit(body: CommitIn, db: Database = Depends(get_db)):
    rows = [r.model_dump() for r in body.rows]
    return db.run(lambda c: service.commit(c, body.target, body.new_name, rows))
