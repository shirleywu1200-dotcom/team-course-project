"""週報的資料彙整、退路事件清單與 R4 對帳（todo 10.1、10.3；FR-RPT-01～03）。

規則依 issue #18 的裁定：
- 範圍只看任務的 scope；私人任務不進任何一段，只計數（同一任務算一次）。
- 本週完成：done_date 在本週；延期：本週有 delta_days > 0 的 due 事件；
  下週重點：未完成，且卡住或最新預計日在下週。
- R4：AI 回的每個完成與延期項目，都要對到本週資料裡同一任務的事件。
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import Connection

from app.db.repo import weekly_repo
from app.errors import DomainError

SECTIONS = ("done", "delay", "next")
CHECKED_SECTIONS = {"done", "delay"}   # FR-RPT-03 只規定完成與延期要對得上事件


@dataclass(frozen=True)
class WeekData:
    week_start: date
    done: list[dict]
    delay: list[dict]
    next: list[dict]
    excluded_private: int


def _check_monday(week_start: date) -> None:
    if week_start.weekday() != 0:
        raise DomainError("VALIDATION_ERROR", "week_start 必須是星期一", {"fields": ["week_start"]})


def _done_item(r: dict) -> dict:
    return {"task_id": r["task_id"], "title": r["title"], "owner": r["owner_name"],
            "done_date": r["done_date"], "event_id": r["event_id"]}


def _delay_items(rows: list[dict]) -> list[dict]:
    """同一任務的多筆延後事件合成一項（rows 已依任務、事件排序）。"""
    items: dict[int, dict] = {}
    for r in rows:
        item = items.setdefault(r["task_id"], {
            "task_id": r["task_id"], "title": r["title"], "owner": r["owner_name"],
            "orig_due": r["orig_due"], "latest_due": r["latest_due"], "event_ids": []})
        item["event_ids"].append(r["event_id"])
    return list(items.values())


def _next_item(r: dict) -> dict:
    return {"task_id": r["task_id"], "title": r["title"], "owner": r["owner_name"],
            "latest_due": r["latest_due"], "blocked": r["blocked"]}


def collect(conn: Connection, week_start: date) -> WeekData:
    _check_monday(week_start)
    week_end = week_start + timedelta(days=6)
    next_start, next_end = week_start + timedelta(days=7), week_start + timedelta(days=13)
    sections = {
        "done": weekly_repo.done_in_range(conn, week_start, week_end),
        "delay": weekly_repo.delay_events_in_range(conn, week_start, week_end),
        "next": weekly_repo.open_due_or_blocked(conn, next_start, next_end),
    }
    private = {r["task_id"] for rows in sections.values() for r in rows if r["scope"] == "private"}
    work = {name: [r for r in rows if r["scope"] == "work"] for name, rows in sections.items()}
    return WeekData(
        week_start=week_start,
        done=[_done_item(r) for r in work["done"]],
        delay=_delay_items(work["delay"]),
        next=[_next_item(r) for r in work["next"]],
        excluded_private=len(private),
    )


def fallback_items(data: WeekData) -> list[dict]:
    """AI 不可用或對帳失敗時回給前端的事件清單（spec 5.14、#18 裁定 4）。"""
    items = [{"section": "done", "task_id": i["task_id"], "event_id": i["event_id"]} for i in data.done]
    items += [{"section": "delay", "task_id": i["task_id"], "event_id": e}
              for i in data.delay for e in i["event_ids"]]
    items += [{"section": "next", "task_id": i["task_id"], "event_id": None} for i in data.next]
    return items


def reconcile(ai_items: list[dict], data: WeekData) -> bool:
    """R4（FR-RPT-03）：每個完成與延期項目，都必須是本週資料裡存在的（段落、任務、事件）。"""
    allowed = {(i["section"], i["task_id"], i["event_id"])
               for i in fallback_items(data) if i["section"] in CHECKED_SECTIONS}
    return all((i["section"], i["task_id"], i["event_id"]) in allowed
               for i in ai_items if i["section"] in CHECKED_SECTIONS)
