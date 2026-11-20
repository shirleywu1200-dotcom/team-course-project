"""Phase 9 第三片：AI-04 輸出驗證與 R3 對帳（todo 9.10；spec 5.3a〈AI-04〉第 8、9 點，2026-11-20 裁定；FR-GOL-07）。

純函式測試，不碰資料庫。測試清單：.scratch/phase9/testlist-9.10-v2.md（O1～O6、R1～R14）。
重試與紀錄（T 系列）與端點在服務層測試。
"""

from decimal import Decimal

import pytest

from app.ai.client import AIInvalidOutput
from app.domain import ai04

PAYLOAD = {
    "goal": {"type": "growth", "title": "讀完 12 本書 v1.2", "period": "2026Q4", "energy_plan": "mid"},
    "stats": {"linked": 3, "avg_actual": 4.0, "avg_expected": 3.3, "overdue_count": 1,
              "energy": {"high": 2, "mid": 0, "low": 1}, "progress_pct": 25, "judgement": None},
    "tasks": [{"task_id": 87, "title": "第 50% 里程碑", "done_date": "2026-11-06"},
              {"task_id": 93, "title": "報表查詢改寫", "done_date": "2026-11-17"}],
}
OK_FIGURES = [{"key": "linked", "value": 3}, {"key": "avg_actual", "value": 4},
              {"key": "avg_expected", "value": 3.3}, {"key": "overdue_count", "value": 1},
              {"key": "energy.high", "value": 2}, {"key": "energy.mid", "value": 0},
              {"key": "energy.low", "value": 1}, {"key": "progress_pct", "value": 25}]
OK_DRAFT = ("【目標】讀完 12 本書 v1.2（能力成長，2026Q4，預期精力：中）\n\n"
            "【進度】已關聯 3 件完成工作，進度 25%；實際平均 4.0 星，事前預設 3.3 星；逾期 1 件。\n\n"
            "【精力分布】高 2 件、中 0 件、低 1 件。\n\n"
            "【相關工作】\n・第 50% 里程碑（11/6）\n・報表查詢改寫（11/17）\n\n【判讀】樣本不足，不下判讀。")


def parse(draft=OK_DRAFT, figures=None):
    return ai04.parse_output({"draft": draft, "figures": OK_FIGURES if figures is None else figures})


def reconcile(draft=OK_DRAFT, figures=None, payload=PAYLOAD):
    d, f = parse(draft, figures)
    return ai04.reconcile(d, f, payload)


# ---------- O1～O6 輸出格式（任一不合 → AIInvalidOutput，可重試）----------

@pytest.mark.parametrize("output", [
    None, [], "x", {"figures": []}, {"draft": "x"}, {"draft": 3, "figures": []}, {"draft": "x", "figures": {}},
], ids=["none", "list", "str", "no-draft", "no-figures", "draft-not-str", "figures-not-list"])
def test_o1_shape(output):
    with pytest.raises(AIInvalidOutput):
        ai04.parse_output(output)


@pytest.mark.parametrize("draft", ["", "   \n\t"], ids=["empty", "blank"])
def test_o2_blank_draft(draft):
    with pytest.raises(AIInvalidOutput):
        parse(draft=draft)


def test_o3_draft_length_limit_counts_code_points():
    assert parse(draft="字" * 20_000)[0] == "字" * 20_000
    with pytest.raises(AIInvalidOutput):
        parse(draft="字" * 20_001)


def test_o4_nul_in_draft():
    with pytest.raises(AIInvalidOutput):
        parse(draft="草稿\x00")


@pytest.mark.parametrize("item", [
    "linked", {"key": "linked", "value": True}, {"key": "linked", "value": "3"}, {"key": "linked", "value": None},
    {"key": 3, "value": 3}, {"key": "linked"}, {"value": 3},
], ids=["not-object", "bool", "str", "null", "key-not-str", "no-value", "no-key"])
def test_o5_figure_item_must_be_key_and_number(item):
    with pytest.raises(AIInvalidOutput):
        parse(figures=[item])


@pytest.mark.parametrize("item", [{"key": "total", "value": 3}, {"key": "linked", "value": 3, "note": "x"}],
                         ids=["unknown-key", "extra-key"])
def test_o6_unknown_or_extra_key_is_format_error_not_r3(item):
    with pytest.raises(AIInvalidOutput):
        parse(figures=[item])


def test_parse_returns_draft_and_figures():
    assert parse() == (OK_DRAFT, [(f["key"], f["value"]) for f in OK_FIGURES])


# ---------- R1～R5 第 1 點：figures 等於 stats ----------

def test_r1_r6_full_valid_draft_passes():
    assert reconcile() is True


def test_r2_figure_value_differs():
    figures = [{"key": "energy.high", "value": 3}]
    assert reconcile(figures=figures) is False


def test_r3_numeric_equality_ignores_int_float():
    assert reconcile(figures=[{"key": "avg_actual", "value": 4}, {"key": "progress_pct", "value": 25.0}]) is True


def test_r4_figure_for_null_stat_fails():
    payload = {**PAYLOAD, "stats": {**PAYLOAD["stats"], "progress_pct": None}}
    assert reconcile(draft="無資料", figures=[{"key": "progress_pct", "value": 0}], payload=payload) is False


