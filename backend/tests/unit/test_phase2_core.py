"""Phase 2：write_event、樂觀鎖、專案、任務（AC-05、26、29、57 的 Dev 單元測試）。"""

from datetime import date

import pytest

from app.db.repo.tasks_repo import TaskRepo
from app.domain import tasks as tasks_domain
from app.domain.events import write_event
from app.errors import DomainError
from tests.unit.seeds import BASE, RUBRIC

# ---------- write_event 與樂觀鎖 ----------


def test_write_event_snapshots_title_mine_and_project(db, seed):
    seed(BASE)
    ev = db.run(lambda c: write_event(c, task_id=4, kind="task", field="x", origin="manual"))
    assert (ev["task_title"], ev["mine"], ev["project_id"]) == ("確認驗收條件", True, 1)
    ev2 = db.run(lambda c: write_event(c, task_id=2, kind="task", field="x", origin="manual"))
    assert ev2["mine"] is False


def test_write_event_without_task_uses_empty_title(db, seed):
    seed(BASE)
    ev = db.run(lambda c: write_event(c, project_id=1, kind="project", field="name", origin="manual"))
    assert ev["task_title"] == "" and ev["task_id"] is None


def test_write_event_rejects_unknown_fields(db, seed):
    seed(BASE)
    with pytest.raises(ValueError):
        db.run(lambda c: write_event(c, kind="task", field="x", origin="manual", bogus=1))


def test_write_event_ts_comes_from_clock(db, seed, clock):
    seed(BASE)
    ev = db.run(lambda c: write_event(c, task_id=2, kind="task", field="x", origin="manual"))
    assert ev["ts"] == clock.now()


def test_get_for_update_checks_version(db, seed):
    seed(BASE)
    assert db.run(lambda c: TaskRepo(c).get_for_update(3, 4))["id"] == 3
    with pytest.raises(DomainError) as e:
        db.run(lambda c: TaskRepo(c).get_for_update(3, 3))
    assert e.value.code == "STALE_VERSION" and e.value.details["current_version"] == 4
    with pytest.raises(DomainError) as e:
        db.run(lambda c: TaskRepo(c).get_for_update(999, 1))
    assert e.value.code == "NOT_FOUND"


def test_update_bumps_version(db, seed):
    seed(BASE)
    t = db.run(lambda c: TaskRepo(c).update(2, {"done_when": "x"}))
    assert t["version"] == 2

# ---------- 專案 ----------


def test_create_list_get_archive_project(client, query):
    p = client.post("/api/v1/projects", json={"name": "  新專案  ", "scope": "private"}).json()
    assert p["name"] == "新專案" and p["scope"] == "private" and p["audience"] == "manager"
    assert client.get(f"/api/v1/projects/{p['id']}").json()["task_count"] == 0
    assert client.get("/api/v1/projects").json()["total"] == 1
    client.post(f"/api/v1/projects/{p['id']}/archive")
    assert client.get("/api/v1/projects").json()["total"] == 0
    assert client.get("/api/v1/projects?include_archived=true").json()["total"] == 1
    fields = [e["field"] for e in query("SELECT field FROM events WHERE project_id = :p ORDER BY id", p=p["id"])]
    assert fields == ["created", "archived_at"]


def test_create_project_requires_name(client):
    r = client.post("/api/v1/projects", json={"name": "   "})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["name"]


def test_ac26_patch_writes_one_event_per_changed_field(client, seed, query):
    seed(BASE)
    r = client.patch("/api/v1/projects/1", json={"name": "會員系統 2.1", "scope": "private"}).json()
    assert {(c["field"], c["from_value"], c["to_value"]) for c in r["changes"]} == {
        ("name", "會員系統 2.0 改版", "會員系統 2.1"), ("scope", "work", "private")}
    again = client.patch("/api/v1/projects/1", json={"name": "會員系統 2.1", "scope": "private"}).json()
    assert again["changes"] == []
    assert len(query("SELECT id FROM events WHERE kind = 'project' AND project_id = 1")) == 2


def test_project_not_found(client):
    assert client.get("/api/v1/projects/999").json()["error"]["code"] == "NOT_FOUND"


def test_project_baseline_saved_at(client, seed):
    seed(BASE + "INSERT INTO events (ts, project_id, task_title, kind, field, origin) "
                "VALUES ('2026-11-02T09:00+08:00', 1, '', 'baseline', 'import', 'import');")
    assert client.get("/api/v1/projects/1").json()["baseline_saved_at"].startswith("2026-11-02T09:00:00+08:00")

