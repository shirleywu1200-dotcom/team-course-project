"""日期調整與基準更正的原因選項（spec 4.3、FR-DUE-05、FR-BAS-02）。

外部原因（external=True）只讓介面提示「建議不計入」，系統不據此設定註記（FR-MRK-03）。
"""

from app.errors import DomainError

EARLIER = "earlier"
LATER = "later"

DUE_REASONS = [
    {"code": "finished_early", "label": "提早完成條件達成", "direction": EARLIER, "external": False},
    {"code": "less_work", "label": "工作量比預期少", "direction": EARLIER, "external": False},
    {"code": "prereq_early", "label": "前置工作提早到位", "direction": EARLIER, "external": False},
    {"code": "other", "label": "其他", "direction": EARLIER, "external": False},
    {"code": "underestimated", "label": "估計不準（我低估）", "direction": LATER, "external": False},
    {"code": "self_interrupt", "label": "被其他事插隊（我自己排程）", "direction": LATER, "external": False},
    {"code": "wait_external", "label": "等對方或客戶回覆（外部）", "direction": LATER, "external": True},
    {"code": "scope_change_external", "label": "需求變更（外部）", "direction": LATER, "external": True},
    {"code": "resource_external", "label": "資源或環境未到位（外部）", "direction": LATER, "external": True},
    {"code": "other", "label": "其他", "direction": LATER, "external": False},
]

BASELINE_TYPES = {"correction": "更正錯誤", "rebaseline": "客戶或主管正式改變承諾日"}
BASELINE_REASONS = {
    "input_error": "匯入或輸入錯誤",
    "plan_date_wrong": "原計畫日期寫錯",
    "formal_commitment_change": "客戶或主管正式改變承諾日",
    "other": "其他",
}

MARKS = ("better", "worse", "none")


def direction_of(delta_days: int) -> str:
    return EARLIER if delta_days < 0 else LATER


def check_due_reason(reason: str | None, delta_days: int) -> None:
    """原因可空（docs/decisions.md DA-09）；有給時必須屬於該方向。"""
    if reason is None:
        return
    direction = direction_of(delta_days)
    if not any(r["code"] == reason and r["direction"] == direction for r in DUE_REASONS):
        raise DomainError("VALIDATION_ERROR", "原因不在此方向的選項內",
                          {"fields": ["reason"], "direction": direction})


def check_mark(mark: str | None) -> None:
    if mark is not None and mark not in MARKS:
        raise DomainError("VALIDATION_ERROR", details={"fields": ["mark"]})
