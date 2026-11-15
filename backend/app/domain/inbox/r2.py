"""R2 規則（FR-INB-07、todo 7.4、7.9、7.10）：由程式決定 AI-01 輸出能變成哪種候選。純函式。

AI 只提議；格式、日期、語氣降級、對不到任務都由這裡判斷，而且只會降級、不會升級。
AI 輸出的其他欄位（例如原因推測）一律不讀（FR-DUE-05a、AC-12a）。
"""

import re
from dataclasses import dataclass
from datetime import date

from app.ai.client import AIInvalidOutput
from app.domain.dates import in_date_range, to_date

AI_KINDS = {"delay", "done", "stuck", "none"}
HEDGE_WORDS = ("可能", "大概", "應該", "也許")
QUESTION_MARKERS = ("?", "？", "嗎", "會不會")
_URL = re.compile(r"https?://\S+")


@dataclass(frozen=True)
class Draft:
    source_id: int
    kind: str
    certainty: str
    task_id: int | None
    proposed: dict | None
    suggest: dict | None


def is_hedged(text: str) -> bool:
    text = _URL.sub("", text)   # 網址裡的 ? 不算問句
    return any(w in text for w in HEDGE_WORDS + QUESTION_MARKERS)


def _valid_items(output, refs: set[int]) -> list[dict]:
    if not isinstance(output, dict) or not isinstance(output.get("items"), list):
        raise AIInvalidOutput("AI-01")
    return [it for it in output["items"]
            if isinstance(it, dict) and type(it.get("ref")) is int and it["ref"] in refs
            and isinstance(it.get("kind"), str) and it["kind"] in AI_KINDS]


def _pick_per_message(items: list[dict]) -> dict[int, dict]:
    """每則訊息最多一個候選；同時有完成與延期時取完成（D-07 預設）。"""
    picked: dict[int, dict] = {}
    for it in items:
        cur = picked.get(it["ref"])
        if cur is None or (it["kind"] == "done" and cur["kind"] != "done"):
            picked[it["ref"]] = it
    return picked


def _draft(source_id: int, it: dict, text: str, task_ids: set[int], today: date) -> Draft | None:
    kind = it["kind"]
    if kind == "none":
        return None
    task_id = it.get("task_id")
    if type(task_id) is not int or task_id not in task_ids:   # 不猜（AC-37）
        return Draft(source_id, "unmatched", "to_match", None, None, {"kind": kind})
    new_due = to_date(it.get("new_due"), today) if kind == "delay" else None
    bad_date = kind == "delay" and not in_date_range(new_due, today)
    suggest = {"kind": kind, "new_due": new_due.isoformat() if new_due and not bad_date else None}
    if bad_date or is_hedged(text) or it.get("certainty", "sure") != "sure":
        return Draft(source_id, "unclear", "to_clarify", task_id, None, suggest)
    proposed = {"new_due": new_due.isoformat()} if kind == "delay" else None
    return Draft(source_id, kind, "sure", task_id, proposed, None)


def apply(output, messages: dict[int, str], task_ids: set[int], today: date) -> list[Draft]:
    """messages：source_id → 原句。整體格式不對時丟 AIInvalidOutput（觸發重試）。"""
    picked = _pick_per_message(_valid_items(output, set(messages)))
    drafts = [_draft(ref, it, messages[ref], task_ids, today) for ref, it in sorted(picked.items())]
    return [d for d in drafts if d is not None]
