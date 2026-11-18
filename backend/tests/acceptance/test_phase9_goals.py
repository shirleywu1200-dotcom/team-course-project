"""Phase 9 第二片：目標的建立、編輯、封存（todo 9.5；spec 3.13 FR-GOL-01、02，5.13；#47 B4、B7 與第二片提案）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP 與 SQL 種子操作，不讀實作。

測試清單：
- G1 建立三種類型：201、GoalOut 鍵集合、寫一筆 goal 事件（task_id null、field=created、extra.goal_id）。
- G2 必填與值域：type、title、period、energy_plan 缺漏或不在值域；title、period 只有空白；target 負數。
- G3 expectation：必須帶存在的 project_id；target 忽略存 0；其他類型帶 project_id 回 422。
- G4 列表：預設不含封存、include_archived=true 含封存；依 id 排序；空列表。
- G5 取得：存在回 GoalOut；不存在回 404。
- G6 編輯：每個實際變更欄位一筆事件（前值→後值）；沒有變更不寫事件；type、project_id 不可改；expectation 的 target 忽略；
  編輯 title 為空白回 422 且不寫任何事件；不存在回 404。
- G7 封存：寫 archived_at 與一筆事件；再封存回原值不寫事件；封存後仍可 GET；不存在回 404。
- G8 歷程只增：建立→編輯→封存後事件依序累積，不改舊事件。
- G9 新端點都要 token。
"""

import pytest
from fastapi.testclient import TestClient

from tests.acceptance.helpers import API, count

TS = "'2026-11-01T09:00+08:00'"
NOW = "2026-11-11T10:00:00+08:00"
SEED = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
 (1, '會員系統', 'work', 'manager', {TS}, {TS});
