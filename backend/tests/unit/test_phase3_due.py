"""Phase 3：預計完成日調整與時間管理註記（AC-01～10、12、12a、13，todo 3.1–3.9）。"""

import threading
import time
from datetime import date

import pytest

from app.domain.due import adjust_due
from app.errors import DomainError
from tests.unit.seeds import BASE

ADJ = "/api/v1/tasks/{}/adjust-due"


def adjust(client, task_id, **body):
    return client.post(ADJ.format(task_id), json=body)


# ---------- AC-01～07 ----------

def test_ac01_others_task_needs_no_mark(client, seed, query):
    seed(BASE)
    r = adjust(client, 2, new_due="2026-11-16", expected_version=1, reason="wait_external")
    assert r.status_code == 200
    body = r.json()
    assert body["task"]["latest_due"] == "2026-11-16" and body["task"]["orig_due"] == "2026-11-13"
    assert body["event"]["mine"] is False and body["event"]["mark"] is None and body["needs_mark"] is False


def test_ac02_my_task_without_mark_is_rejected_and_nothing_changes(client, seed, query):
    seed(BASE)
    r = adjust(client, 4, new_due="2026-11-20", expected_version=1, reason="underestimated")
    assert r.status_code == 422 and r.json()["error"]["code"] == "MARK_REQUIRED"
    assert query("SELECT latest_due, version FROM tasks WHERE id = 4") == [
        {"latest_due": date(2026, 11, 18), "version": 1}]
    assert query("SELECT count(*) AS n FROM events")[0]["n"] == 0


def test_ac03_mark_none_records_delta_and_keeps_orig(client, seed):
    seed(BASE)
    body = adjust(client, 4, new_due="2026-11-21", expected_version=1, reason="scope_change_external",
                  mark="none").json()
    assert body["event"]["mark"] == "none" and body["event"]["delta_days"] == 3
    assert body["task"]["orig_due"] == "2026-11-18" and body["task"]["version"] == 2


def test_ac04_defer_mark(client, seed):
    seed(BASE)
    body = adjust(client, 4, new_due="2026-11-20", expected_version=1, defer_mark=True).json()
    assert body["event"]["mark"] is None and body["needs_mark"] is True
    assert client.get("/api/v1/stats/time-management").json()["unmarked"] == 1


def test_ac05_single_task_adjust(client, seed, query):
    seed(BASE)
    body = adjust(client, 6, new_due="2026-11-21", expected_version=1, mark="worse").json()
    assert body["event"]["project_id"] is None
    assert query("SELECT count(*) AS n FROM events WHERE project_id IS NULL AND kind = 'due'")[0]["n"] == 1


def test_ac06_done_task(client, seed):
    seed(BASE)
    r = adjust(client, 1, new_due="2026-11-20", expected_version=3, mark="none")
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_DONE"


def test_ac07_no_change(client, seed):
    seed(BASE)
    r = adjust(client, 2, new_due="2026-11-13", expected_version=1)
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_CHANGE"


@pytest.mark.parametrize(("new_due", "ok"), [
    ("2025-11-11", True), ("2025-11-10", False), ("2028-11-10", True), ("2028-11-11", False)])
def test_date_range_365_back_730_forward(client, seed, new_due, ok):
    seed(BASE)
    r = adjust(client, 2, new_due=new_due, expected_version=1)
    assert (r.status_code == 200) is ok
    if not ok:
        assert r.json()["error"]["code"] == "DATE_OUT_OF_RANGE"


def test_before_start_is_warning_not_error(client, seed):
    seed(BASE)
    body = adjust(client, 4, new_due="2026-11-12", expected_version=1, mark="better",
                  reason="finished_early").json()
    assert body["warnings"] == ["BEFORE_START"] and body["event"]["delta_days"] == -6


def test_before_today_is_allowed_without_warning(client, seed):
    seed(BASE)
    body = adjust(client, 2, new_due="2026-11-10", expected_version=1).json()
    assert body["warnings"] == []


def test_mark_on_others_task_is_ignored_with_warning(client, seed):
    seed(BASE)
    body = adjust(client, 2, new_due="2026-11-16", expected_version=1, mark="worse").json()
    assert body["event"]["mark"] is None and body["warnings"] == ["MARK_IGNORED"]


def test_mark_and_defer_together_is_rejected(client, seed):
    seed(BASE)
    r = adjust(client, 4, new_due="2026-11-20", expected_version=1, mark="worse", defer_mark=True)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(("new_due", "reason", "ok"), [
    ("2026-11-20", "underestimated", True), ("2026-11-20", "finished_early", False),
    ("2026-11-16", "finished_early", True), ("2026-11-16", "wait_external", False),
    ("2026-11-20", "not_a_reason", False), ("2026-11-20", "other", True), ("2026-11-16", "other", True)])
