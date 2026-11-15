"""資料控制端點（spec 5.15；todo 8.6、8.7，Dev-B）。"""

import json

from fastapi import APIRouter, Depends, Response
from pydantic import StrictBool

from app.api.deps import get_db
from app.api.responses import ExportOut, PurgeOut
from app.api.schemas import Strict
from app.clock import get_clock
from app.db.database import Database
from app.domain import governance

router = APIRouter(tags=["governance"])


class PurgeIn(Strict):
    confirm: StrictBool   # 字串 "true" 或 1 都不算確認（AC-53）


@router.post("/sources/purge", response_model=PurgeOut)
def purge_sources(body: PurgeIn, db: Database = Depends(get_db)):
    return {"purged": db.run(lambda c: governance.purge_all(c, body.confirm))}


@router.post("/export",
             responses={200: {"model": ExportOut, "description": "下載檔（Content-Disposition: attachment）"}})
def export(db: Database = Depends(get_db)):
    """直接回傳下載檔，伺服器不落地存檔（SDD 第 6 節）。"""
    data = db.run(governance.export)
    filename = f"export-{get_clock().now():%Y%m%d-%H%M%S}.json"
    return Response(json.dumps(data, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
