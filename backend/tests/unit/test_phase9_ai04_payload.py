"""Phase 9 第三片：AI-04 目標回報的 payload 組裝（todo 9.10；spec 5.3a〈AI-04〉、5.13 stats；FR-GOL-06、FR-AI-06）。

只測 5.3a 已定案的部分：payload 的鍵、內容與私人範圍排除。端點、存檔、R3 等 #47 9.10 裁定後補。
測試清單與子代理審查紀錄：.scratch/phase9/testlist-9.10.md（P1～P9）。

統計值與 GET /goals/{id}/stats 比對（行為），payload 由 goal_report.collect 取得；端點定案後改成經 API 從 FakeAIClient 收到的 payload 驗證。
"""

import json

import pytest

from app.ai.nodes.ai04 import FIGURE_KEYS
from app.domain import goal_report
from app.errors import DomainError
from tests.acceptance.helpers import API

TS = "'2026-11-01T09:00+08:00'"
MARK = "機密標記XYZ"   # 放進不該外送的欄位，payload 裡不能出現

BASE = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
 (1, '會員系統', 'work', 'manager', {TS}, {TS}),
 (3, '空專案', 'work', 'manager', {TS}, {TS});
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
 (11, 'growth', '讀完 3 本書', '2026Q4', '{MARK}', 4, 'mid', NULL, {TS}, NULL),
 (12, 'time', '每週留 2 小時讀書', '2026Q4', '', 120, 'low', NULL, {TS}, NULL),
 (13, 'expectation', '空專案準時上線', '2026Q4', '', 0, 'high', 3, {TS}, NULL),
 (15, 'growth', '沒有目標數', '2026Q4', '', 0, 'high', NULL, {TS}, NULL);