def test_reason_must_match_direction(client, seed, new_due, reason, ok):
    seed(BASE)
    r = adjust(client, 4, new_due=new_due, expected_version=1, reason=reason, mark="none")
    assert (r.status_code == 200) is ok
    if not ok:
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_stale_version(client, seed):
    seed(BASE)
    r = adjust(client, 3, new_due="2026-11-20", expected_version=3)
    assert r.status_code == 409 and r.json()["error"]["code"] == "STALE_VERSION"


# ---------- AC-08～10：補註記 ----------

def _due_event(client, task_id=4, **kw):
    body = {"new_due": "2026-11-20", "expected_version": 1, "defer_mark": True} | kw
    return client.post(ADJ.format(task_id), json=body).json()["event"]


def test_ac08_annotation(client, seed, query):
    seed(BASE)
    ev = _due_event(client)
    before = query("SELECT * FROM events WHERE id = :i", i=ev["id"])
    r = client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse"})
    assert r.status_code == 201
    ann = r.json()["event"]
    assert ann["kind"] == "annotation" and ann["ref_event_id"] == ev["id"] and r.json()["effective_mark"] == "worse"
    assert query("SELECT * FROM events WHERE id = :i", i=ev["id"]) == before
    stats = client.get("/api/v1/stats/time-management").json()
    assert (stats["worse"]["count"], stats["unmarked"]) == (1, 0)


def test_ac09_reannotation_keeps_both(client, seed, query):
    seed(BASE)
    ev = _due_event(client)
    client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse"})
    r = client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "none"}).json()
    assert r["effective_mark"] == "none" and r["event"]["from_value"] == "worse"
    assert len(query("SELECT id FROM events WHERE kind = 'annotation' AND ref_event_id = :i", i=ev["id"])) == 2


def test_ac10_annotation_not_allowed_on_others_event(client, seed):
    seed(BASE)
    ev = _due_event(client, task_id=2, defer_mark=False)
    r = client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "ANNOTATION_NOT_ALLOWED"


def test_annotation_not_allowed_on_non_due_event(client, seed):
    seed(BASE)
    ev = client.post("/api/v1/tasks/4/block", json={"expected_version": 1}).json()["event"]
    r = client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse"})
    assert r.json()["error"]["code"] == "ANNOTATION_NOT_ALLOWED"


def test_annotation_requires_valid_mark_and_existing_event(client, seed):
    seed(BASE)
    assert client.post("/api/v1/events/999/annotations", json={"mark": "worse"}).status_code == 404
    ev = _due_event(client)
    assert client.post(f"/api/v1/events/{ev['id']}/annotations", json={}).status_code == 422
    assert client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "bad"}).status_code == 422


def test_annotation_reason_direction_follows_original_event(client, seed):
    seed(BASE)
    ev = _due_event(client)   # 延後
    r = client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse", "reason": "less_work"})
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_annotation_allowed_after_owner_changed(client, seed):
    seed(BASE)
    ev = _due_event(client)
    client.patch("/api/v1/tasks/4/owner", json={"owner": "阿德", "expected_version": 2})
    r = client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse"})
    assert r.status_code == 201 and r.json()["event"]["mine"] is True


# ---------- AC-12、12a：不預填、不代判 ----------

def test_ac12_external_reason_is_only_a_hint(client, seed):
    seed(BASE)
    reasons = client.get("/api/v1/meta/reasons").json()["due"]
    ext = {r["code"] for r in reasons if r["external"]}
    assert ext == {"wait_external", "scope_change_external", "resource_external"}
    assert all(r["direction"] == "later" for r in reasons if r["external"])
    r = adjust(client, 4, new_due="2026-11-20", expected_version=1, reason="wait_external")
    assert r.json()["error"]["code"] == "MARK_REQUIRED"   # 外部原因也不會自動補上 mark=none
    body = adjust(client, 4, new_due="2026-11-20", expected_version=1, reason="wait_external",
                  defer_mark=True).json()
    assert body["event"]["mark"] is None


def test_ac12a_api_does_not_prefill_reason_or_mark(client, seed):
    """FR-AI-06 防回歸（Dev 側）：沒給原因與註記時，事件的 reason、mark 都保持空白。"""
    seed(BASE)
    body = adjust(client, 4, new_due="2026-11-20", expected_version=1, defer_mark=True).json()
    assert body["event"]["reason"] is None and body["event"]["mark"] is None
    body = adjust(client, 2, new_due="2026-11-20", expected_version=1).json()
    assert body["event"]["reason"] is None and body["event"]["mark"] is None