def test_r5_empty_figures_and_draft_without_numbers_pass():
    assert reconcile(draft="樣本不足，不下判讀。", figures=[]) is True


def test_same_key_twice_must_both_match():
    assert reconcile(figures=[{"key": "linked", "value": 3}, {"key": "linked", "value": 3}]) is True
    assert reconcile(figures=[{"key": "linked", "value": 3}, {"key": "linked", "value": 4}]) is False


def test_no_tolerance():
    assert reconcile(figures=[{"key": "avg_expected", "value": 3.25}]) is False
    assert reconcile(draft="事前預設 3.33 星") is False


# ---------- R6～R14 第 2 點：草稿數字都在允許名單 ----------
# 允許名單：stats 值 3、4.0、3.3、1、2、0、1、25；標題 12、1.2；期間 2026、4；任務標題 50；完成日 2026、11、6、17。
# 「不通過」的例子刻意選不在名單的數字（第 1 版曾用 2、5，和 energy.high、完成日撞號，測不出東西）。

@pytest.mark.parametrize("draft", ["相差 0.7 星", "共 8 項工作", "超出 7 天"], ids=["diff", "task-count", "made-up"])
def test_r7_number_not_in_allowlist(draft):
    assert reconcile(draft=draft) is False


def test_r8_r9_numbers_from_goal_task_text_and_dates_pass():
    assert reconcile(draft="讀完 12 本書 v1.2，2026Q4；第 50% 里程碑在 2026 年 11/6，另一項 11/17。") is True


def test_r10_normalization_in_spec():
    assert reconcile(draft="進度 25%，實際 4.0 星，逾期 １ 件，連結 ３ 件") is True


def test_r10b_fullwidth_point_percent_and_leading_zero():
    assert reconcile(draft="實際 ４．０ 星，進度 ２５％，完成於 11/06") is True


@pytest.mark.parametrize("draft", ["任務 87", "門檻 5 筆", "私人任務在 11/9"], ids=["task-id", "min-sample", "private-date"])
def test_r11_numbers_in_payload_but_not_allowed(draft):
    assert reconcile(draft=draft) is False


def test_r12_type_energy_plan_judgement_note_do_not_contribute():
    payload = {**PAYLOAD, "stats": {**PAYLOAD["stats"], "judgement": "建議檢視", "judgement_note": "樣本 3 筆，不到 5 筆"}}
    assert reconcile(draft="不到 5 筆", payload=payload) is False


def test_r13_both_points_required():
    assert reconcile(draft="相差 0.7 星") is False                              # 第 1 點過、第 2 點不過
    assert reconcile(figures=[{"key": "linked", "value": 4}]) is False          # 第 1 點不過、第 2 點過


def test_r14_verbatim_copy_of_payload_text_always_passes():
    payload = {**PAYLOAD,
               "goal": {**PAYLOAD["goal"], "title": "2026-Q4 營收 1,000 萬 v1.2 達 50%", "period": "２０２６Ｑ４"},
               "tasks": [{"task_id": 5, "title": "完成３份報告", "done_date": "2026-11-05"}]}
    draft = "2026-Q4 營收 1,000 萬 v1.2 達 50%（２０２６Ｑ４）：完成３份報告（11/5）"
    assert reconcile(draft=draft, figures=[], payload=payload) is True


def test_known_limitation_number_position_not_checked():
    """已知限制（spec 5.3a 第 8 點）：只看允許名單、不看位置，linked 與 overdue 互換仍通過。"""
    assert reconcile(draft="已關聯 1 件，逾期 3 件") is True


def test_negative_sign_is_not_part_of_number():
    assert reconcile(draft="差 -1 件") is True          # 切成 1，1 在名單（overdue_count）


def test_numbers_only_ascii_digits_after_fullwidth_conversion():
    """不做 NFKC（spec 5.3a 第 8 點）：①、²、阿拉伯－印度數字不算數字；全形數字轉半形後才算。"""
    assert ai04.numbers("① ² ٣") == set()
    assert ai04.numbers("１２．５％ 與 05、1,000、1e5") == {Decimal("12.5"), 5, 1, 0}


def test_trailing_point_counts_as_integer():
    assert ai04.numbers("逾期 3.") == {3}
    assert reconcile(draft="已關聯 3.") is True


def test_draft_length_counts_code_points_with_emoji():
    assert parse(draft="🙂" * 20_000)[0] == "🙂" * 20_000      # 20,000 個 code point（UTF-16 是 40,000）
    with pytest.raises(AIInvalidOutput):
        parse(draft="🙂" * 20_001)


@pytest.mark.parametrize("value", [10**5000, float("inf"), float("nan")], ids=["huge-int", "inf", "nan"])
def test_non_finite_value_is_format_error(value):
    """code-review：超大整數在 R3 的 str() 會丟 ValueError（重試迴圈外 → 500），在格式檢查就擋下（AC-50）。"""
    with pytest.raises(AIInvalidOutput):
        parse(figures=[{"key": "linked", "value": value}])
