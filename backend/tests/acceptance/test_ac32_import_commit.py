"""AC-32：匯入保存建立任務與基準事件，單一交易（FR-IMP-06、07）。"""

import contextlib

from tests.acceptance.helpers import API, SEED_BASE, count, created

ROWS = [
    {"index": 0, "title": "需求確認", "owner": "我", "start": "2026-11-16", "end": "2026-11-18"},
    {"index": 1, "title": "畫面設計", "owner": "小薇", "start": "2026-11-17", "end": "2026-11-21"},
    {"index": 2, "title": "上線準備", "owner": "我", "start": "2026-11-24", "end": "2026-11-26"},
]

# 測試端注入失敗：第 3 列寫入 tasks 時資料庫丟例外。
FAIL_TRIGGER = """
CREATE FUNCTION qc_fail_task() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.title = '上線準備' THEN RAISE EXCEPTION 'qc injected failure'; END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER qc_fail_task BEFORE INSERT ON tasks FOR EACH ROW EXECUTE FUNCTION qc_fail_task();
"""


def _commit(client, target="new", rows=ROWS):
    return client.post(f"{API}/projects/import/commit", json={"target": target, "new_name": "匯入專案", "rows": rows})


def test_ac32_commit_creates_tasks_with_baseline_dates(client, query):
    body = created(_commit(client))
    assert body["created"] == 3 and body["skipped"] == 0
    proj = query("SELECT id, name FROM projects")
    assert proj == [{"id": body["project_id"], "name": "匯入專案"}]
    tasks = query("SELECT title, owner_name, start_date::text AS s, orig_due::text AS o, latest_due::text AS l, "
                  "star_source, project_id FROM tasks ORDER BY id")
    assert [(t["title"], t["owner_name"], t["s"], t["o"], t["l"]) for t in tasks] == [
        ("需求確認", "我", "2026-11-16", "2026-11-18", "2026-11-18"),
        ("畫面設計", "小薇", "2026-11-17", "2026-11-21", "2026-11-21"),
        ("上線準備", "我", "2026-11-24", "2026-11-26", "2026-11-26"),
    ]
    assert {t["star_source"] for t in tasks} == {"import_default"}
    assert {t["project_id"] for t in tasks} == {body["project_id"]}


def test_ac32_commit_writes_exactly_one_baseline_event(client, query):
    body = created(_commit(client))
    events = query("SELECT id, kind, origin, project_id FROM events WHERE kind = 'baseline'")
    assert events == [{"id": body["event_id"], "kind": "baseline", "origin": "import", "project_id": body["project_id"]}]


def test_ac32_skipped_rows_are_counted_not_imported(client, query):
    rows = ROWS + [{"index": 3, "title": "壞列", "owner": "我", "start": None, "end": None, "skip": True}]
    body = created(_commit(client, rows=rows))
    assert (body["created"], body["skipped"]) == (3, 1)
    assert count(query, "tasks") == 3
    assert query("SELECT count(*) AS n FROM events WHERE kind = 'baseline'")[0]["n"] == 1


def test_ac32_import_into_existing_project(client, seed, query):
    seed(SEED_BASE)
    assert created(_commit(client, target=3))["project_id"] == 3
    assert count(query, "projects") == 3
    assert query("SELECT count(*) AS n FROM tasks WHERE project_id = 3")[0]["n"] == 1 + 3


def test_ac32_imported_tasks_use_current_rubric(client, seed, query):
    seed("""INSERT INTO rubrics (version, levels, source, created_at)
            VALUES (1, '["a","b","c","d","e"]', 'interview', '2026-11-10T09:00+08:00');""")
    current = query("SELECT id FROM rubrics ORDER BY version DESC LIMIT 1")[0]["id"]
    created(_commit(client))
    assert {t["rubric_id"] for t in query("SELECT rubric_id FROM tasks")} == {current}


def test_ac32_failure_midway_leaves_nothing(client, seed, query):
    seed(FAIL_TRIGGER)
    status = None
    with contextlib.suppress(Exception):  # TestClient 預設會把伺服器例外往外丟
        status = _commit(client).status_code
    assert status is None or status >= 500
    for t in ("projects", "tasks", "events"):
        assert count(query, t) == 0


def test_spec51_import_commit_returns_200(client):
    """spec 5.1（DA-20）：回 201 的只有 POST /projects、/tasks、/events/{id}/annotations，其餘 POST 回 200。"""
    assert _commit(client).status_code == 200


def test_fr_imp07_unknown_target_project_is_not_found(client, seed, query):
    """審查 2-8(b)。"""
    seed(SEED_BASE)
    before = {t: count(query, t) for t in ("projects", "tasks", "events")}
    r = _commit(client, target=999)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
    assert {t: count(query, t) for t in before} == before


def test_fr_imp07_new_target_without_name_is_rejected(client, query):
    """審查 2-8(c)：新建專案的名稱必填（FR-PRJ-01）。"""
    r = client.post(f"{API}/projects/import/commit", json={"target": "new", "rows": ROWS})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    for t in ("projects", "tasks", "events"):
        assert count(query, t) == 0


def test_spec51_same_idempotency_key_imports_once(client, query):
    """審查 2-8(d)：同一 Idempotency-Key 連送兩次，第二次回首次結果。"""
    payload = {"target": "new", "new_name": "匯入專案", "rows": ROWS}
    headers = {"Idempotency-Key": "qc-import-1"}
    first = client.post(f"{API}/projects/import/commit", json=payload, headers=headers)
    second = client.post(f"{API}/projects/import/commit", json=payload, headers=headers)
    body = created(first)
    assert second.status_code == first.status_code
    assert second.json() == body
    assert count(query, "projects") == 1
    assert count(query, "tasks") == 3
    assert query("SELECT count(*) AS n FROM events WHERE kind = 'baseline'")[0]["n"] == 1