# ---------- 任務 ----------


def test_ac05_create_single_task(client, seed, query):
    seed(BASE)
    t = client.post("/api/v1/tasks", json={"title": "確認驗收條件", "due": "2026-11-18",
                                           "done_when": "客戶回覆確認"}).json()
    assert t["project_id"] is None and t["orig_due"] == t["latest_due"] == "2026-11-18"
    assert t["owner"] == "我" and t["star_source"] == "self" and t["start"] == "2026-11-11"
    assert t["rubric_id"] == 1   # 只有系統種子的量表 v0 時，填入它
    ev = query("SELECT * FROM events WHERE task_id = :t", t=t["id"])
    assert len(ev) == 1 and ev[0]["kind"] == "task" and ev[0]["project_id"] is None


def test_create_task_records_origin_from_candidate(db, seed, query):
    """Issue #2（R-01）：從待配對候選建立任務時，created 事件記下依據的候選與原句來源。"""
    seed(BASE + """
    INSERT INTO sources (id, channel, speaker, excerpt_hash, received_at, expires_at)
      VALUES (5, 'paste', '阿德', 'h5', now(), now());
    INSERT INTO candidates (id, source_id, kind, certainty, created_at)
      VALUES (12, 5, 'unmatched', 'to_match', now());
    """)
    t = db.run(lambda c: tasks_domain.create_task(c, title="報表處理", due=date(2026, 12, 20), owner="阿德",
                                                  project_id=1, origin="candidate", origin_ref=12, source_id=5))
    ev = query("SELECT origin, origin_ref, source_id, mine FROM events WHERE task_id = :t AND field = 'created'",
               t=t["id"])
    assert ev == [{"origin": "candidate", "origin_ref": 12, "source_id": 5, "mine": False}]


def test_create_task_defaults_to_manual_origin(db, seed, query):
    seed(BASE)
    t = db.run(lambda c: tasks_domain.create_task(c, title="x", due=date(2026, 11, 20)))
    assert query("SELECT origin, origin_ref, source_id FROM events WHERE task_id = :t", t=t["id"]) == [
        {"origin": "manual", "origin_ref": None, "source_id": None}]


def test_create_task_in_project_inherits_scope_and_active_rubric(client, seed):
    seed(BASE + RUBRIC + "UPDATE projects SET scope = 'private' WHERE id = 2;")
    t = client.post("/api/v1/tasks", json={"title": "x", "due": "2026-11-20", "project_id": 2}).json()
    assert t["scope"] == "private" and t["rubric_id"] == 2   # 目前量表 = version 最大者（RUBRIC 為 v1，id 2）


def test_create_task_unknown_project(client, seed):
    seed(BASE)
    r = client.post("/api/v1/tasks", json={"title": "x", "due": "2026-11-20", "project_id": 99})
    assert r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(("expected", "suggested", "source"), [
    (3, None, "self"), (4, 4, "ai_accepted"), (2, 4, "ai_edited")])
def test_star_source_decided_by_server(client, seed, expected, suggested, source):
    seed(BASE)
    body = {"title": "x", "due": "2026-11-20", "expected_stars": expected, "star_source": "import_default"}
    if suggested is not None:
        body["suggested_stars"] = suggested
    assert client.post("/api/v1/tasks", json=body).json()["star_source"] == source


def test_task_start_defaults_to_due_when_due_is_past(client, seed):
    seed(BASE)
    t = client.post("/api/v1/tasks", json={"title": "補登", "due": "2026-11-05"}).json()
    assert t["start"] == "2026-11-05"


def test_list_tasks_filters(client, seed):
    seed(BASE)
    assert client.get("/api/v1/tasks?project_id=none").json()["total"] == 1
    assert client.get("/api/v1/tasks?project_id=1&owner=我").json()["total"] == 3
    assert client.get("/api/v1/tasks?status=done").json()["total"] == 1
    assert client.get("/api/v1/tasks?due_before=2026-11-14").json()["total"] == 2
    assert client.get("/api/v1/tasks?project_id=abc").status_code == 422


def test_task_detail_includes_history(client, seed):
    seed(BASE)
    client.post("/api/v1/tasks/2/block", json={"expected_version": 1})
    d = client.get("/api/v1/tasks/2").json()
    assert d["task"]["blocked"] is True and d["events"][0]["field"] == "blocked"


