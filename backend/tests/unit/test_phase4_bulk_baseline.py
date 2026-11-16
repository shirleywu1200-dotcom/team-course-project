"""Phase 4：整批順延與基準更正（AC-14～25 的 Dev 單元測試，todo 4.1–4.9）。"""

from datetime import date, timedelta

import pytest

from tests.unit.seeds import BASE

PREVIEW = "/api/v1/projects/1/bulk-shift/preview"
COMMIT = "/api/v1/projects/1/bulk-shift/commit"
# 專案 1 未完成任務：2（阿德 v1）、3（小薇 v4）、4（我 v1）、5（我 v2）；1 已完成（v3）
OPEN_ITEMS = [{"task_id": 2, "expected_version": 1}, {"task_id": 3, "expected_version": 4},
              {"task_id": 4, "expected_version": 1}, {"task_id": 5, "expected_version": 2}]
EXTRA_TASK = """
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, created_at, updated_at)
  VALUES (8, 1, '上線準備', '阿德', 'work', '2026-11-20', '2026-11-30', '2026-11-30', now(), now());
"""


def body(items=None, **kw):
    return {"items": OPEN_ITEMS if items is None else items, "days": 3, "reason": "scope_change_external",
            "note": "客戶延後驗收會議"} | kw


def snapshot(query):
    return query("SELECT id, latest_due, orig_due, version FROM tasks ORDER BY id")


# ---------- 整批順延 ----------

def test_ac14_commit_shifts_selected_tasks_only(client, seed, query):
    seed(BASE + EXTRA_TASK)
    r = client.post(COMMIT, json=body(mark="none"))
    assert r.status_code == 200
    out = r.json()
    assert out["updated"] == 4 and len(out["events"]) == 4
    due = {t["id"]: t for t in query("SELECT id, latest_due, orig_due FROM tasks")}
    assert due[2]["latest_due"] == date(2026, 11, 16) and due[2]["orig_due"] == date(2026, 11, 13)
    assert due[5]["latest_due"] == date(2026, 11, 23)
    assert due[8]["latest_due"] == date(2026, 11, 30)
    batch_ids = {e["batch_id"] for e in query("SELECT batch_id FROM events WHERE kind = 'due'")}
    assert batch_ids == {out["batch_id"]}
    assert query("SELECT days, task_count FROM batches") == [{"days": 3, "task_count": 4}]


def test_ac15_unified_mark_only_on_my_tasks(client, seed, query):
    seed(BASE)
    out = client.post(COMMIT, json=body(mark="none")).json()
    rows = {e["task_id"]: e for e in query("SELECT task_id, mine, mark FROM events WHERE kind = 'due'")}
    assert rows[4] == {"task_id": 4, "mine": True, "mark": "none"}
    assert rows[5]["mark"] == "none"
    assert rows[2] == {"task_id": 2, "mine": False, "mark": None}
    assert out["mine_marked"] == 2