"""
GOAL_KEYS = {"id", "type", "title", "period", "definition", "target", "energy_plan", "project_id", "created_at",
             "archived_at"}


def growth(**kw):
    return {"type": "growth", "title": "學會 SQL 視窗函式", "period": "2026Q4", "definition": "完成 3 個查詢改寫",
            "target": 3, "energy_plan": "high", "project_id": None} | kw


def create(client, payload):
    return client.post(f"{API}/goals", json=payload)


def goal_events(query):
    return query("SELECT * FROM events WHERE kind = 'goal' ORDER BY id")


def assert_validation(r, fields):
    assert r.status_code == 422, r.text
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR" and sorted(err["details"]["fields"]) == sorted(fields)


# ---------- G1～G3：建立 ----------

@pytest.mark.parametrize("payload", [
    growth(),
    growth(type="time", title="每週留 2 小時讀書", target=120, energy_plan="low"),
    growth(type="expectation", title="會員系統準時上線", target=0, energy_plan="mid", project_id=1),
], ids=["growth", "time", "expectation"])
def test_g1_create_goal_writes_one_event(client, seed, query, payload):
    seed(SEED)
    r = create(client, payload)
    assert r.status_code == 201, r.text
    goal = r.json()
    assert set(goal) == GOAL_KEYS
    assert {k: goal[k] for k in payload} == payload
    assert goal["created_at"] == NOW and goal["archived_at"] is None
    evs = goal_events(query)
    assert len(evs) == 1 and count(query, "events") == 1
    ev = evs[0]
    assert (ev["task_id"], ev["task_title"], ev["field"], ev["from_value"], ev["to_value"], ev["origin"]) == \
        (None, "", "created", None, payload["title"], "manual")
    assert ev["extra"] == {"goal_id": goal["id"]} and ev["project_id"] == payload["project_id"]


def test_g1_defaults(client, seed):
    seed(SEED)
    payload = growth()
    del payload["definition"], payload["target"], payload["project_id"]
    goal = create(client, payload).json()
    assert (goal["definition"], goal["target"], goal["project_id"]) == ("", 0, None)


@pytest.mark.parametrize("field", ["type", "title", "period", "energy_plan"])
def test_g2_required_fields(client, seed, query, field):
    seed(SEED)
    payload = growth()
    del payload[field]
    assert_validation(create(client, payload), [field])
    assert count(query, "goals") == 0 and count(query, "events") == 0


@pytest.mark.parametrize("field,value", [
    ("type", "skill"), ("energy_plan", "HIGH"), ("title", "   "), ("period", ""), ("target", -1),
])
def test_g2_value_ranges(client, seed, query, field, value):
    seed(SEED)
    assert_validation(create(client, growth(**{field: value})), [field])
    assert count(query, "goals") == 0 and count(query, "events") == 0


def test_g2_title_and_period_are_trimmed(client, seed):
    seed(SEED)
    goal = create(client, growth(title="  學 SQL  ", period=" 2026Q4 ")).json()
    assert (goal["title"], goal["period"]) == ("學 SQL", "2026Q4")


@pytest.mark.parametrize("project_id", [None, 999])
def test_g3_expectation_needs_existing_project(client, seed, query, project_id):
    seed(SEED)
    assert_validation(create(client, growth(type="expectation", project_id=project_id)), ["project_id"])
    assert count(query, "goals") == 0


def test_g3_expectation_target_is_ignored(client, seed, query):
    seed(SEED)
    goal = create(client, growth(type="expectation", project_id=1, target=80)).json()
    assert goal["target"] == 0
    assert query("SELECT target FROM goals")[0]["target"] == 0


@pytest.mark.parametrize("goal_type", ["growth", "time"])
def test_g3_other_types_must_not_have_project(client, seed, query, goal_type):
    seed(SEED)
    assert_validation(create(client, growth(type=goal_type, project_id=1)), ["project_id"])
    assert count(query, "goals") == 0


# ---------- G4、G5：列表與取得 ----------

def test_g4_list_excludes_archived_by_default(client, seed):
    seed(SEED)
    ids = [create(client, growth(title=f"目標 {i}")).json()["id"] for i in range(3)]
    assert client.post(f"{API}/goals/{ids[1]}/archive").status_code == 200
    default = client.get(f"{API}/goals")
    assert default.status_code == 200
    assert set(default.json()) == {"items"}
    assert [g["id"] for g in default.json()["items"]] == [ids[0], ids[2]]
    every = client.get(f"{API}/goals", params={"include_archived": "true"}).json()["items"]
    assert [g["id"] for g in every] == ids
    for g in every:
        assert set(g) == GOAL_KEYS


def test_g4_empty_list(client, seed):
    seed(SEED)
    assert client.get(f"{API}/goals").json() == {"items": []}


def test_g5_get_goal(client, seed):
    seed(SEED)
    goal = create(client, growth()).json()
    r = client.get(f"{API}/goals/{goal['id']}")
    assert r.status_code == 200 and r.json() == goal
    missing = client.get(f"{API}/goals/999")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"


# ---------- G6：編輯 ----------

def test_g6_each_changed_field_writes_one_event(client, seed, query):
    seed(SEED)
    goal = create(client, growth()).json()
    r = client.patch(f"{API}/goals/{goal['id']}", json={"title": "學會 SQL", "target": 5, "energy_plan": "high",
                                                       "period": "2026Q4"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert set(out) == {"goal", "changes"}
    assert (out["goal"]["title"], out["goal"]["target"]) == ("學會 SQL", 5)
    changes = sorted((c["field"], c["from_value"], c["to_value"]) for c in out["changes"])
    assert changes == [("target", "3", "5"), ("title", "學會 SQL 視窗函式", "學會 SQL")]   # energy_plan、period 沒變
    evs = goal_events(query)[1:]
    assert len(evs) == 2 and all(e["task_id"] is None and e["extra"] == {"goal_id": goal["id"]} for e in evs)


def test_g6_no_change_writes_nothing(client, seed, query):
    seed(SEED)
    goal = create(client, growth()).json()
    r = client.patch(f"{API}/goals/{goal['id']}", json={"title": goal["title"]})
    assert r.status_code == 200 and r.json() == {"goal": goal, "changes": []}
    assert count(query, "events") == 1


def test_g6_type_and_project_cannot_change(client, seed, query):
    seed(SEED)
    goal = create(client, growth()).json()
    r = client.patch(f"{API}/goals/{goal['id']}", json={"type": "expectation", "project_id": 1})
    assert r.status_code == 200 and r.json()["changes"] == []
    assert (r.json()["goal"]["type"], r.json()["goal"]["project_id"]) == ("growth", None)


def test_g6_expectation_target_edit_is_ignored(client, seed, query):
    seed(SEED)
    goal = create(client, growth(type="expectation", project_id=1)).json()
    r = client.patch(f"{API}/goals/{goal['id']}", json={"target": 90})
    assert r.json()["goal"]["target"] == 0 and r.json()["changes"] == []


@pytest.mark.parametrize("body,fields", [
    ({"title": "  "}, ["title"]), ({"period": ""}, ["period"]), ({"energy_plan": "max"}, ["energy_plan"]),
    ({"target": -2}, ["target"]),
])
def test_g6_invalid_edit_writes_nothing(client, seed, query, body, fields):
    seed(SEED)
    goal = create(client, growth()).json()
    assert_validation(client.patch(f"{API}/goals/{goal['id']}", json=body), fields)
    assert count(query, "events") == 1
    assert client.get(f"{API}/goals/{goal['id']}").json() == goal


def test_g6_edit_unknown_goal(client, seed):
    seed(SEED)
    r = client.patch(f"{API}/goals/999", json={"title": "x"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


# ---------- G7、G8：封存與歷程 ----------

def test_g7_archive_once(client, seed, query):
    seed(SEED)
    goal = create(client, growth()).json()
    r = client.post(f"{API}/goals/{goal['id']}/archive")
    assert r.status_code == 200 and r.json()["archived_at"] == NOW
    again = client.post(f"{API}/goals/{goal['id']}/archive")
    assert again.status_code == 200 and again.json() == r.json()
    evs = goal_events(query)
    assert [e["field"] for e in evs] == ["created", "archived_at"]
    assert client.get(f"{API}/goals/{goal['id']}").json()["archived_at"] == NOW   # 封存仍可讀
    missing = client.post(f"{API}/goals/999/archive")
    assert missing.status_code == 404


def test_g8_history_only_grows(client, seed, query):
    seed(SEED)
    goal = create(client, growth()).json()
    first = goal_events(query)
    client.patch(f"{API}/goals/{goal['id']}", json={"title": "新標題"})
    client.post(f"{API}/goals/{goal['id']}/archive")
    evs = goal_events(query)
    assert [e["field"] for e in evs] == ["created", "title", "archived_at"]
    assert evs[0] == first[0]                                       # 舊事件不變


# ---------- G9：認證 ----------

@pytest.mark.parametrize("method,path", [
    ("GET", "/goals"), ("POST", "/goals"), ("GET", "/goals/1"), ("PATCH", "/goals/1"), ("POST", "/goals/1/archive"),
])
def test_g9_goal_endpoints_require_token(app, seed, query, method, path):
    seed(SEED)
    with TestClient(app) as anon:
        r = anon.request(method, f"{API}{path}", json=growth() if method in ("POST", "PATCH") else None)
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert count(query, "goals") == 0 and count(query, "events") == 0