def test_status_todo_doing_and_done_rejected(client, seed, query):
    seed(BASE)
    r = client.post("/api/v1/tasks/2/status", json={"status": "doing", "expected_version": 1}).json()
    assert r["task"]["status"] == "doing" and r["event"]["kind"] == "status"
    assert client.post("/api/v1/tasks/1/status", json={"status": "todo", "expected_version": 3}
                       ).json()["error"]["code"] == "TASK_DONE"
    assert client.post("/api/v1/tasks/2/status", json={"status": "done", "expected_version": 2}
                       ).status_code == 422


def test_block_and_unblock(client, seed):
    seed(BASE)
    assert client.post("/api/v1/tasks/2/block", json={"expected_version": 1}).json()["task"]["blocked"]
    r = client.post("/api/v1/tasks/2/block", json={"blocked": False, "expected_version": 2}).json()
    assert r["task"]["blocked"] is False and r["task"]["version"] == 3


def test_done_task_cannot_be_blocked(client, seed):
    seed(BASE)
    r = client.post("/api/v1/tasks/1/block", json={"expected_version": 3})
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_DONE"


def test_ac29_owner_change_keeps_old_events(client, seed, query):
    seed(BASE)
    client.post("/api/v1/tasks/4/block", json={"expected_version": 1})
    r = client.patch("/api/v1/tasks/4/owner", json={"owner": "阿德", "expected_version": 2}).json()
    assert r["task"]["owner"] == "阿德"
    assert (r["event"]["from_value"], r["event"]["to_value"]) == ("我", "阿德")
    old = query("SELECT mine, task_title FROM events WHERE task_id = 4 AND field = 'blocked'")
    assert old == [{"mine": True, "task_title": "確認驗收條件"}]
    assert client.patch("/api/v1/tasks/4/owner", json={"owner": "阿德", "expected_version": 3}
                        ).json()["error"]["code"] == "NO_CHANGE"


def test_title_snapshot_survives_rename(db, seed, query):
    seed(BASE)
    db.run(lambda c: write_event(c, task_id=2, kind="task", field="x", origin="manual"))
    db.run(lambda c: TaskRepo(c).update(2, {"title": "畫面規格 v2"}))
    assert query("SELECT task_title FROM events WHERE task_id = 2") == [{"task_title": "畫面規格 v1"}]


def test_complete_task(client, seed):
    seed(BASE)
    r = client.post("/api/v1/tasks/2/complete", json={"expected_version": 1}).json()
    assert r["task"]["status"] == "done" and r["task"]["done_date"] == "2026-11-11"
    assert r["feedback_required"] is True and r["event"]["to_value"] == "done"
    assert client.post("/api/v1/tasks/2/complete", json={"expected_version": 2}).json()["error"]["code"] == \
        "TASK_DONE"


def test_complete_date_cannot_be_future(client, seed):
    seed(BASE)
    r = client.post("/api/v1/tasks/2/complete", json={"expected_version": 1, "done_date": "2026-11-12"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_stale_version_via_api(client, seed):
    seed(BASE)
    r = client.post("/api/v1/tasks/3/block", json={"expected_version": 1})
    assert r.status_code == 409 and r.json()["error"]["code"] == "STALE_VERSION"

# ---------- AC-57 原子性 ----------


def test_ac57_exception_after_event_leaves_nothing(db, seed, query, monkeypatch):
    seed(BASE)

    def boom(self, task_id, fields):
        raise RuntimeError("中途失敗")

    monkeypatch.setattr(TaskRepo, "update", boom)
    with pytest.raises(RuntimeError):
        db.run(lambda c: tasks_domain.complete_task(c, 2, 1, date(2026, 11, 11)))
    assert query("SELECT count(*) AS n FROM events")[0]["n"] == 0
    assert query("SELECT status, version FROM tasks WHERE id = 2") == [{"status": "todo", "version": 1}]


def test_ac57_api_failure_rolls_back(app, db, seed, query, monkeypatch):
    from fastapi.testclient import TestClient
    seed(BASE)
    monkeypatch.setattr(TaskRepo, "update", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    with TestClient(app, raise_server_exceptions=False, headers={"Authorization": "Bearer test-token"}) as c:
        r = c.post("/api/v1/tasks/2/block", json={"expected_version": 1})
    assert r.status_code == 500
    assert query("SELECT count(*) AS n FROM events")[0]["n"] == 0