def test_ac16_includes_done_task(client, seed, query):
    seed(BASE)
    before = snapshot(query)
    r = client.post(COMMIT, json=body(OPEN_ITEMS + [{"task_id": 1, "expected_version": 3}], mark="none"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INCLUDES_DONE_TASK"
    assert r.json()["error"]["details"]["tasks"] == [{"task_id": 1, "title": "需求確認"}]
    assert snapshot(query) == before


def test_ac17_one_stale_version_rolls_back_everything(client, seed, query):
    seed(BASE)
    before = snapshot(query)
    items = [dict(i) for i in OPEN_ITEMS]
    items[1]["expected_version"] = 3
    r = client.post(COMMIT, json=body(items, mark="none"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "STALE_VERSION"
    assert r.json()["error"]["details"]["tasks"] == [{"task_id": 3, "expected_version": 3, "current_version": 4}]
    assert snapshot(query) == before
    assert query("SELECT count(*) AS n FROM batches")[0]["n"] == 0
    assert query("SELECT count(*) AS n FROM events")[0]["n"] == 0


def test_failure_midway_rolls_back_batch(client, seed, query):
    """任一項寫入失敗（第 4 項新日期超出範圍）整批回滾，不留下部分批次。"""
    seed(BASE + "UPDATE tasks SET latest_due = '2028-11-09' WHERE id = 5;")
    before = snapshot(query)
    r = client.post(COMMIT, json=body(days=2, mark="none"))
    assert r.json()["error"]["code"] == "DATE_OUT_OF_RANGE"
    assert snapshot(query) == before and query("SELECT count(*) AS n FROM batches")[0]["n"] == 0


def test_ac18_idempotency_key(client, seed, query):
    seed(BASE)
    h = {"Idempotency-Key": "bulk-1"}
    first = client.post(COMMIT, json=body(mark="none"), headers=h)
    second = client.post(COMMIT, json=body(mark="none"), headers=h)
    assert first.json() == second.json()
    assert query("SELECT count(*) AS n FROM batches")[0]["n"] == 1
    assert query("SELECT count(*) AS n FROM events WHERE kind = 'due'")[0]["n"] == 4


def test_ac19_preview_writes_nothing_and_warns(client, seed, query):
    seed(BASE)
    before = snapshot(query)
    out = client.post(PREVIEW, json=body(days=-5, reason="prereq_early")).json()
    assert snapshot(query) == before and query("SELECT count(*) AS n FROM events")[0]["n"] == 0
    rows = {r["task_id"]: r for r in out["items"]}
    assert rows[2]["to"] == "2026-11-08" and "BEFORE_TODAY" in rows[2]["warnings"]
    assert "BEFORE_START" in rows[4]["warnings"]
    assert (out["mine_count"], out["mark_required"]) == (2, True)


def test_preview_without_my_tasks(client, seed):
    seed(BASE)
    out = client.post(PREVIEW, json=body([{"task_id": 2, "expected_version": 1}], reason=None)).json()
    assert (out["mine_count"], out["mark_required"]) == (0, False)


def test_commit_requires_mark_when_selection_has_my_tasks(client, seed, query):
    seed(BASE)
    r = client.post(COMMIT, json=body())
    assert r.json()["error"]["code"] == "MARK_REQUIRED"
    assert query("SELECT count(*) AS n FROM batches")[0]["n"] == 0


def test_commit_without_my_tasks_needs_no_mark(client, seed):
    seed(BASE)
    out = client.post(COMMIT, json=body([{"task_id": 2, "expected_version": 1}])).json()
    assert out["mine_marked"] == 0 and out["updated"] == 1


def test_commit_with_defer_mark(client, seed, query):
    seed(BASE)
    client.post(COMMIT, json=body(defer_mark=True))
    marks = {e["task_id"]: e["mark"] for e in query("SELECT task_id, mark FROM events WHERE kind = 'due'")}
    assert marks[4] is None and marks[5] is None


@pytest.mark.parametrize(("items", "days", "code"), [
    ([], 3, "EMPTY_SELECTION"),
    (OPEN_ITEMS, 0, "VALIDATION_ERROR"),
    (OPEN_ITEMS, 366, "VALIDATION_ERROR"),
    ([{"task_id": 7, "expected_version": 1}], 3, "VALIDATION_ERROR"),   # 別的專案
    ([{"task_id": 999, "expected_version": 1}], 3, "VALIDATION_ERROR"),
    ([{"task_id": 2, "expected_version": 1}] * 2, 3, "VALIDATION_ERROR"),
])
def test_bulk_validation(client, seed, items, days, code):
    seed(BASE)
    for url in (PREVIEW, COMMIT):
        r = client.post(url, json=body(items, days=days, mark="none"))
        assert r.json()["error"]["code"] == code


def test_bulk_reason_direction(client, seed):
    seed(BASE)
    r = client.post(COMMIT, json=body(days=-2, reason="wait_external", mark="none"))
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_bulk_events_filterable_by_batch(client, seed, query):
    seed(BASE)
    out = client.post(COMMIT, json=body(mark="none")).json()
    rows = query("SELECT id, origin, origin_ref FROM events WHERE batch_id = :b ORDER BY id", b=out["batch_id"])
    assert [r["id"] for r in rows] == out["events"]
    assert all(r["origin"] == "bulk" and r["origin_ref"] == out["batch_id"] for r in rows)


# ---------- 基準更正 ----------

BP = "/api/v1/tasks/{}/baseline-correction/preview"
BC = "/api/v1/tasks/{}/baseline-correction/commit"


def bpreview(client, task_id=3, **kw):
    b = {"new_orig_due": "2026-11-14", "type": "correction", "reason": "plan_date_wrong",
         "expected_version": 4} | kw
    return client.post(BP.format(task_id), json=b)


def test_ac20_preview_returns_token_and_impact_without_changing_tasks(client, seed, query):
    seed(BASE)
    before = snapshot(query)
    r = bpreview(client).json()
    assert r["confirmation_token"] and r["expires_at"].startswith("2026-11-11T10:10:00+08:00")
    assert r["impact"] == {
        "orig_due": {"from": "2026-11-12", "to": "2026-11-14"},
        "gap_days": {"from": 3, "to": 1},
        "project_delayed_count": {"from": 1, "to": 1},
        "past_due_events_kept": 0,
        "old_value_kept_in_history": True,
    }
    assert snapshot(query) == before and query("SELECT count(*) AS n FROM events")[0]["n"] == 0


def test_preview_delayed_count_drops_when_new_baseline_covers_delay(client, seed):
    seed(BASE)
    r = bpreview(client, new_orig_due="2026-11-15").json()
    assert r["impact"]["project_delayed_count"] == {"from": 1, "to": 0}


def test_ac21_commit_without_ack(client, seed, query):
    seed(BASE)
    token = bpreview(client).json()["confirmation_token"]
    r = client.post(BC.format(3), json={"confirmation_token": token})
    assert r.status_code == 422 and r.json()["error"]["code"] == "ACK_REQUIRED"
    assert query("SELECT orig_due FROM tasks WHERE id = 3") == [{"orig_due": date(2026, 11, 12)}]
    assert client.post(BC.format(3), json={"confirmation_token": token, "ack": True}).status_code == 200


def test_ac22_commit_overwrites_baseline_and_keeps_past_events(client, seed, query):
    seed(BASE)
    client.post("/api/v1/tasks/4/adjust-due", json={"new_due": "2026-11-20", "expected_version": 1, "mark": "worse"})
    past = query("SELECT * FROM events WHERE task_id = 4")
    token = bpreview(client, 4, new_orig_due="2026-11-19", expected_version=2,
                     type="rebaseline", reason="formal_commitment_change").json()["confirmation_token"]
    out = client.post(BC.format(4), json={"confirmation_token": token, "ack": True}).json()
    assert out["task"]["orig_due"] == "2026-11-19" and out["task"]["latest_due"] == "2026-11-20"
    ev = out["event"]
    assert (ev["kind"], ev["field"], ev["from_value"], ev["to_value"]) == ("baseline", "orig_due",
                                                                          "2026-11-18", "2026-11-19")
    assert ev["reason"] == "formal_commitment_change" and ev["origin"] == "baseline_correction"
    assert ev["extra"] == {"type": "rebaseline", "confirmation": "two_step"}
    assert query("SELECT * FROM events WHERE task_id = 4 AND kind = 'due'") == past


def test_ac23_token_used_twice(client, seed):
    seed(BASE)
    token = bpreview(client).json()["confirmation_token"]
    client.post(BC.format(3), json={"confirmation_token": token, "ack": True})
    r = client.post(BC.format(3), json={"confirmation_token": token, "ack": True})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONFIRMATION_INVALID"


def test_ac23_token_expired(client, seed, clock):
    seed(BASE)
    token = bpreview(client).json()["confirmation_token"]
    clock.set(clock.now() + timedelta(minutes=10))
    assert client.post(BC.format(3), json={"confirmation_token": token, "ack": True}
                       ).json()["error"]["code"] == "CONFIRMATION_INVALID"


def test_ac23_task_changed_after_preview(client, seed):
    seed(BASE)
    token = bpreview(client).json()["confirmation_token"]
    client.post("/api/v1/tasks/3/adjust-due", json={"new_due": "2026-11-16", "expected_version": 4})
    assert client.post(BC.format(3), json={"confirmation_token": token, "ack": True}
                       ).json()["error"]["code"] == "CONFIRMATION_INVALID"


def test_token_bound_to_task(client, seed):
    seed(BASE)
    token = bpreview(client).json()["confirmation_token"]
    assert client.post(BC.format(2), json={"confirmation_token": token, "ack": True}
                       ).json()["error"]["code"] == "CONFIRMATION_INVALID"
    assert client.post(BC.format(3), json={"confirmation_token": "nope", "ack": True}
                       ).json()["error"]["code"] == "CONFIRMATION_INVALID"


def test_ac24_done_task_preview_and_commit(client, seed):
    seed(BASE)
    assert bpreview(client, 1, expected_version=3).json()["error"]["code"] == "TASK_DONE"
    token = bpreview(client, 2, expected_version=1).json()["confirmation_token"]
    client.post("/api/v1/tasks/2/complete", json={"expected_version": 1})
    r = client.post(BC.format(2), json={"confirmation_token": token, "ack": True})
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_DONE"


@pytest.mark.parametrize(("kw", "code"), [
    ({"new_orig_due": "2026-11-12"}, "NO_CHANGE"),
    ({"reason": None}, "VALIDATION_ERROR"),
    ({"reason": "bad"}, "VALIDATION_ERROR"),
    ({"type": "other"}, "VALIDATION_ERROR"),
    ({"expected_version": 1}, "STALE_VERSION"),
])
def test_baseline_preview_rejections(client, seed, kw, code):
    seed(BASE)
    assert bpreview(client, **kw).json()["error"]["code"] == code


def test_baseline_later_than_latest_gives_negative_gap(client, seed):
    seed(BASE)
    r = bpreview(client, 3, new_orig_due="2026-11-18").json()
    assert r["impact"]["gap_days"]["to"] == -3


def test_ac25_backend_delayed_count_uses_new_baseline(client, seed, db):
    from app.db.repo.tasks_repo import TaskRepo
    seed(BASE)
    assert db.run(lambda c: TaskRepo(c).delayed_count(1)) == 1
    token = bpreview(client, new_orig_due="2026-11-15").json()["confirmation_token"]
    client.post(BC.format(3), json={"confirmation_token": token, "ack": True})
    assert db.run(lambda c: TaskRepo(c).delayed_count(1)) == 0


def test_single_task_delayed_count_scope(client, seed):
    seed(BASE + "UPDATE tasks SET latest_due = '2026-11-21' WHERE id = 6;")
    r = bpreview(client, 6, new_orig_due="2026-11-21", expected_version=1).json()
    assert r["impact"]["project_delayed_count"] == {"from": 1, "to": 0}
