"""目標關聯（FR-GOL-03；spec 5.13；#47 G1）。

關聯由使用者確認：同一交易寫一筆 goal 事件並更新 tasks.goal_id（版本加 1）。改選、改成不關聯都是新增一筆事件。
"""

import json

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import ai_runs_repo, feedback_repo, goal_links_repo, goals_repo
from app.db.repo.tasks_repo import TaskRepo
from app.domain.events import write_event
from app.errors import DomainError


def _check_goal(conn: Connection, goal_id: int | None) -> None:
    """目標必須存在且未封存（B7）；null 代表不關聯。"""
    if goal_id is None:
        return
    try:
        goal = goals_repo.get(conn, goal_id)
    except DomainError:
        raise DomainError("VALIDATION_ERROR", "目標不存在", {"fields": ["goal_id"]}) from None
    if goal["archived_at"] is not None:
        raise DomainError("VALIDATION_ERROR", "目標已封存", {"fields": ["goal_id"]})


_NO_SUGGESTION = object()


def _suggested_goal(conn: Connection, ai_run_id: int | None, task_id: int):
    """讀 AI-03 當初對這個任務的建議（goal_id 或 None）；沒有可比對的建議回 _NO_SUGGESTION。

    建議只從 ai_runs 取，不信前端（比照 AI-07）。ok 那一列存的是驗證後、已排除私人任務的建議。
    """
    if ai_run_id is None:
        return _NO_SUGGESTION
    run = ai_runs_repo.get_run(conn, ai_run_id)
    if not run or run["node_id"] != "AI-03" or run["status"] != "ok":
        raise DomainError("VALIDATION_ERROR", "ai_run_id 不是可用的 AI-03 紀錄", {"fields": ["ai_run_id"]})
    if run["raw_output"] is None:          # 原文已清除（spec 6.7）：照未帶 ai_run_id 處理
        return _NO_SUGGESTION
    items = json.loads(run["raw_output"]).get("items", [])
    return next((i["goal_id"] for i in items if i["task_id"] == task_id), _NO_SUGGESTION)


def _record_feedback(conn: Connection, ai_run_id: int, task_id: int, event_id: int, suggested, final) -> None:
    """detail 只放 id（D-3b 比照）；同一建議只寫一次。"""
    if ai_runs_repo.has_goal_link_feedback(conn, ai_run_id, task_id):
        return
    ai_runs_repo.insert_feedback(conn, {
        "node_id": "AI-03", "target_type": "goal_link", "target_id": event_id,
        "outcome": "accepted" if suggested == final else "changed",
        "detail": {"ai_run_id": ai_run_id, "task_id": task_id, "ai": suggested, "final": final},
        "created_at": get_clock().now(),
    })


def link(conn: Connection, task_id: int, goal_id: int | None, expected_version: int,
         ai_run_id: int | None = None) -> tuple[dict, dict]:
    """確認關聯；回傳 (任務, 事件)。檢查順序依 spec 5.13；帶 ai_run_id 時同一交易寫 AI-03 回饋。"""
    repo = TaskRepo(conn)
    task = repo.get_for_update(task_id, expected_version)       # NOT_FOUND、STALE_VERSION
    if task["status"] != "done" or feedback_repo.get_by_task(conn, task_id) is None:
        raise DomainError("VALIDATION_ERROR", "只有已完成且已填完成回報的任務可以關聯目標", {"fields": ["task_id"]})
    _check_goal(conn, goal_id)
    suggested = _suggested_goal(conn, ai_run_id, task_id)
    decided = goal_links_repo.has_decision(conn, task_id)
    # 第一次選「不關聯」時新舊值都是 null，仍要記下這個決定（spec 5.13）
    if goal_id == task["goal_id"] and decided:
        raise DomainError("NO_CHANGE", details={"task_id": task_id})
    if decided:                    # 回饋只記第一次決定：之後改選不是對建議的回應（spec 5.13）
        suggested = _NO_SUGGESTION
    event = write_event(conn, task_id=task_id, kind="goal", field="goal_id",
                        from_value=_text(task["goal_id"]), to_value=_text(goal_id), origin="manual")
    if suggested is not _NO_SUGGESTION:
        _record_feedback(conn, ai_run_id, task_id, event["id"], suggested, goal_id)
    return repo.update(task_id, {"goal_id": goal_id}), event


def _text(goal_id: int | None) -> str | None:
    return None if goal_id is None else str(goal_id)


def pending(conn: Connection) -> list[dict]:
    """待關聯清單：不呼叫 AI（#47 G3）。"""
    return goal_links_repo.pending(conn)
