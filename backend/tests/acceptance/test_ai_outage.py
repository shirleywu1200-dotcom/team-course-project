"""13.3 AI 失效演練（spec AC-50、FR-AI-03；docs/dev-b/13-3-sdd.md）。

AI 全關（FakeAIClient(available=False)）時，掃過現有 AI 端點都走退路，非 AI 主流程照常。
各端點的細節由專屬測試涵蓋，這裡只回答「AI 全關時每個端點是否都退得下來」。
AI-02（⛔ D-01）端點尚未落地，落地時加在這裡。
"""

import pytest

from app.ai.client import FakeAIClient

API = "/api/v1"
TS = "'2026-11-01T09:00+08:00'"
DATA = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '工作專案', 'work', 'manager', {TS}, {TS});
INSERT INTO goals (id, type, title, period, target, energy_plan, created_at) VALUES
  (1, 'growth', '提升簡報能力', '2026Q4', 3, 'high', {TS}),
  (2, 'growth', '每週寫技術筆記', '2026Q4', 3, 'mid', {TS});
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, version, created_at, updated_at) VALUES
  (1, 1, '畫面規格', '我', 'work', '2026-11-01', '2026-11-13', '2026-11-13', 'todo', NULL, 1, {TS}, {TS}),
  (2, 1, '本週完成', '我', 'work', '2026-11-01', '2026-11-10', '2026-11-10', 'done', '2026-11-10', 2, {TS}, {TS});
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, goal_id, version, created_at, updated_at) VALUES
  (3, 1, '筆記整理', '我', 'work', '2026-11-01', '2026-11-07', '2026-11-07', 'done', '2026-11-07', 2, 3, {TS}, {TS});
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    delta_days, mine) VALUES
  (11, '2026-11-10T18:00+08:00', 1, 2, '本週完成', 'status', 'status', 'todo', 'done', 'manual', NULL, true),
  (12, '2026-11-07T18:00+08:00', 1, 3, '筆記整理', 'goal', 'goal_id', NULL, '2', 'manual', NULL, true);
INSERT INTO completion_feedback (task_id, actual_stars, energy, overdue_days, rubric_id, created_at)
  SELECT t, 3, 'mid', 0, (SELECT id FROM rubrics ORDER BY version LIMIT 1), {TS} FROM (VALUES (2), (3)) v(t);
"""


@pytest.fixture
def ai():
    return FakeAIClient(available=False)


@pytest.fixture(autouse=True)
def data(seed):
    seed(DATA)


def test_health_reports_ai_unavailable_db_ok(client):
    assert client.get(f"{API}/meta/health").json() == {"db": "ok", "ai": "unavailable"}


@pytest.mark.parametrize(("node", "method", "path", "body"), [
    ("AI-05", "post", "/reports/weekly/draft", {"week_start": "2026-11-09"}),
    ("AI-03", "post", "/goal-links/suggest", None),
    ("AI-01", "post", "/ingest", {"text": "[10:12] 阿德：畫面規格延到 11/20", "project_id": 1}),
    ("AI-07", "post", "/projects/import/preview", {"text": "工項,PIC,起,交期\n需求確認,我,11/16,11/18"}),
])
def test_ai_endpoints_fall_back_with_200(client, node, method, path, body):
    r = getattr(client, method)(f"{API}{path}", json=body)
    assert r.status_code == 200, node
    assert r.json()["ai_status"] == "unavailable", node


def test_goal_report_falls_back_after_ai_call(client, query):
    """AI-04：目標 2 有關聯，會真的呼叫 AI；失敗後 200、不給草稿，畫面改顯示目標統計（spec 5.13）。

    沒有關聯的目標依規則不呼叫 AI，也回 unavailable，所以另外看 ai_runs，確認走的是「呼叫失敗」這條路。
    """
    r = client.post(f"{API}/goals/2/report/draft")
    assert r.status_code == 200
    assert r.json() | {"id": None, "updated_at": None} == {
        "id": None, "goal_id": 2, "ai_status": "unavailable", "excluded_private": 0, "draft": None,
        "validated": False, "manual_text": None, "updated_at": None}
    # ai_runs.status 記細分值：供應商不可用是 error（spec 5.3）；AIUnavailable 立刻停，只有一列
    assert query("SELECT node_id, status, error FROM ai_runs") == [
        {"node_id": "AI-04", "status": "error", "error": "AIUnavailable"}]
    assert client.get(f"{API}/goals/2/stats").json()["linked"] == 1


def test_rubric_interview_returns_503(client):
    r = client.post(f"{API}/rubrics/interview", json={"q1": "交付完成", "q2": "超出範圍", "q3": "否"})
    assert r.status_code == 503


def test_non_ai_flow_unaffected(client):
    project = client.post(f"{API}/projects", json={"name": "新專案"})
    assert project.status_code == 201
    task = client.post(f"{API}/tasks", json={"title": "新任務", "due": "2026-11-20",
                                             "project_id": project.json()["id"]})
    assert task.status_code == 201
    moved = client.post(f"{API}/tasks/1/adjust-due", json={"new_due": "2026-11-20", "expected_version": 1,
                                                           "mark": "worse"})
    assert moved.status_code == 200
    done = client.post(f"{API}/tasks/1/complete", json={"expected_version": 2})
    assert done.status_code == 200
    rubric = client.get(f"{API}/rubrics").json()["items"][0]["id"]
    fb = client.put(f"{API}/tasks/1/feedback", json={"actual_stars": 4, "energy": "mid", "rubric_id": rubric})
    assert fb.status_code == 201
    pending = client.get(f"{API}/goal-links/pending").json()["items"]
    version = next(i["version"] for i in pending if i["task_id"] == 1)
    link = client.post(f"{API}/goal-links", json={"task_id": 1, "goal_id": 1, "expected_version": version})
    assert link.status_code == 200