"""
TASK_COLS = ("id, project_id, goal_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date, "
             "done_when, expected_stars, star_source, version, created_at, updated_at")


def task_sql(tid, title, goal, *, scope="work", status="done", done="2026-11-07", expected=4):
    done_sql = f"'{done}'" if status == "done" else "NULL"
    project = "NULL" if scope == "private" else "1"
    return (f"({tid}, {project}, {goal}, '{title}', '{MARK}', '{scope}', '2026-11-01', '2026-11-05', '2026-11-05', "
            f"'{status}', {done_sql}, '{MARK}', {expected}, 'self', 1, {TS}, {TS})")


def fb_sql(tid, stars, energy, overdue):
    return f"({tid}, {tid}, {stars}, '{energy}', 'more', {overdue}, (SELECT min(id) FROM rubrics), {TS})"


TASKS = [
    task_sql(21, "報表查詢改寫", 11, done="2026-11-07", expected=4),
    task_sql(22, "私人看診 7 號", 11, scope="private", done="2026-11-09", expected=2),   # 私人：只進統計
    task_sql(23, "索引調校", 11, done="2026-11-09", expected=3),                         # 與 22 同日，id 較大排前
    task_sql(24, "沒有回報", 11, done="2026-11-08"),                                     # 沒有回報：不在母體
    task_sql(25, "未完成", 11, status="todo"),                                           # 未完成：不在母體
    task_sql(26, "別的目標", 12, done="2026-11-06"),                                     # 關聯到別的目標
]
FEEDBACK = [fb_sql(21, 5, "high", 0), fb_sql(22, 3, "low", 2), fb_sql(23, 4, "high", 0), fb_sql(26, 2, "mid", 0)]


@pytest.fixture
def data(seed):
    seed(BASE)
    seed(f"INSERT INTO tasks ({TASK_COLS}) VALUES\n" + ",\n".join(TASKS) + ";\n"
         "INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, "
         "rubric_id, created_at) VALUES\n" + ",\n".join(FEEDBACK) + ";")


def collect(db, goal_id):
    return db.run(lambda c: goal_report.collect(c, goal_id))


def stats_api(client, goal_id):
    r = client.get(f"{API}/goals/{goal_id}/stats")
    assert r.status_code == 200, r.text
    return r.json()


# P1、P2
def test_payload_top_level_and_goal_keys(db, data):
    payload = collect(db, 11).payload
    assert set(payload) == {"goal", "stats", "tasks"}
    assert payload["goal"] == {"type": "growth", "title": "讀完 3 本書", "period": "2026Q4", "energy_plan": "mid"}


# P3、P4：鍵集合固定，值與 GET /goals/{id}/stats 同一份計算
def test_stats_keys_and_values_match_stats_endpoint(db, data, client):
    stats = collect(db, 11).payload["stats"]
    assert set(stats) == {"linked", "avg_actual", "avg_expected", "overdue_count", "energy", "progress_pct",
                          "judgement"}
    expected = stats_api(client, 11)
    assert stats == {
        "linked": expected["linked"], "avg_actual": expected["avg_actual"], "avg_expected": expected["avg_expected"],
        "overdue_count": expected["overdue_count"], "energy": expected["energy"],
        "progress_pct": expected["progress"]["pct"], "judgement": expected["judgement"],
    }
    # 母體 21、22、23：3 件；私人 22 計入統計（5.3a）
    assert stats["linked"] == 3 and stats["overdue_count"] == 1
    assert stats["energy"] == {"high": 2, "mid": 0, "low": 1}
    assert stats["progress_pct"] == 75   # 3 ÷ 4


@pytest.mark.parametrize("goal_id", [12, 13, 15], ids=["time", "expectation_empty_project", "growth_target_0"])
def test_progress_pct_null_when_stats_progress_has_no_pct(db, data, client, goal_id):
    expected = stats_api(client, goal_id)
    assert (expected["progress"] or {}).get("pct") is None
    assert collect(db, goal_id).payload["stats"]["progress_pct"] is None


# P5、P8：只列母體中的工作任務，依完成日、task_id 由新到舊
def test_tasks_only_work_population_with_allowed_keys(db, data):
    tasks = collect(db, 11).payload["tasks"]
    assert tasks == [
        {"task_id": 23, "title": "索引調校", "done_date": "2026-11-09"},
        {"task_id": 21, "title": "報表查詢改寫", "done_date": "2026-11-07"},
    ]


# P6：私人任務的標題與 id 不出現在 payload，只計入統計與 excluded_private
def test_private_task_not_in_payload_but_counted(db, data):
    result = collect(db, 11)
    text = json.dumps(result.payload, ensure_ascii=False)
    assert "私人看診" not in text
    assert 22 not in [t["task_id"] for t in result.payload["tasks"]]
    assert result.excluded_private == 1
    assert result.payload["stats"]["linked"] == 3


def test_only_private_tasks_gives_empty_task_list(db, data, seed):
    seed("UPDATE tasks SET scope = 'private', project_id = NULL WHERE id IN (21, 23);")
    result = collect(db, 11)
    assert result.payload["tasks"] == []
    assert result.excluded_private == 3
    assert result.payload["stats"]["linked"] == 3


# P7：不送逐筆評價、負責人、完成條件、備註、目標定義
def test_payload_has_no_per_task_evaluation_or_free_text(db, data):
    text = json.dumps(collect(db, 11).payload, ensure_ascii=False)
    assert MARK not in text
    for key in ("actual_stars", "expected_stars", "overdue_days", "owner", "definition", "target",
                "min_sample", "judgement_note", "project_id"):
        assert f'"{key}"' not in text


def test_unknown_goal_is_not_found(db, data):
    with pytest.raises(DomainError) as e:
        collect(db, 999)
    assert e.value.code == "NOT_FOUND"


# P9 結構測試：節點的 FIGURE_KEYS 與呼叫端 stats 的數字鍵要一致（SDD 2.3、#50）。
# 行為測試做不到：鍵名不一致時，真實供應商依 schema 只會產生 FIGURE_KEYS 裡的鍵，
# R3 第 1 點只會「找不到同名值」而失敗，從 API 看起來和 AI 寫錯數字沒有分別。
def _flat_keys(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _flat_keys(v, f"{prefix}{k}.")
        else:
            yield prefix + k


def test_figure_keys_match_caller_stats_numeric_keys(db, data):
    stats = collect(db, 11).payload["stats"]
    assert set(_flat_keys(stats)) - {"judgement"} == set(FIGURE_KEYS)
