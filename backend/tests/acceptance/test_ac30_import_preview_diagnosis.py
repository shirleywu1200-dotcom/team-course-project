"""AC-30：匯入預覽的診斷（FR-IMP-02、04）。"""

from tests.acceptance.helpers import API, ai_calls, count

# 7 列：第 1 列（index 1）缺結束日期、第 2 列結束早於開始、第 3 列名稱重複、第 4 列缺負責人。
TABLE = """任務,負責人,開始,結束
需求確認,我,2026-11-16,2026-11-18
畫面設計,小薇,2026-11-17,
API 開發,阿德,2026-11-25,2026-11-20
需求確認,我,2026-11-19,2026-11-21
測試計畫,,2026-11-20,2026-11-24
上線準備,我,2026-11-24,2026-11-26
驗收,阿德,2026-11-26,2026-11-28"""


def _preview(client, text=TABLE):
    r = client.post(f"{API}/projects/import/preview", json={"text": text, "target": "new", "new_name": "新專案"})
    assert r.status_code == 200, r.text
    return r.json()


def _levels(row):
    return {i["level"] for i in row["issues"]}


def test_ac30_error_rows_are_blocking(client):
    rows = _preview(client)["rows"]
    assert len(rows) == 7
    assert [r["index"] for r in rows if r["blocking"]] == [1, 2]
    assert "error" in _levels(rows[1]) and "error" in _levels(rows[2])
    assert rows[1]["end"] is None


def test_ac30_duplicate_and_missing_owner_are_warnings(client):
    rows = _preview(client)["rows"]
    for i in (3, 4):
        assert rows[i]["blocking"] is False
        assert _levels(rows[i]) == {"warn"}
    assert rows[4]["owner"] == "我"
    for i in (0, 5, 6):
        assert rows[i]["blocking"] is False and rows[i]["issues"] == []


def test_ac30_summary_counts_and_rule_mapping(client, ai):
    body = _preview(client)
    assert body["summary"] == {"importable": 5, "blocking": 2}
    cm = body["column_map"]
    assert (cm["title"], cm["owner"], cm["start"], cm["end"], cm["mapped_by"]) == (0, 1, 2, 3, "rule")
    assert ai_calls(ai, "AI-07") == []  # 規則能對應就不呼叫 AI（FR-IMP-02）


def test_fr_imp04_missing_title_is_blocking(client):
    rows = _preview(client, "任務,負責人,開始,結束\n,我,2026-11-16,2026-11-18\n驗收,我,2026-11-16,2026-11-18")["rows"]
    assert rows[0]["blocking"] is True and "error" in _levels(rows[0])
    assert rows[1]["blocking"] is False


def test_fr_imp04_missing_start_uses_three_days_before_end(client):
    rows = _preview(client, "任務,負責人,開始,結束\n驗收,我,,2026-11-18")["rows"]
    assert rows[0]["blocking"] is False
    assert _levels(rows[0]) == {"warn"}
    assert rows[0]["start"] == "2026-11-15"


def test_fr_imp03_unparseable_end_date_is_treated_as_missing(client):
    rows = _preview(client, "任務,負責人,開始,結束\n驗收,我,2026-11-16,下週吧")["rows"]
    assert rows[0]["blocking"] is True and rows[0]["end"] is None


def test_fr_imp01_tab_separated_table(client):
    body = _preview(client, "任務\t負責人\t開始\t結束\n驗收\t我\t2026-11-16\t2026-11-18")
    assert body["summary"] == {"importable": 1, "blocking": 0}
    assert body["rows"][0]["title"] == "驗收"


def test_ac30_preview_writes_nothing(client, query):
    _preview(client)
    for t in ("projects", "tasks", "events"):
        assert count(query, t) == 0


def test_fr_imp01_tab_and_comma_give_the_same_result(client):
    """審查 1-10(a)。"""
    assert _preview(client, TABLE.replace(",", chr(9))) == _preview(client, TABLE)


def test_fr_imp03_month_day_dates_get_a_year(client):
    """審查 1-10(b)：M/D 沒有年份時推年。今天是 2026-11-11，11/16、11/18 只可能是 2026 年。"""
    rows = _preview(client, "任務,負責人,開始,結束\n驗收,我,11/16,11/18")["rows"]
    assert rows[0]["blocking"] is False
    assert (rows[0]["start"], rows[0]["end"]) == ("2026-11-16", "2026-11-18")


def test_fr_imp03_unparseable_start_date_is_warning_with_three_days_before_end(client):
    """審查 1-10(c)：開始日期無法解析視為缺開始日期（FR-IMP-03、04）。"""
    rows = _preview(client, "任務,負責人,開始,結束\n驗收,我,下週吧,2026-11-18")["rows"]
    assert rows[0]["blocking"] is False
    assert _levels(rows[0]) == {"warn"}
    assert rows[0]["start"] == "2026-11-15"
