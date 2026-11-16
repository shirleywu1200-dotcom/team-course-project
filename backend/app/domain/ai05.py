"""AI-05 週報初稿的輸入與輸出格式（FR-RPT-02、03）。

格式依 issue #22 的提案（Dev-A 與 Dev-B 協議中，尚未定案；定案後只改這個檔）。
- 輸入只放白名單欄位：標題、負責人、日期與 id；不放備註、原因、註記、原句與自評（資安規則 2）。
- 輸出要有 draft（字串）與 items（結構化項目）。items 只保留 section、task_id、event_id 三個鍵，
  其他鍵一律丟掉，不存也不回傳（spec 8.2：AI 輸出須通過結構驗證）。
"""

from datetime import date, timedelta

from app.ai.client import AIInvalidOutput
from app.domain.weekly_report import SECTIONS, WeekData

NODE = "AI-05"


def _iso(value):
    return value.isoformat() if isinstance(value, date) else value


def build_payload(data: WeekData) -> dict:
    """只由 collect 的輸出組成；私人任務在 collect 已排除（AC-48）。"""
    return {
        "week": {"start": data.week_start.isoformat(), "end": (data.week_start + timedelta(days=6)).isoformat()},
        **{name: [{k: _iso(v) for k, v in item.items()} for item in getattr(data, name)] for name in SECTIONS},
    }


def _is_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parse_output(output) -> tuple[str, list[dict]]:
    """檢查結構，回傳 (draft, items)。格式不對丟 AIInvalidOutput（訊息不帶內容）。"""
    if not isinstance(output, dict) or not isinstance(output.get("draft"), str) \
            or not isinstance(output.get("items"), list):
        raise AIInvalidOutput(NODE)
    items: list[dict] = []
    for raw in output["items"]:
        if not isinstance(raw, dict) or raw.get("section") not in SECTIONS or not _is_id(raw.get("task_id")) \
                or not (raw.get("event_id") is None or _is_id(raw.get("event_id"))):
            raise AIInvalidOutput(NODE)
        item = {"section": raw["section"], "task_id": raw["task_id"], "event_id": raw.get("event_id")}
        if item not in items:   # 重複的項目合併（#18 J9）
            items.append(item)
    return output["draft"], items
