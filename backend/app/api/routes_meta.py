"""系統資訊端點（spec 5.12；#47 A5）：前端以伺服器的今天判斷日期，不用瀏覽器時鐘。"""

from fastapi import APIRouter

from app.api.responses import TodayOut
from app.clock import get_clock

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/today", response_model=TodayOut)
def today():
    return {"today": get_clock().today()}
