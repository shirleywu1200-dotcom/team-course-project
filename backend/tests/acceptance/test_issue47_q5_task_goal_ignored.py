"""#47 Q5（PO 2026-11-21 裁定 A）：POST /tasks 帶 goal_id 一律忽略（送了也不存）；關聯只走 POST /goal-links（spec 5.13）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP 與 SQL 種子操作。
"""

import pytest

from tests.acceptance.helpers import API

TS = "'2026-11-01T09:00+08:00'"
GOALS = f"""
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
 (1, 'growth', '學會 SQL', '2026Q4', '', 3, 'mid', NULL, {TS}, NULL),
 (2, 'growth', '舊目標', '2026Q3', '', 3, 'mid', NULL, {TS}, '2026-11-05T09:00+08:00');
"""


def create(client, **extra):
    r = client.post(f"{API}/tasks", json={"title": "報表查詢改寫", "due": "2026-11-20"} | extra)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize("goal_id", [1, 2, 999, None], ids=["active", "archived", "missing", "null"])
def test_goal_id_is_accepted_but_not_stored(client, seed, query, goal_id):
    seed(GOALS)
    task = create(client, goal_id=goal_id)        # 不存在的 id 也不再撞外鍵回 500
    assert task["goal_id"] is None
    assert query("SELECT goal_id FROM tasks WHERE id = :i", i=task["id"])[0]["goal_id"] is None


def test_created_task_enters_pending_links_after_feedback(client, seed, query):
    seed(GOALS)
    task = create(client, goal_id=1)
    done = client.post(f"{API}/tasks/{task['id']}/complete",
                       json={"expected_version": task["version"], "done_date": "2026-11-10"})
    assert done.status_code == 200, done.text
    rubric = query("SELECT max(id) AS id FROM rubrics")[0]["id"]
    fb = client.put(f"{API}/tasks/{task['id']}/feedback",
                    json={"actual_stars": 4, "energy": "mid", "rubric_id": rubric})
    assert fb.status_code == 201, fb.text   # 第一次存完成回報為新建
    pending = client.get(f"{API}/goal-links/pending").json()["items"]
    assert [i["task_id"] for i in pending] == [task["id"]]          # 只有 POST /goal-links 能做關聯決定
    assert client.get(f"{API}/goals/1/stats").json()["linked"] == 0  # 沒有算進目標統計
