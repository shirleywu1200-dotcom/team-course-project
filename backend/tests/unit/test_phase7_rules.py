"""Phase 7 純函式：寬鬆解析（SDD 2.1）、R1（AC-42）、R2（AC-35～37、7.9、7.10）。"""

import hashlib
from datetime import date

import pytest

from app.ai.client import AIInvalidOutput
from app.domain.inbox import r2
from app.domain.inbox.parse import parse_line, parse_text
from app.domain.inbox.r1 import accept_line_message

TODAY = date(2026, 11, 11)


# ---------- 寬鬆解析 ----------

@pytest.mark.parametrize("line, expected", [
    ("[10:12] 阿德：畫面規格 v1 確定延到 11/18", ("10:12", "阿德", "畫面規格 v1 確定延到 11/18")),
    ("10:12\t阿德\t畫面規格延到 11/18", ("10:12", "阿德", "畫面規格延到 11/18")),
    ("10:12\t\t阿德\t\t\t延到 11/18", ("10:12", "阿德", "延到 11/18")),
    ("10:12   阿德   延到 11/18", ("10:12", "阿德", "延到 11/18")),
    ("［10：12］阿德:延到 11/18", ("10:12", "阿德", "延到 11/18")),
    ("【9:05】 小薇 ： API 完成了", ("09:05", "小薇", "API 完成了")),
    ("下午3:05 阿德 延到 11/18", ("15:05", "阿德", "延到 11/18")),
    ("上午12:30\t阿德\t早", ("00:30", "阿德", "早")),
    ("１０:１２ 阿德 延到 11/18", ("10:12", "阿德", "延到 11/18")),
    ("阿德：備註：明天交", (None, "阿德", "備註：明天交")),
    ("10:12\t阿德\t內容：含冒號", ("10:12", "阿德", "內容：含冒號")),
])
def test_parse_line_tolerates_separators(line, expected):
    assert parse_line(line) == expected


@pytest.mark.parametrize("line", ["只是一段沒有發言者的文字", "10:12", "10:12 阿德", "25:99 阿德 內容"])
def test_parse_line_rejects_unrecognized(line):
    assert parse_line(line) is None


def test_parse_text_continuation_date_header_and_unparsed_lines():
    text = "\n".join([
        "沒有發言者的開頭",            # 1：前面沒有訊息 → 無法辨識
        "",
        "2026/11/11（三）",            # 3：日期標題，略過
        "10:12\t阿德\t第一行",
        "第二行接續",                   # 5：接到上一則
        "2026.11.12 星期四",
        "[10:20] 小薇：好",
    ])
    r = parse_text(text)
    assert [(m.speaker, m.text) for m in r.messages] == [("阿德", "第一行\n第二行接續"), ("小薇", "好")]
    assert r.unparsed_lines == [1]
    assert r.line_count == 6


def test_message_hash_uses_time_speaker_and_text():
    a, b, c = (parse_text(t).messages[0] for t in ("[10:12] 阿德：延", "[10:12] 阿德：延", "[10:13] 阿德：延"))
    assert a.hash == b.hash != c.hash


def test_message_hash_includes_date_header_when_present():
    """PR #20 B3：有日期標頭時，日期併入雜湊；沒有日期時雜湊與原本相同（FR-INB-04）。"""
    line = "[10:12] 阿德：延"
    no_date = parse_text(line).messages[0]
    d11 = parse_text(f"2026/11/11（三）\n{line}").messages[0]
    d11_other_format = parse_text(f"2026年11月11日\n{line}").messages[0]
    d12 = parse_text(f"2026.11.12 星期四\n{line}").messages[0]
    assert (d11.date, d12.date, no_date.date) == ("2026-11-11", "2026-11-12", None)
    assert d11.hash == d11_other_format.hash != d12.hash
    assert no_date.hash not in (d11.hash, d12.hash)
    assert no_date.hash == hashlib.sha256("10:12\n阿德\n延".encode()).hexdigest()


# ---------- R1（AC-42） ----------

@pytest.mark.parametrize("group, accepted", [
    (None, False),
    ({"notified": False, "bound": False}, False),
    ({"notified": True, "bound": False}, False),
    ({"notified": True, "bound": True}, True),
])
def test_ac42_r1_drops_unbound_or_uninformed_groups(group, accepted):
    assert accept_line_message(group) is accepted


# ---------- R2 ----------

def apply(items, texts=None, task_ids=frozenset({2, 3})):
    texts = texts or {1: "畫面規格 v1 確定延到 11/18"}
    return r2.apply({"items": items}, texts, set(task_ids), TODAY)


def test_r2_sure_delay_converts_month_day():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18", "certainty": "sure"}])
    assert (d.kind, d.certainty, d.task_id, d.proposed, d.suggest) == ("delay", "sure", 2,
                                                                      {"new_due": "2026-11-18"}, None)