def test_adjust_due_signature_supports_candidate_origin(db, seed):
    """DA-03：Dev-B 確認延期候選時帶入候選 id 與來源。"""
    seed(BASE + "INSERT INTO sources (id, channel, speaker, excerpt_hash, received_at, expires_at) "
                "VALUES (5, 'paste', '阿德', 'h', now(), now());")
    r = db.run(lambda c: adjust_due(c, 4, date(2026, 11, 20), 1, None, None, None, True,
                                    origin="candidate", origin_ref=12, source_id=5))
    assert (r.event["origin"], r.event["origin_ref"], r.event["source_id"]) == ("candidate", 12, 5)
    assert r.needs_mark is True


# ---------- AC-13：統計 ----------

def test_ac13_stats_counts_each_effective_mark(client, seed):
    seed(BASE + """
    INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, created_at,
                       updated_at) VALUES
      (11, 1, 'a', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', now(), now()),
      (12, 1, 'b', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', now(), now()),
      (13, 1, 'c', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', now(), now()),
      (14, 1, 'd', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', now(), now());
    """)
    adjust(client, 11, new_due="2026-11-18", expected_version=1, mark="better")
    adjust(client, 12, new_due="2026-11-23", expected_version=1, mark="worse")
    adjust(client, 13, new_due="2026-11-22", expected_version=1, mark="none")
    adjust(client, 14, new_due="2026-11-21", expected_version=1, defer_mark=True)
    adjust(client, 2, new_due="2026-11-25", expected_version=1)        # mine=0，不計入
    s = client.get("/api/v1/stats/time-management").json()
    assert s["better"] == {"count": 1, "days": 2}
    assert s["worse"] == {"count": 1, "days": 3}
    assert (s["none"], s["unmarked"], s["judgement"], s["min_sample"]) == (1, 1, None, 5)
    assert s["worse_by_energy"] == {"high": 0, "mid": 0, "low": 0, "not_done": 1}


def test_stats_use_effective_mark_and_energy(client, seed):
    seed(BASE + """
    INSERT INTO rubrics (id, version, levels, source, created_at)
      VALUES (1, 0, '["1","2","3","4","5"]', 'default', now());
    INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status,
                       done_date, created_at, updated_at) VALUES
      (21, 1, 'e', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', 'todo', NULL, now(), now());
    """)
    ev = adjust(client, 21, new_due="2026-11-24", expected_version=1, mark="better").json()["event"]
    client.post(f"/api/v1/events/{ev['id']}/annotations", json={"mark": "worse"})
    client.post("/api/v1/tasks/21/complete", json={"expected_version": 2})
    seed("INSERT INTO completion_feedback (task_id, actual_stars, energy, overdue_days, rubric_id, created_at) "
         "VALUES (21, 3, 'high', 0, 1, now());")
    s = client.get("/api/v1/stats/time-management").json()
    assert s["better"]["count"] == 0 and s["worse"] == {"count": 1, "days": 4}
    assert s["worse_by_energy"]["high"] == 1


def test_stats_date_filter(client, seed, clock):
    from datetime import timedelta
    seed(BASE)
    adjust(client, 4, new_due="2026-11-20", expected_version=1, mark="worse")
    clock.set(clock.now() + timedelta(days=3))
    adjust(client, 5, new_due="2026-11-22", expected_version=2, mark="worse")
    assert client.get("/api/v1/stats/time-management?from=2026-11-12").json()["worse"]["count"] == 1
    assert client.get("/api/v1/stats/time-management?to=2026-11-11").json()["worse"]["count"] == 1


# ---------- 3.9 並行 ----------

def test_concurrent_adjust_second_gets_stale_version(db, seed):
    seed(BASE)
    results: dict[str, object] = {}
    locked = threading.Event()

    def first():
        def fn(c):
            adjust_due(c, 2, date(2026, 11, 16), 1, None, None, None, False, origin="manual")
            locked.set()
            time.sleep(0.3)   # 持有列鎖一段時間
        db.run(fn)
        results["first"] = "ok"

    def second():
        locked.wait(2)
        try:
            db.run(lambda c: adjust_due(c, 2, date(2026, 11, 17), 1, None, None, None, False, origin="manual"))
            results["second"] = "ok"
        except DomainError as e:
            results["second"] = e.code

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == {"first": "ok", "second": "STALE_VERSION"}
