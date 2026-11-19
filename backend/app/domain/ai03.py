"""AI-03 目標關聯建議的輸入與輸出格式（FR-GOL-03；spec 5.3a〈AI-03〉、5.13）。

格式以 spec 5.3a 為準（2026-11-18 #72、#73 定案；契約擁有者 Dev-B）。格式要改時先改 spec，再改這個檔。
- 輸入只放白名單欄位：目標的 id、類型、名稱、期間，任務的 id、名稱、完成日；私人任務不送（資安規則 2）。
- 輸出驗證分三步：先查結構（任一項不合整次 invalid_output），再丟不在 payload 的項目，最後同一任務留第一項。
"""

from app.ai.client import AIInvalidOutput

NODE = "AI-03"
MAX_TASKS = 20          # 一次最多送 20 筆待關聯任務（#72）
REASON_MAX_CHARS = 200


def build_payload(goals: list[dict], tasks: list[dict]) -> dict:
    """goals：未封存目標；tasks：工作範圍的待關聯任務（已依完成日由新到舊）。只取允許的欄位。"""
    return {
        "goals": [{"goal_id": g["id"], "type": g["type"], "title": g["title"], "period": g["period"]} for g in goals],
        "tasks": [{"task_id": t["task_id"], "title": t["title"], "done_date": t["done_date"].isoformat()}
                  for t in tasks[:MAX_TASKS]],
    }


def _is_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _well_formed(item) -> bool:
    if not isinstance(item, dict) or not _is_id(item.get("task_id")):
        return False
    goal_id, reason = item.get("goal_id", 0.5), item.get("reason")   # 缺 goal_id 用 0.5 讓檢查失敗
    if not (goal_id is None or _is_id(goal_id)):
        return False
    return isinstance(reason, str) and len(reason) <= REASON_MAX_CHARS and "\x00" not in reason


def parse_output(output, payload: dict) -> list[dict]:
    """回傳驗證後的建議；結構不合丟 AIInvalidOutput（訊息不帶內容）。"""
    if not isinstance(output, dict) or not isinstance(output.get("items"), list):
        raise AIInvalidOutput(NODE)
    if not all(_well_formed(item) for item in output["items"]):
        raise AIInvalidOutput(NODE)
    task_ids = {t["task_id"] for t in payload["tasks"]}
    goal_ids = {g["goal_id"] for g in payload["goals"]}
    items: list[dict] = []
    seen: set[int] = set()
    for raw in output["items"]:
        if raw["task_id"] not in task_ids or (raw["goal_id"] is not None and raw["goal_id"] not in goal_ids):
            continue                                   # 不在 payload：整項丟棄，不算錯誤（#73）
        if raw["task_id"] in seen:
            continue                                   # 同一任務只留第一項（#73）
        seen.add(raw["task_id"])
        items.append({"task_id": raw["task_id"], "goal_id": raw["goal_id"], "reason": raw["reason"]})
    return items
