"""AC-39：確認延期候選時，我的任務回 needs_mark=true，別人的任務為 false（FR-INB-10～12、spec 6.1）。"""

import pytest

from tests.acceptance.helpers import API, MARK, SEED_BASE, SEED_CANDIDATES, count


@pytest.fixture
def data(seed):
    seed(SEED_BASE + SEED_CANDIDATES)


def _confirm(client, cid, **body):
    return client.post(f"{API}/candidates/{cid}/confirm", json={"expected_version": 1, **body})


def test_ac39_my_task_needs_mark(client, data, query):
    r = _confirm(client, 2)
    assert r.status_code == 200, r.text
    assert r.json()["needs_mark"] is True
    ev = query("SELECT mine, mark, delta_days FROM events WHERE id = :i", i=r.json()["event"]["id"])[0]
    assert ev == {"mine": True, "mark": None, "delta_days": 5}
    assert query("SELECT latest_due::text AS l, version FROM tasks WHERE id = 2")[0] == {"l": "2026-11-19", "version": 2}


def test_ac39_others_task_does_not_need_mark(client, data, query):
    r = _confirm(client, 1)
    assert r.status_code == 200, r.text
    assert r.json()["needs_mark"] is False
    ev = query("SELECT mine, mark FROM events WHERE id = :i", i=r.json()["event"]["id"])[0]
    assert ev == {"mine": False, "mark": None}


def test_ac39_event_can_be_annotated_afterwards(client, data):
    ev_id = _confirm(client, 2).json()["event"]["id"]
    r = client.post(f"{API}/events/{ev_id}/annotations", json={"mark": "none"})
    assert r.status_code == 201, r.text
    s = client.get(f"{API}/stats/time-management").json()
    assert (s["none"], s["unmarked"]) == (1, 0)


def test_spec61_confirm_on_done_task_returns_task_done_and_keeps_open(client, data, query):
    r = _confirm(client, 7)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "TASK_DONE"
    assert query("SELECT state FROM candidates WHERE id = 7")[0]["state"] == "open"
    assert count(query, "events") == 0


def test_spec61_stale_version_keeps_everything(client, data, query):
    r = client.post(f"{API}/candidates/2/confirm", json={"expected_version": 99})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "STALE_VERSION"
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "open"
    assert query("SELECT latest_due::text AS l, version FROM tasks WHERE id = 2")[0] == {"l": "2026-11-14", "version": 1}
    assert count(query, "events") == 0


def test_spec52_decided_candidate_cannot_be_decided_again(client, data, query):
    assert _confirm(client, 2).status_code == 200
    again = client.post(f"{API}/candidates/2/confirm", json={"expected_version": 2})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "CANDIDATE_NOT_OPEN"
    ignore = client.post(f"{API}/candidates/2/ignore")
    assert ignore.status_code == 409
    assert ignore.json()["error"]["code"] == "CANDIDATE_NOT_OPEN"
    assert count(query, "events") == 1


def test_spec511_date_out_of_range_is_rejected(client, data, query):
    r = _confirm(client, 2, new_due="2030-01-01")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "DATE_OUT_OF_RANGE"
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "open"
    assert count(query, "events") == 0


@pytest.mark.xfail(reason="待裁定 Q4：確認時新日期等於目前值", strict=False)
def test_ac39_new_due_equal_to_current_is_no_change(client, data, query):
    r = _confirm(client, 2, new_due="2026-11-14")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NO_CHANGE"
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "open"
    assert count(query, "events") == 0


def test_fr_inb11_confirm_done_completes_task_and_requires_feedback(client, data, query):
    r = _confirm(client, 6)
    assert r.status_code == 200, r.text
    assert r.json()["feedback_required"] is True
    task = query("SELECT status, done_date::text AS d FROM tasks WHERE id = 3")[0]
    assert task == {"status": "done", "d": "2026-11-11"}
    assert count(query, "completion_feedback") == 0  # 星數與精力等使用者自己填（FR-AI-06）


def test_fr_inb12_confirm_stuck_blocks_task(client, data, query):
    r = _confirm(client, 3)
    assert r.status_code == 200, r.text
    assert query("SELECT blocked FROM tasks WHERE id = 3")[0]["blocked"] is True
    assert query("SELECT kind, source_id FROM events") == [{"kind": "status", "source_id": 3}]


