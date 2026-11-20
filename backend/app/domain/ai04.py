"""AI-04 目標回報草稿的輸入格式（FR-GOL-06；spec 5.3a〈AI-04〉）。

格式以 spec 5.3a 為準（2026-11-18 #72、#73 定案；節點與 prompt 為 Dev-B 的 app/ai/nodes/ai04.py）。
格式要改時先改 spec，再改這個檔。
- 輸入只放白名單欄位：目標的類型、名稱、期間、預期精力；程式算好的彙總統計；工作範圍任務的 id、名稱、完成日。
- 不送逐筆的星數與精力（FR-AI-06）、目標定義、負責人、完成條件；私人任務只進統計數字、不列標題（資安規則 2）。
"""

import re
from decimal import Decimal

from app.ai.client import AIInvalidOutput
from app.ai.nodes.ai04 import FIGURE_KEYS
from app.domain.ai05 import TEXT_MAX_CHARS  # 草稿上限同 AI-05（spec 5.3a）

NODE = "AI-04"
# R3 數字切法（spec 5.3a 第 8 點）：全形數字與全形「．」「％」轉半形，不做 NFKC；只認 ASCII 0–9，
# 不認負號、千分位、科學記號；以數值比較（05＝5、4.0＝4）。草稿與 payload 文字用同一套切法。
_HALF_WIDTH = str.maketrans({**{chr(0xFF10 + i): str(i) for i in range(10)}, "．": ".", "％": "%"})
_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def build_payload(goal: dict, stats: dict, rows: list[dict]) -> dict:
    """goal：goals 列；stats：goal_stats.summarize 的輸出；rows：同一母體的逐筆資料。"""
    work = sorted((r for r in rows if r["scope"] == "work"), key=lambda r: (r["done_date"], r["task_id"]),
                  reverse=True)
    return {
        "goal": {"type": goal["type"], "title": goal["title"], "period": goal["period"],
                 "energy_plan": goal["energy_plan"]},
        "stats": {
            "linked": stats["linked"], "avg_actual": stats["avg_actual"], "avg_expected": stats["avg_expected"],
            "overdue_count": stats["overdue_count"], "energy": dict(stats["energy"]),
            "progress_pct": (stats["progress"] or {}).get("pct"), "judgement": stats["judgement"],
        },
        "tasks": [{"task_id": r["task_id"], "title": r["title"], "done_date": r["done_date"].isoformat()}
                  for r in work],
    }


def numbers(text: str) -> set[Decimal]:
    return {Decimal(m) for m in _NUMBER.findall(text.translate(_HALF_WIDTH))}


def _flat_stats(stats: dict) -> dict:
    """stats 攤平成 FIGURE_KEYS 的寫法（energy.high 等），只取這些鍵；judgement 等文字欄位不貢獻數字。"""
    def value(key: str):
        group, _, sub = key.partition(".")
        return stats[group][sub] if sub else stats[group]
    return {key: value(key) for key in FIGURE_KEYS}


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _well_formed(item) -> bool:
    return (isinstance(item, dict) and set(item) == {"key", "value"}
            and item["key"] in FIGURE_KEYS and _is_number(item["value"]))


def parse_output(output) -> tuple[str, list[tuple[str, float]]]:
    """檢查格式，回傳 (draft, [(key, value)])。

    不合格丟 AIInvalidOutput（訊息不帶內容），可重試（spec 5.3a 第 9 點）。
    """
    if not isinstance(output, dict) or not isinstance(output.get("draft"), str) \
            or not isinstance(output.get("figures"), list):
        raise AIInvalidOutput(NODE)
    draft = output["draft"]
    if not draft.strip() or len(draft) > TEXT_MAX_CHARS or "\x00" in draft:
        raise AIInvalidOutput(NODE)
    if not all(_well_formed(item) for item in output["figures"]):
        raise AIInvalidOutput(NODE)
    return draft, [(item["key"], item["value"]) for item in output["figures"]]


def reconcile(draft: str, figures: list[tuple[str, float]], payload: dict) -> bool:
    """R3（FR-GOL-07）：figures 都等於 stats 同名值，且草稿裡每個數字都在允許名單。任一不符回 False。"""
    stats = _flat_stats(payload["stats"])
    for key, value in figures:
        if stats.get(key) is None or Decimal(str(value)) != Decimal(str(stats[key])):
            return False
    allowed = {Decimal(str(v)) for v in stats.values() if v is not None}
    texts = [payload["goal"]["title"], payload["goal"]["period"]]
    texts += [t for task in payload["tasks"] for t in (task["title"], task["done_date"])]
    for text in texts:
        allowed |= numbers(text)
    return numbers(draft) <= allowed
