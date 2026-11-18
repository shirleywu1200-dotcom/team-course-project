"""候選處理（FR-INB-10～15、todo 7.6～7.9）。

任務的寫入只經 Dev-A 的 adjust_due／complete_task／set_blocked／create_task；
候選狀態與任務寫入在同一個交易內，任一步失敗（例如 TASK_DONE）就整筆回滾，候選維持 open。
原因與註記一律留空（FR-DUE-05a、AC-12a）。
"""

from datetime import date

from sqlalchemy import Connection

from app.clock import get_clock
from app.db.repo import ai_runs_repo, candidates_repo, projects_repo, sources_repo
from app.domain import tasks
from app.domain.due import adjust_due
from app.domain.inbox.ingest import NODE
from app.errors import DomainError

_ENDPOINT_FOR = {"unclear": "clarify", "unmatched": "create-task"}


def _load_open(conn: Connection, candidate_id: int, kinds: set[str]) -> dict:
    cand = candidates_repo.get_for_update(conn, candidate_id)
    if cand["state"] != "open":
        raise DomainError("CANDIDATE_NOT_OPEN", details={"candidate_id": candidate_id})
    if cand["kind"] not in kinds:
        raise DomainError("VALIDATION_ERROR", "此種類的候選請用專用端點",
                          {"fields": ["kind"], "use": _ENDPOINT_FOR.get(cand["kind"], "confirm")})
    return cand


def _close(conn: Connection, cand: dict, state: str, decision: str, outcome: str, detail: dict | None = None) -> dict:
    now = get_clock().now()
    ai_runs_repo.insert_feedback(conn, {"node_id": NODE, "target_type": "candidate", "target_id": cand["id"],
                                        "outcome": outcome, "detail": detail, "created_at": now})
    return candidates_repo.update(conn, cand["id"], {"state": state, "decision": decision, "decided_at": now})


def _apply(conn: Connection, cand: dict, kind: str, new_due: date | None, expected_version: int) -> dict:
    ref = {"origin": "candidate", "origin_ref": cand["id"], "source_id": cand["source_id"]}
    if kind == "delay":
        if new_due is None:
            raise DomainError("VALIDATION_ERROR", "請指定新日期", {"fields": ["new_due"]})
        res = adjust_due(conn, cand["task_id"], new_due, expected_version, None, None, None, True, **ref)
        return {"task": res.task, "event": res.event, "needs_mark": res.needs_mark, "warnings": res.warnings}
    if kind == "done":
        task, event, feedback_required = tasks.complete_task(conn, cand["task_id"], expected_version, **ref)
        return {"task": task, "event": event, "feedback_required": feedback_required}
    if kind == "stuck":
        task, event = tasks.set_blocked(conn, cand["task_id"], True, expected_version, **ref)
        return {"task": task, "event": event}
    raise DomainError("VALIDATION_ERROR", "候選缺少可處理的建議", {"fields": ["suggest"]})


def _resolve(conn: Connection, cand: dict, kind: str, suggested_due: str | None, new_due: date | None,
             expected_version: int, decision: str) -> dict:
    suggested = date.fromisoformat(suggested_due) if suggested_due else None
    due = new_due or suggested
    out = _apply(conn, cand, kind, due, expected_version)
    outcome = "edited" if kind == "delay" and new_due is not None and new_due != suggested else "accepted"
    return {"candidate": _close(conn, cand, "confirmed", decision, outcome)} | out


def confirm(conn: Connection, candidate_id: int, new_due: date | None, expected_version: int) -> dict:
    """delay／done／stuck 候選。delay 可改日期。"""
    cand = _load_open(conn, candidate_id, {"delay", "done", "stuck"})
    suggested = (cand["proposed"] or {}).get("new_due")
    return _resolve(conn, cand, cand["kind"], suggested, new_due, expected_version, "confirm")


def clarify(conn: Connection, candidate_id: int, new_due: date | None, expected_version: int) -> dict:
    """unclear 候選：依建議的種類處理（FR-INB-13）。「待釐清，你確認」由歷程從候選種類推導。"""
    cand = _load_open(conn, candidate_id, {"unclear"})
    suggest = cand["suggest"] or {}
    return _resolve(conn, cand, suggest.get("kind"), suggest.get("new_due"), new_due, expected_version, "clarify")


_FROM_CANDIDATE = object()


def create_task_from(conn: Connection, candidate_id: int, *, title: str, due: date, owner: str | None = None,
                     project_id: int | None | object = _FROM_CANDIDATE) -> dict:
    """unmatched 候選：建立新任務，負責人預設為發言者（FR-INB-14）。建立事件記錄候選依據（R-01）。

    project_id 沒送時沿用候選收件時的專案；有送（含 null）以送來的為準（PR #20 B5）。
    沿用的專案已封存時改建無專案任務，並回警告 PROJECT_ARCHIVED（#44 裁定 A）。
    """
    cand = _load_open(conn, candidate_id, {"unmatched"})
    owner = owner or sources_repo.get_many(conn, [cand["source_id"]])[0]["speaker"]
    warnings: list[str] = []
    if project_id is _FROM_CANDIDATE:
        project_id = cand["project_id"]
        if project_id is not None and projects_repo.get(conn, project_id)["archived_at"] is not None:
            project_id = None
            warnings.append("PROJECT_ARCHIVED")
    task = tasks.create_task(conn, title=title, owner=owner, due=due, project_id=project_id, origin="candidate",
                             origin_ref=cand["id"], source_id=cand["source_id"])
    return {"candidate": _close(conn, cand, "confirmed", "create_task", "changed", {"task_id": task["id"]}),
            "task": task, "warnings": warnings}


def ignore(conn: Connection, candidate_id: int) -> dict:
    cand = _load_open(conn, candidate_id, {"delay", "done", "stuck", "unclear", "unmatched"})
    return {"candidate": _close(conn, cand, "ignored", "ignore", "ignored")}