def test_fr_inb15_ignore_keeps_record_and_changes_nothing(client, data, query):
    r = client.post(f"{API}/candidates/2/ignore")
    assert r.status_code == 200, r.text
    assert r.json()["candidate"]["state"] == "ignored"
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "ignored"
    assert query("SELECT latest_due::text AS l FROM tasks WHERE id = 2")[0]["l"] == "2026-11-14"
    assert count(query, "events") == 0


def test_spec52_unknown_candidate_is_not_found(client, data):
    r = _confirm(client, 999)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_spec511_list_candidates_by_state(client, data):
    assert client.post(f"{API}/candidates/3/ignore").status_code == 200
    r = client.get(f"{API}/candidates", params={"state": "open"})
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 7
    assert 3 not in [c["id"] for c in r.json()["items"]]


# ---- 審查發現補測（PR #20）----

# 候選 9：完成候選，但對應的任務 7 早已完成。
SEED_DONE_ON_DONE_TASK = f"""
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
 (9, 'paste', '我', '10:50', '需求訪談完成了 {MARK}', 'seed-h9', '2026-11-11T09:00+08:00', '2026-12-11T09:00+08:00');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, suggest, state, created_at) VALUES
 (9, 9, 'done', 'sure', 7, NULL, NULL, 'open', '2026-11-11T09:00+08:00');
"""

# 候選由 AI-01 產生：補上 ai_runs 與 candidates.ai_run_id，貼近實際資料。
SEED_AI_RUN = """
INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at) VALUES
 (1, 'AI-01', 'ok', 1, '{"items": []}', '2026-11-11T09:00+08:00');
UPDATE candidates SET ai_run_id = 1;
"""


def _task(query, task_id):
    return query("SELECT * FROM tasks WHERE id = :i", i=task_id)[0]


