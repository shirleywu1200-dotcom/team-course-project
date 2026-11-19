"""Phase 9 第二片：目標關聯、待關聯清單、統計與判讀、矩陣（todo 9.6、9.8、9.9；spec 5.13；
FR-GOL-03～05、AC-46；#47 G1、G2 與第二片提案）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP 與 SQL 種子操作，不讀實作。

測試清單：
- L1 關聯：寫一筆 goal 事件（field=goal_id、task_id、from→to）、更新 tasks.goal_id、version 加 1；輸出 {task, event}。
- L2 第一次選「不關聯」也寫事件（null→null）；再送 null 回 NO_CHANGE。
- L3 改選 A→B 再寫一筆；送與目前相同的目標回 NO_CHANGE；歷程只增。
- L4 錯誤：任務不存在 404；版本不符 STALE_VERSION；未完成或沒有回報、目標不存在或已封存、型別錯誤回 422；
  失敗時不寫事件、版本不變。
- L5 待關聯清單：只列已完成、有回報、從未做過關聯決定的任務；含私人與封存專案；依完成日由新到舊；欄位集合。
- L6 統計樣本不足：judgement null 與說明；平均四捨五入到小數一位；逾期件數、精力分布；母體只算已完成且有回報。
- L7 判讀（樣本 5 筆以上）：一致、建議檢視、主要精力並列一律建議檢視。
- L8 進度：growth 上限 100、四捨五入、target 0 為 null；time 為 null；expectation 為專案完成比、沒有任務為 null。
- L9 封存的目標可查統計；目標不存在 404；沒有樣本時平均為 null。
- L10 矩陣：只列未封存目標、依 id 排序，精力與件數同統計母體。
- L11 新端點都要 token。
"""

import pytest
from fastapi.testclient import TestClient

from tests.acceptance.helpers import API, count

TS = "'2026-11-01T09:00+08:00'"
BASE = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at, archived_at) VALUES
 (1, '會員系統', 'work', 'manager', {TS}, {TS}, NULL),
 (2, '舊專案', 'work', 'manager', {TS}, {TS}, '2026-11-05T09:00+08:00'),
 (3, '空專案', 'work', 'manager', {TS}, {TS}, NULL);
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
 (11, 'growth', '學會 SQL 視窗函式', '2026Q4', '', 3, 'mid', NULL, {TS}, NULL),
 (12, 'time', '每週留 2 小時讀書', '2026Q4', '', 120, 'low', NULL, {TS}, NULL),
 (13, 'expectation', '會員系統準時上線', '2026Q4', '', 0, 'high', 1, {TS}, NULL),
 (14, 'growth', '舊目標', '2026Q3', '', 2, 'high', NULL, {TS}, '2026-11-05T09:00+08:00'),
 (15, 'expectation', '空專案目標', '2026Q4', '', 0, 'low', 3, {TS}, NULL);
