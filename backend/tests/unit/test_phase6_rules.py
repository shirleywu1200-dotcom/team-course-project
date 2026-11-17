"""Phase 6 純函式：日期（6.3）、切表格與表頭對應（6.1、6.2）、診斷（6.4）。"""

from datetime import date

import pytest

from app.domain.dates import to_date
from app.domain.imports.diagnose import diagnose
from app.domain.imports.table import is_complete, map_by_rule, split_table, valid_map
from app.errors import DomainError

TODAY = date(2026, 11, 11)


@pytest.mark.parametrize("raw, expected", [
    ("2026-11-18", date(2026, 11, 18)),
    ("2026/11/8", date(2026, 11, 8)),
    ("2026年11月18日", date(2026, 11, 18)),
    ("11/18", date(2026, 11, 18)),
    ("11月18日", date(2026, 11, 18)),
    ("1/10", date(2027, 1, 10)),       # 比今天早 180 天以上 → 明年（跨年專案）
    ("6/1", date(2026, 6, 1)),
    ("2026-02-30", None),
    ("下週", None),
    ("", None),
    (None, None),
])
def test_to_date(raw, expected):
    assert to_date(raw, TODAY) == expected


def test_split_table_comma_with_quotes_and_blank_lines():
    header, data = split_table('任務,負責人,開始,結束\n"規格, v1",阿德,11/9,11/13\n\n  \n測試,,,11/20\n')
    assert header == ["任務", "負責人", "開始", "結束"]
    assert data == [["規格, v1", "阿德", "11/9", "11/13"], ["測試", "", "", "11/20"]]


def test_split_table_tab_from_excel():
    header, data = split_table("任務\t負責人\t結束\n規格, v1\t阿德\t11/13")
    assert header == ["任務", "負責人", "結束"] and data == [["規格, v1", "阿德", "11/13"]]


def test_split_table_limits():
    with pytest.raises(DomainError) as e:
        split_table("任務,結束\n" + "a,11/20\n" * 501)
    assert e.value.code == "PAYLOAD_TOO_LARGE"
    with pytest.raises(DomainError) as e:
        split_table("x" * 50_001)
    assert e.value.code == "PAYLOAD_TOO_LARGE"
    with pytest.raises(DomainError) as e:
        split_table("  \n")
    assert e.value.code == "EMPTY_SELECTION"


@pytest.mark.parametrize("header, expected", [
    (["任務", "負責人", "開始", "結束"], {"title": 0, "owner": 1, "start": 2, "end": 3}),
    (["Task Name", "Owner", "Start Date", "Due Date"], {"title": 0, "owner": 1, "start": 2, "end": 3}),
    (["期限", "工作項目"], {"title": 1, "owner": None, "start": None, "end": 0}),
    (["工項", "PIC", "起", "交期"], {"title": None, "owner": 1, "start": None, "end": None}),
])
def test_map_by_rule(header, expected):
    assert map_by_rule(header) == expected


def test_is_complete_requires_title_and_end():
    assert is_complete({"title": 0, "owner": None, "start": None, "end": 1})
    assert not is_complete({"title": 0, "owner": 1, "start": 2, "end": None})


@pytest.mark.parametrize("mapping, ok", [
    ({"title": 0, "owner": 1, "start": 2, "end": 3}, True),
    ({"title": 0, "end": 3}, True),
    ({"title": 0, "end": 0}, False),          # 重複
    ({"title": 0, "end": 9}, False),          # 超出欄數
    ({"title": "0", "end": 3}, False),        # 型別
    ({"title": None, "end": 3}, False),       # 必填
    (["x"], False),
])
def test_valid_map(mapping, ok):
    assert (valid_map(mapping, 4) is not None) is ok


def codes(row):
    return [i["code"] for i in row.out()["issues"]]


def test_diagnose_defaults_and_warnings():
    seen = set()
    row = diagnose(0, "需求確認", "", "", "11/18", TODAY, seen)
    assert (row.owner, row.start, row.end, row.blocking) == ("我", date(2026, 11, 15), date(2026, 11, 18), False)
    assert codes(row) == ["OWNER_MISSING", "START_MISSING"]
    dup = diagnose(1, "需求確認", "阿德", "11/16", "11/18", TODAY, seen)
    assert codes(dup) == ["DUPLICATE_TITLE"] and not dup.blocking


@pytest.mark.parametrize("args, code", [
    (("", "我", "11/16", "11/18"), "TITLE_MISSING"),
    (("a", "我", "11/16", ""), "END_MISSING"),
    (("a", "我", "11/16", "改天"), "END_MISSING"),
    (("a", "我", "11/20", "11/18"), "END_BEFORE_START"),
    (("a", "我", "", "2024-01-01"), "DATE_OUT_OF_RANGE"),
])
def test_diagnose_errors_block(args, code):
    row = diagnose(0, *args, TODAY, set())
    assert code in codes(row) and row.blocking


# ---------- 審查修正的回歸測試 ----------

@pytest.mark.parametrize("header, expected", [
    (["任務", "完成標準", "期限"], {"title": 0, "owner": None, "start": None, "end": 2}),
    (["Owner Name", "Task", "Due"], {"title": 1, "owner": 0, "start": None, "end": 2}),
    (["任務負責人", "任務名稱", "結束"], {"title": 1, "owner": 0, "start": None, "end": 2}),
])
def test_map_by_rule_avoids_greedy_substring_claims(header, expected):
    assert map_by_rule(header) == expected


def test_split_table_keeps_blank_line_inside_quoted_cell():
    _, data = split_table('任務,結束\n"說明第一段\n\n第二段",11/20\n')
    assert data == [["說明第一段\n\n第二段", "11/20"]]