def test_fr_inb13_clarify_delay_on_my_task_needs_mark_and_notes_basis(client, data, query):
    """審查 1-1（AC-12a、AC-39、FR-INB-13、FR-AI-06）：待釐清的延期候選採用建議。"""
    r = client.post(f"{API}/candidates/4/clarify", json={"expected_version": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["needs_mark"] is True
    task = query("SELECT orig_due::text AS o, latest_due::text AS l FROM tasks WHERE id = 2")[0]
    assert task == {"o": "2026-11-14", "l": "2026-11-21"}
    ev = query("SELECT reason, mark, mine, CAST(row_to_json(e) AS text) AS j FROM events e WHERE id = :i",
               i=body["event"]["id"])[0]
    assert (ev["reason"], ev["mark"], ev["mine"]) == (None, None, True)
    assert MARK not in ev["j"]  # 原句不存在事件本身（FR-HIS-05）
    # 依據註記：spec 沒指定放哪個欄位，事件列或歷程回應任一處出現即可
    item = next(i for i in client.get(f"{API}/events").json()["items"] if i["id"] == body["event"]["id"])
    assert "待釐清，你確認" in ev["j"] or "待釐清，你確認" in str(item)


def test_fr_inb11_confirm_done_writes_status_event_from_candidate(client, data, query):
    """審查 1-5(a)。"""
    r = _confirm(client, 6)
    assert r.status_code == 200, r.text
    assert r.json()["feedback_required"] is True
    task = query("SELECT status, done_date FROM tasks WHERE id = 3")[0]
    assert task["status"] == "done" and task["done_date"] is not None
    ev = query("SELECT origin, origin_ref, task_id FROM events WHERE kind = 'status'")
    assert ev == [{"origin": "candidate", "origin_ref": 6, "task_id": 3}]
    assert query("SELECT state FROM candidates WHERE id = 6")[0]["state"] == "confirmed"


def test_spec61_confirm_done_candidate_on_done_task_is_task_done(client, seed, query):
    """審查 1-5(c)：完成候選的任務已完成，回 TASK_DONE，候選維持 open。"""
    seed(SEED_BASE + SEED_CANDIDATES + SEED_DONE_ON_DONE_TASK)
    before = _task(query, 7)
    r = _confirm(client, 9)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "TASK_DONE"
    assert query("SELECT state FROM candidates WHERE id = 9")[0]["state"] == "open"
    assert _task(query, 7) == before
    assert count(query, "events") == 0


def test_fr_inb15_ignore_records_decision_and_ai_feedback(client, data, seed, query):
    """審查 1-6(a)：忽略保留紀錄並寫一筆評估資料（FR-INB-15、FR-AI-04）。"""
    seed(SEED_AI_RUN)
    tasks_before = query("SELECT * FROM tasks ORDER BY id")
    r = client.post(f"{API}/candidates/2/ignore")
    assert r.status_code == 200, r.text
    cand = query("SELECT state, decided_at FROM candidates WHERE id = 2")[0]
    assert cand["state"] == "ignored" and cand["decided_at"] is not None
    assert count(query, "events") == 0
    assert query("SELECT * FROM tasks ORDER BY id") == tasks_before
    fb = query("SELECT node_id, target_type, target_id, outcome FROM ai_feedback")
    assert fb == [{"node_id": "AI-01", "target_type": "candidate", "target_id": 2, "outcome": "ignored"}]


@pytest.mark.parametrize("extra,outcome", [
    ({}, "accepted"),                          # 沒改日期
    ({"new_due": "2026-11-19"}, "accepted"),   # 送回與建議相同的日期
    ({"new_due": "2026-11-20"}, "edited"),     # 改了日期
])
def test_fr_ai04_confirm_delay_records_accepted_or_edited(client, data, seed, query, extra, outcome):
    """審查 1-6(b)：確認延期候選寫 ai_feedback，detail 不含原句。"""
    seed(SEED_AI_RUN)
    assert _confirm(client, 2, **extra).status_code == 200
    fb = query("SELECT node_id, target_type, target_id, outcome, CAST(detail AS text) AS d FROM ai_feedback")
    assert len(fb) == 1
    assert (fb[0]["node_id"], fb[0]["target_type"], fb[0]["target_id"], fb[0]["outcome"]) == (
        "AI-01", "candidate", 2, outcome)
    assert MARK not in (fb[0]["d"] or "") and "API 介面定義要延到" not in (fb[0]["d"] or "")


@pytest.mark.parametrize("new_due", ["2025-11-10", "2028-11-11"])  # 今天前 366 天、今天後 731 天
def test_spec511_date_out_of_range_both_bounds_change_nothing(client, data, query, new_due):
    """審查 1-7：超出「今天前 365 天～後 730 天」。"""
    before = _task(query, 2)
    r = _confirm(client, 2, new_due=new_due)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "DATE_OUT_OF_RANGE"
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "open"
    assert _task(query, 2) == before
    assert count(query, "events") == 0


def test_spec511_date_on_upper_bound_is_accepted(client, data):
    assert _confirm(client, 2, new_due="2028-11-10").status_code == 200  # 剛好今天後 730 天


def test_spec68_same_confirm_request_sent_twice_writes_one_event(client, data, query):
    """審查 2-11(a)：兩個內容相同的確認請求先後送達（都帶舊的版本號）。"""
    first, second = _confirm(client, 2), _confirm(client, 2)
    assert first.status_code == 200, first.text
    assert second.status_code == 409
    assert second.json()["error"]["code"] in ("CANDIDATE_NOT_OPEN", "STALE_VERSION")
    assert count(query, "events") == 1
    assert query("SELECT latest_due::text AS l, version FROM tasks WHERE id = 2")[0] == {"l": "2026-11-19", "version": 2}


@pytest.mark.parametrize("endpoint,body", [
    ("clarify", {"expected_version": 1}),
    ("create-task", {"title": "報表處理", "due": "2026-12-20"}),
])
def test_spec511_delay_candidate_on_wrong_endpoint_stays_open(client, data, query, endpoint, body):
    """審查 2-13(a)：用錯端點回 VALIDATION_ERROR，候選維持 open。"""
    tasks_before = query("SELECT * FROM tasks ORDER BY id")
    r = client.post(f"{API}/candidates/2/{endpoint}", json=body)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert query("SELECT state FROM candidates WHERE id = 2")[0]["state"] == "open"
    assert query("SELECT * FROM tasks ORDER BY id") == tasks_before
    assert count(query, "events") == 0