"""

TASK_COLS = ("id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, done_date, "
             "expected_stars, star_source, goal_id, version, created_at, updated_at")


def task_sql(tid, *, project="1", scope="work", status="done", done="2026-11-07", stars=3, goal="NULL",
             version=1, title=None):
    done_sql = f"'{done}'" if status == "done" else "NULL"
    title = title or f"任務{tid}"
    return (f"({tid}, {project}, '{title}', '我', '{scope}', '2026-11-01', '2026-11-05', '2026-11-05', "
            f"'{status}', {done_sql}, {stars}, 'self', {goal}, {version}, {TS}, {TS})")


def feedback_sql(tid, *, stars=4, energy="mid", overdue=0):
    # 量表用遷移 0003 種下的預設版本（completion_feedback.rubric_id NOT NULL）
    return f"({tid}, {tid}, {stars}, '{energy}', NULL, {overdue}, (SELECT min(id) FROM rubrics), {TS})"


def seed_tasks(seed, tasks, feedback):
    sql = f"INSERT INTO tasks ({TASK_COLS}) VALUES\n" + ",\n".join(tasks) + ";\n"
    if feedback:
        sql += ("INSERT INTO completion_feedback (id, task_id, actual_stars, energy, invest_vs_expected, "
                "overdue_days, rubric_id, created_at) VALUES\n" + ",\n".join(feedback) + ";\n")
    seed(sql)


LINK_TASKS = [
    task_sql(21, done="2026-11-07", version=2, title="報表查詢改寫"),      # 一般：已完成、有回報
    task_sql(22, project="NULL", scope="private", done="2026-11-08"),    # 私人
    task_sql(23, project="2", done="2026-11-06"),                        # 封存專案底下
    task_sql(24, done="2026-11-09"),                                     # 已完成、沒有回報
    task_sql(25, status="todo"),                                         # 未完成
    task_sql(26, done="2026-11-08"),                                     # 與 22 同日，比 id
]
LINK_FEEDBACK = [feedback_sql(21), feedback_sql(22), feedback_sql(23), feedback_sql(26)]


@pytest.fixture
def links(seed):
    seed(BASE)
    seed_tasks(seed, LINK_TASKS, LINK_FEEDBACK)


def link(client, task_id, goal_id, version):
    return client.post(f"{API}/goal-links", json={"task_id": task_id, "goal_id": goal_id, "expected_version": version})


def link_events(query, task_id):
    return query("SELECT * FROM events WHERE kind = 'goal' AND task_id = :t ORDER BY id", t=task_id)


def task_row(query, task_id):
    return query("SELECT goal_id, version FROM tasks WHERE id = :t", t=task_id)[0]


def pending(client):
    r = client.get(f"{API}/goal-links/pending")
    assert r.status_code == 200, r.text
    return r.json()


def assert_error(r, status, code, fields=None):
    assert r.status_code == status, r.text
    err = r.json()["error"]
    assert err["code"] == code
    if fields is not None:
        assert sorted(err["details"]["fields"]) == sorted(fields)


# ---------- L1～L3：關聯 ----------

def test_l1_link_writes_event_and_updates_task(client, links, query):
    r = link(client, 21, 11, 2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"task", "event"}
    assert body["task"]["id"] == 21 and body["task"]["goal_id"] == 11 and body["task"]["version"] == 3
    ev = body["event"]
    assert (ev["kind"], ev["field"], ev["task_id"], ev["from_value"], ev["to_value"]) == ("goal", "goal_id", 21, None, "11")
    assert ev["task_title"] == "報表查詢改寫" and ev["origin"] == "manual"
    assert task_row(query, 21) == {"goal_id": 11, "version": 3}
    assert len(link_events(query, 21)) == 1


def test_l2_first_unlink_is_recorded_then_no_change(client, links, query):
    r = link(client, 21, None, 2)
    assert r.status_code == 200, r.text
    ev = r.json()["event"]
    assert (ev["from_value"], ev["to_value"]) == (None, None)
    assert task_row(query, 21) == {"goal_id": None, "version": 3}
    assert_error(link(client, 21, None, 3), 422, "NO_CHANGE")
    assert len(link_events(query, 21)) == 1 and task_row(query, 21)["version"] == 3


def test_l3_relink_appends_event_and_same_goal_is_no_change(client, links, query):
    assert link(client, 21, 11, 2).status_code == 200
    r = link(client, 21, 12, 3)
    assert r.status_code == 200, r.text
    assert (r.json()["event"]["from_value"], r.json()["event"]["to_value"]) == ("11", "12")
    assert_error(link(client, 21, 12, 4), 422, "NO_CHANGE")
    r = link(client, 21, None, 4)                                   # 改成不關聯也是新增一筆
    assert r.status_code == 200 and r.json()["event"]["from_value"] == "12"
    events = link_events(query, 21)
    assert [(e["from_value"], e["to_value"]) for e in events] == [(None, "11"), ("11", "12"), ("12", None)]
    assert task_row(query, 21) == {"goal_id": None, "version": 5}


def test_l3_private_task_can_be_linked(client, links, query):
    r = link(client, 22, 11, 1)
    assert r.status_code == 200 and task_row(query, 22)["goal_id"] == 11


# ---------- L4：錯誤 ----------

@pytest.mark.parametrize("task_id, goal_id, version, status, code, fields", [
    (999, 11, 1, 404, "NOT_FOUND", None),
    (21, 11, 1, 409, "STALE_VERSION", None),
    (25, 11, 1, 422, "VALIDATION_ERROR", ["task_id"]),     # 未完成
    (24, 11, 1, 422, "VALIDATION_ERROR", ["task_id"]),     # 已完成但沒有回報
    (21, 999, 2, 422, "VALIDATION_ERROR", ["goal_id"]),    # 目標不存在
    (21, 14, 2, 422, "VALIDATION_ERROR", ["goal_id"]),     # 目標已封存（B7）
], ids=["task-missing", "stale", "not-done", "no-feedback", "goal-missing", "goal-archived"])
def test_l4_link_errors_write_nothing(client, links, query, task_id, goal_id, version, status, code, fields):
    before = count(query, "events")
    assert_error(link(client, task_id, goal_id, version), status, code, fields)
    assert count(query, "events") == before
    if task_id != 999:
        assert task_row(query, task_id)["goal_id"] is None


def test_l4_stale_checked_before_task_state(client, links):
    assert_error(link(client, 25, 11, 9), 409, "STALE_VERSION")


@pytest.mark.parametrize("payload", [
    {"task_id": 21, "goal_id": 11},                                   # 缺 expected_version
    {"goal_id": 11, "expected_version": 2},                           # 缺 task_id
    {"task_id": "21", "goal_id": 11, "expected_version": 2},
    {"task_id": 21, "goal_id": "11", "expected_version": 2},
    {"task_id": 21, "goal_id": True, "expected_version": 2},
    {"task_id": 21, "goal_id": 11, "expected_version": True},
], ids=["no-version", "no-task", "task-str", "goal-str", "goal-bool", "version-bool"])
def test_l4_link_body_types_are_strict(client, links, query, payload):
    r = client.post(f"{API}/goal-links", json=payload)
    assert_error(r, 422, "VALIDATION_ERROR")
    assert link_events(query, 21) == [] and task_row(query, 21) == {"goal_id": None, "version": 2}


# ---------- L5：待關聯清單 ----------

def test_l5_pending_lists_undecided_feedback_tasks_newest_first(client, links):
    body = pending(client)
    assert [i["task_id"] for i in body["items"]] == [26, 22, 21, 23]      # 11-08（26 > 22）、11-07、11-06
    assert body["total"] == 4
    item = next(i for i in body["items"] if i["task_id"] == 22)
    assert item == {"task_id": 22, "title": "任務22", "project_id": None, "scope": "private",
                    "done_date": "2026-11-08", "version": 1}


def test_l5_decided_tasks_leave_pending_including_unlink(client, links):
    assert link(client, 21, 11, 2).status_code == 200
    assert link(client, 26, None, 1).status_code == 200                    # 選過不關聯也不再列
    assert [i["task_id"] for i in pending(client)["items"]] == [22, 23]


def test_l5_pending_does_not_call_ai(client, links, query):
    pending(client)
    assert count(query, "ai_runs") == 0


# ---------- L6～L9：統計 ----------

def seed_stats(seed, rows, extra_tasks=()):
    """rows：(task_id, goal_id, expected_stars, actual_stars, energy, overdue_days)。"""
    seed(BASE)
    tasks = [task_sql(t, goal=str(g), stars=e) for t, g, e, *_ in rows] + list(extra_tasks)
    seed_tasks(seed, tasks, [feedback_sql(t, stars=a, energy=en, overdue=o) for t, _, _, a, en, o in rows])


def stats(client, goal_id):
    r = client.get(f"{API}/goals/{goal_id}/stats")
    assert r.status_code == 200, r.text
    return r.json()


STATS_KEYS = {"progress", "linked", "avg_actual", "avg_expected", "overdue_count", "energy", "energy_plan",
              "min_sample", "judgement", "judgement_note"}


def test_l6_small_sample_shows_distribution_only(client, seed):
    seed_stats(seed, [(31, 11, 3, 4, "high", 0), (32, 11, 3, 4, "mid", 2), (33, 11, 4, 5, "mid", 0),
                      (34, 11, 3, 3, "low", 1)],
               extra_tasks=[task_sql(35, goal="11", status="todo"),            # 未完成：不算
                            task_sql(36, goal="11", done="2026-11-09")])       # 沒有回報：不算
    s = stats(client, 11)
    assert set(s) == STATS_KEYS
    assert s["linked"] == 4
    assert s["avg_actual"] == 4.0 and s["avg_expected"] == 3.3          # 3.25 四捨五入到 3.3
    assert s["overdue_count"] == 2
    assert s["energy"] == {"high": 1, "mid": 2, "low": 1}
    assert s["energy_plan"] == "mid" and s["min_sample"] == 5
    assert s["judgement"] is None and s["judgement_note"] == "樣本 4 筆，不到 5 筆，只顯示不下結論"


@pytest.mark.parametrize("energies, judgement, note", [
    (["mid", "mid", "mid", "high", "low"], "一致", "主要精力為中，與預期相同"),
    (["high", "high", "high", "mid", "low"], "建議檢視", "主要精力為高，預期為中"),
    (["high", "high", "mid", "mid", "low"], "建議檢視", "主要精力並列：高、中"),
    (["low", "low", "mid", "mid", "high", "high"], "建議檢視", "主要精力並列：高、中、低"),
], ids=["consistent", "different", "tie-two", "tie-three"])
def test_l7_judgement_rules(client, seed, energies, judgement, note):
    seed_stats(seed, [(40 + i, 11, 3, 4, e, 0) for i, e in enumerate(energies)])
    s = stats(client, 11)
    assert (s["judgement"], s["judgement_note"]) == (judgement, note)


@pytest.mark.parametrize("linked, target, text, pct", [
    (1, 8, "1 ／ 8 件完成事件", 13),            # 12.5 四捨五入
    (3, 3, "3 ／ 3 件完成事件", 100),
    (4, 3, "4 ／ 3 件完成事件", 100),           # 上限 100
    (2, 0, "2 ／ 0 件完成事件", None),
], ids=["round", "full", "cap", "zero-target"])
def test_l8_growth_progress(client, seed, query, linked, target, text, pct):
    seed_stats(seed, [(50 + i, 11, 3, 4, "mid", 0) for i in range(linked)])
    seed(f"UPDATE goals SET target = {target} WHERE id = 11;")
    assert stats(client, 11)["progress"] == {"text": text, "pct": pct}


def test_l8_time_progress_is_null(client, seed):
    seed_stats(seed, [(60, 12, 3, 4, "low", 0)])
    s = stats(client, 12)
    assert s["progress"] is None and s["linked"] == 1


def test_l8_expectation_progress_is_project_done_ratio(client, seed):
    # 專案 1：3 件完成（其中 2 件關聯到目標 13）、2 件未完成 → 3 ／ 5 = 60%
    seed_stats(seed, [(70, 13, 3, 4, "high", 0), (71, 13, 3, 4, "high", 0)],
               extra_tasks=[task_sql(72), task_sql(73, status="todo"), task_sql(74, status="doing")])
    s = stats(client, 13)
    assert s["progress"] == {"text": "3 ／ 5 件專案任務完成", "pct": 60}
    assert s["linked"] == 2


def test_l8_expectation_project_without_tasks(client, seed):
    seed(BASE)
    assert stats(client, 15)["progress"] == {"text": "0 ／ 0 件專案任務完成", "pct": None}


def test_l9_empty_and_archived_and_missing(client, seed):
    seed(BASE)
    s = stats(client, 14)                                    # 封存的目標照常可查
    assert s["linked"] == 0 and s["avg_actual"] is None and s["avg_expected"] is None
    assert s["energy"] == {"high": 0, "mid": 0, "low": 0} and s["overdue_count"] == 0
    assert s["judgement"] is None and s["judgement_note"] == "樣本 0 筆，不到 5 筆，只顯示不下結論"
    assert_error(client.get(f"{API}/goals/999/stats"), 404, "NOT_FOUND")


def test_l9_link_via_api_counts_in_stats(client, links):
    assert link(client, 21, 11, 2).status_code == 200
    assert link(client, 22, 11, 1).status_code == 200      # 私人任務也算（目標是你自己的）
    assert stats(client, 11)["linked"] == 2
    assert link(client, 21, None, 3).status_code == 200    # 改成不關聯就離開母體
    assert stats(client, 11)["linked"] == 1


# ---------- L10：矩陣 ----------

def test_l10_matrix_lists_active_goals(client, seed):
    seed_stats(seed, [(80, 11, 3, 4, "high", 0), (81, 11, 3, 4, "mid", 0), (82, 13, 3, 4, "low", 0),
                      (83, 14, 3, 4, "high", 0)])        # 14 已封存：不列
    r = client.get(f"{API}/goals/matrix")
    assert r.status_code == 200, r.text
    assert r.json() == {"items": [
        {"goal_id": 11, "title": "學會 SQL 視窗函式", "energy_plan": "mid", "energy": {"high": 1, "mid": 1, "low": 0}, "linked": 2},
        {"goal_id": 12, "title": "每週留 2 小時讀書", "energy_plan": "low", "energy": {"high": 0, "mid": 0, "low": 0}, "linked": 0},
        {"goal_id": 13, "title": "會員系統準時上線", "energy_plan": "high", "energy": {"high": 0, "mid": 0, "low": 1}, "linked": 1},
        {"goal_id": 15, "title": "空專案目標", "energy_plan": "low", "energy": {"high": 0, "mid": 0, "low": 0}, "linked": 0},
    ]}


# ---------- L11：認證 ----------

@pytest.mark.parametrize("method, path", [
    ("POST", "/goal-links"), ("GET", "/goal-links/pending"), ("GET", "/goals/11/stats"), ("GET", "/goals/matrix"),
])
def test_l11_endpoints_require_token(app, links, query, method, path):
    with TestClient(app) as anon:
        r = anon.request(method, f"{API}{path}",
                         json={"task_id": 21, "goal_id": 11, "expected_version": 2} if method == "POST" else None)
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert link_events(query, 21) == []
