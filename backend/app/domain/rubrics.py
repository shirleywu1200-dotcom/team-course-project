"""星數量表（todo 8.2～8.4、FR-RUB-01～04；Phase 8 SDD 第 3 節）。

版本不可變：只新增新版本，不改舊版本。AI-06 草稿只回給前端，使用者確認後才成為新版本。
"""

import json
import logging
import time

from sqlalchemy import Connection

from app.ai.client import AIClient, AIInvalidOutput, AIUnavailable
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import ai_runs_repo, rubrics_repo
from app.errors import DomainError

log = logging.getLogger(__name__)

NODE = "AI-06"
MAX_ATTEMPTS = 3                 # 比照 AI-01：逾時與格式不符續跑，供應商不可用不續跑
LEVEL_COUNT = 5
MAX_LEVEL_CHARS = 200
V0_LEVELS = ["未達成", "部分達成", "符合預設", "優於預設", "遠超預設"]   # FR-SET-04


def ensure_v0(conn: Connection) -> None:
    rubrics_repo.insert_if_empty(conn, {"version": 0, "levels": V0_LEVELS, "source": "default",
                                        "created_at": get_clock().now()})


def list_rubrics(conn: Connection, active: bool) -> list[dict]:
    ensure_v0(conn)
    return [rubrics_repo.latest(conn)] if active else rubrics_repo.list_all(conn)


def valid_levels(value) -> list[str] | None:
    """剛好 5 句、去頭尾空白後非空且不超過上限；否則回 None。"""
    if not isinstance(value, list) or len(value) != LEVEL_COUNT:
        return None
    if not all(isinstance(s, str) for s in value):
        return None
    levels = [s.strip() for s in value]
    if not all(0 < len(s) <= MAX_LEVEL_CHARS for s in levels):
        return None
    return levels


def interview(db: Database, ai: AIClient, answers: dict) -> list[str]:
    """AI-06：三題回答＋目前量表 → 5 句草稿。最終失敗回 503（spec 5.4、6.6）。"""
    current = db.run(lambda c: list_rubrics(c, active=True)[0]["levels"])
    payload = answers | {"current": current}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        output, levels, error = None, None, None
        try:
            output = ai.call(NODE, payload)
            levels = valid_levels(output.get("levels") if isinstance(output, dict) else None)
            if levels is None:
                error = AIInvalidOutput(NODE)
        except Exception as exc:   # 供應商可能丟出非 AIError 的例外，一律算這次失敗
            error = exc
        run = {"node_id": NODE, "attempt": attempt, "created_at": get_clock().now(),
               "latency_ms": int((time.monotonic() - started) * 1000),
               "status": "ok" if error is None else ai_runs_repo.status_for(error),
               "error": None if error is None else type(error).__name__,
               "raw_output": None if output is None else json.dumps(output, ensure_ascii=False, default=str)}
        db.run(lambda c, r=run: ai_runs_repo.insert_run(c, r))
        if error is None:
            return levels
        log.info("AI-06 失敗 attempt=%s status=%s", attempt, run["status"])
        if isinstance(error, AIUnavailable):
            break
    raise DomainError("AI_UNAVAILABLE")


def confirm(conn: Connection, levels: list[str], answers: dict, draft: list[str] | None) -> dict:
    """確認為新版本（FR-RUB-03）。帶了 AI 草稿時記錄採用情形（SDD Q4）。"""
    ensure_v0(conn)
    now = get_clock().now()
    row = rubrics_repo.insert(conn, {"version": rubrics_repo.latest(conn)["version"] + 1, "levels": levels,
                                     "source": "interview", "interview": answers, "created_at": now})
    if draft is not None:
        ai_runs_repo.insert_feedback(conn, {"node_id": NODE, "target_type": "rubric", "target_id": row["id"],
                                            "outcome": "accepted" if [s.strip() for s in draft] == levels else "edited",
                                            "created_at": now})
    return row