def test_r2_month_day_far_in_past_rolls_to_next_year():
    assert r2.to_date("1/5", TODAY) == date(2027, 1, 5)
    assert r2.to_date("10/1", TODAY) == date(2026, 10, 1)
    assert r2.to_date("2026-12-01", TODAY) == date(2026, 12, 1)
    assert r2.to_date("下週", TODAY) is None


def test_ac35_question_becomes_unclear_not_stuck():
    [d] = apply([{"ref": 1, "kind": "stuck", "task_id": 3}], {1: "下週測試如果環境沒好，會不會卡住？"})
    assert (d.kind, d.certainty, d.task_id, d.suggest) == ("unclear", "to_clarify", 3,
                                                          {"kind": "stuck", "new_due": None})


def test_ac36_hedged_delay_becomes_unclear():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"}], {1: "畫面規格可能延到 11/18"})
    assert d.kind == "unclear" and d.suggest == {"kind": "delay", "new_due": "2026-11-18"} and d.proposed is None


def test_r2_ai_uncertainty_only_downgrades():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18", "certainty": "to_clarify"}])
    assert d.kind == "unclear"


def test_r2_bad_or_out_of_range_date_becomes_unclear():
    [d1] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "改天"}])
    [d2] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "2030-01-01"}])
    assert d1.kind == d2.kind == "unclear" and d1.suggest["new_due"] is None


@pytest.mark.parametrize("task_id", [None, 99, "2"])
def test_ac37_unknown_task_is_unmatched_without_guessing(task_id):
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": task_id, "new_due": "11/18"}])
    assert (d.kind, d.certainty, d.task_id) == ("unmatched", "to_match", None)


def test_r2_drops_irrelevant_and_malformed_items():
    texts = {1: "a", 2: "b"}
    drafts = apply([{"ref": 1, "kind": "none"}, {"ref": 2, "kind": "cancel", "task_id": 2},
                    {"ref": 9, "kind": "done", "task_id": 2}, "垃圾"], texts)
    assert drafts == []


@pytest.mark.parametrize("output", [None, [], {"items": "x"}, {"candidates": []}])
def test_r2_whole_output_malformed_raises_for_retry(output):
    with pytest.raises(AIInvalidOutput):
        r2.apply(output, {1: "a"}, {2}, TODAY)


def test_d07_done_wins_over_delay_in_same_message():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"},
                 {"ref": 1, "kind": "done", "task_id": 2}], {1: "畫面做完了，報告延到 11/18"})
    assert d.kind == "done"


def test_ac12a_reason_guess_in_ai_output_is_not_kept():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18", "reason": "underestimated",
                  "mark": "worse"}])
    assert "underestimated" not in str(d) and "worse" not in str(d)


# ---------- 審查修正的回歸測試 ----------

@pytest.mark.parametrize("item", [
    {"ref": [1], "kind": "delay", "task_id": 2},
    {"ref": 1, "kind": ["delay"], "task_id": 2},
    {"ref": True, "kind": "done", "task_id": 2},
])
def test_r2_unhashable_or_wrong_type_fields_are_skipped(item):
    assert apply([item]) == []


def test_r2_unhashable_task_id_is_unmatched():
    [d] = apply([{"ref": 1, "kind": "done", "task_id": {"id": 2}}])
    assert d.kind == "unmatched"


def test_r2_question_mark_inside_url_is_not_a_question():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"}],
                {1: "規格確定延到 11/18 https://x.example/doc?id=3"})
    assert d.kind == "delay"


def test_parse_url_line_continues_previous_message():
    r = parse_text("[10:12] 阿德：規格在這\nhttps://docs.example.com/spec")
    assert [(m.speaker, m.text) for m in r.messages] == [("阿德", "規格在這\nhttps://docs.example.com/spec")]


# ---------- #138：延期的新日期等於目前期限 → 略過 ----------

SAME_DUE = {2: date(2026, 11, 18)}


def _apply_due(items, texts=None, latest_due=SAME_DUE):
    texts = texts or {1: "畫面規格 v1 確定延到 11/18"}
    return r2.apply({"items": items}, texts, {2, 3}, TODAY, latest_due=latest_due)


def test_issue138_delay_to_same_due_is_skipped():
    assert _apply_due([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"}]) == []


def test_issue138_hedged_delay_to_same_due_is_skipped_not_unclear():
    assert _apply_due([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"}],
                      {1: "畫面規格可能延到 11/18"}) == []


def test_issue138_delay_one_day_later_is_still_sure_delay():
    [d] = _apply_due([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/19"}])
    assert (d.kind, d.certainty, d.proposed) == ("delay", "sure", {"new_due": "2026-11-19"})


def test_issue138_without_latest_due_behaves_as_before():
    [d] = apply([{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"}])
    assert (d.kind, d.certainty) == ("delay", "sure")
