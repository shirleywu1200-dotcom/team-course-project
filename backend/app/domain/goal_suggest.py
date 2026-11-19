"""POST /goal-links/suggest：呼叫 AI-03 取得關聯建議（FR-GOL-03；spec 5.13；#47 G3）。

流程：讀資料（一個交易）→ 在交易外呼叫 AI → 每次嘗試各寫一列 ai_runs。建議不存檔，只放在這次回應；
status='ok' 那一列的 raw_output 存驗證後的建議（與回應相同），確認關聯時據以寫回饋。
"""

import json
import logging
import time

from app.ai.client import DEFAULT_TIMEOUT_S, AIClient, AIInvalidOutput, AIUnavailable
from app.clock import get_clock
from app.db.database import Database
from app.db.repo import ai_runs_repo, goal_links_repo, goals_repo
from app.domain import ai03

log = logging.getLogger("g4")
MAX_ATTEMPTS = 3   # 任何失敗都算一次、最多 3 次；AI 不可用立刻停（spec 5.3a「重試比照 AI-01」）


def _fallback(ai_status: str = "unavailable") -> dict:
    """退路回應：沒有建議，由使用者自己選（AC-50）。每次產生新的 dict。"""
    return {"ai_status": ai_status, "ai_run_id": None, "items": []}


def _collect(conn) -> dict:
    goals = goals_repo.list_all(conn, include_archived=False)
    tasks = [t for t in goal_links_repo.pending(conn) if t["scope"] == "work"]   # 私人任務不送（資安規則 2）
    return ai03.build_payload(goals, tasks)


def suggest(db: Database, ai: AIClient) -> dict:
    payload = db.run(_collect)
    if not payload["goals"] or not payload["tasks"]:
        return _fallback()            # 依規則刻意不呼叫（spec 5.3），不寫 ai_runs
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        output, items, error = None, None, None
        try:
            output = ai.call(ai03.NODE, payload, timeout_s=DEFAULT_TIMEOUT_S)
            items = ai03.parse_output(output, payload)
        except Exception as exc:   # noqa: BLE001 供應商可能丟出任何例外；AI 失敗一律走退路（spec 5.3）
            error = exc
        status = "ok" if error is None else ai_runs_repo.status_for(error)
        stored = {"items": items} if error is None else output
        run = {"node_id": ai03.NODE, "status": status, "attempt": attempt, "created_at": get_clock().now(),
               "latency_ms": int((time.monotonic() - started) * 1000),
               "error": None if error is None else type(error).__name__,
               "raw_output": None if stored is None else json.dumps(stored, ensure_ascii=False, default=str)}
        run_id = db.run(lambda c, r=run: ai_runs_repo.insert_run(c, r))["id"]
        if error is None:
            return {"ai_status": "ok", "ai_run_id": run_id, "items": items}
        log.info("AI-03 失敗 attempt=%s status=%s", attempt, status)
        if isinstance(error, AIUnavailable):
            break
    # 最終狀態以最後一次嘗試為準：格式不合為 invalid_output，其餘為 unavailable（比照 AI-05）
    last_invalid = isinstance(error, AIInvalidOutput)
    return _fallback("invalid_output" if last_invalid else "unavailable")
