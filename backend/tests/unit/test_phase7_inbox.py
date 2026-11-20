"""Phase 7：收件、候選確認、背景工作（AC-12a、34～41，todo 7.1～7.11）。AI 一律 FakeAIClient。"""

import pytest

from app import worker
from app.ai.client import DEFAULT_TIMEOUT_S, AIInvalidOutput, AITimeout
from tests.unit.seeds import BASE

API = "/api/v1"
NODE = "AI-01"
PRIVATE_TASK = """
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, version, created_at, updated_at) VALUES
  (8, NULL, '看牙醫', '我', 'private', '2026-11-11', '2026-11-20', '2026-11-20', 'todo', 1,
      '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00');
"""
# 已在收件匣的 open 候選（確認類測試直接用 SQL 種子，不經收件流程）
CANDIDATES = """
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at) VALUES
  (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/18', 'h1', '2026-11-11T10:12+08:00', '2026-12-11T10:12+08:00'),
  (2, 'paste', '小薇', '10:20', '報表處理我來', 'h2', '2026-11-11T10:20+08:00', '2026-12-11T10:20+08:00');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, suggest, state, created_at) VALUES
  (21, 1, 'delay', 'sure', 2, '{"new_due":"2026-11-18"}', NULL, 'open', '2026-11-11T10:12+08:00'),
  (22, 1, 'delay', 'sure', 4, '{"new_due":"2026-11-25"}', NULL, 'open', '2026-11-11T10:12+08:00'),
  (23, 1, 'done', 'sure', 3, NULL, NULL, 'open', '2026-11-11T10:12+08:00'),
  (24, 1, 'stuck', 'sure', 5, NULL, NULL, 'open', '2026-11-11T10:12+08:00'),
  (25, 1, 'unclear', 'to_clarify', 2, NULL, '{"kind":"delay","new_due":"2026-11-20"}', 'open',
       '2026-11-11T10:12+08:00'),
  (26, 2, 'unmatched', 'to_match', NULL, NULL, '{"kind":"done"}', 'open', '2026-11-11T10:20+08:00'),
  (27, 1, 'done', 'sure', 1, NULL, NULL, 'open', '2026-11-11T10:12+08:00');
"""


def ingest(client, text, project_id=None):
    return client.post(f"{API}/ingest", json={"text": text, "project_id": project_id})


def count(query, table):
    return query(f"SELECT count(*) AS n FROM {table}")[0]["n"]  # noqa: S608 測試固定表名


# ---------- 收件（7.1、7.3、7.4） ----------

def test_sync_ingest_creates_open_candidates_and_saves_raw_output(client, seed, ai, query):
    seed(BASE + PRIVATE_TASK)
    ai.script(NODE, {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"},
                               {"ref": 2, "kind": "none"}]})
    r = ingest(client, "[10:12] 阿德：畫面規格 v1 確定延到 11/18\n[10:15] 小薇：午餐吃什麼\n不明的一行")
    assert r.status_code == 200
    body = r.json()
    assert (body["mode"], body["ai_status"]) == ("sync", "ok")
    assert body["result"] == {"created": 1, "skipped": 1, "duplicates": 0, "unparsed_lines": []}
    [c] = body["candidates"]
    assert (c["kind"], c["state"], c["proposed"], c["quote"], c["speaker"], c["spoken_at"]) == (
        "delay", "open", {"new_due": "2026-11-18"}, "畫面規格 v1 確定延到 11/18", "阿德", "10:12")
    assert c["task"]["id"] == 2 and c["task"]["version"] == 1
    # 第三行接到第二則訊息，只存必要摘錄
    assert query("SELECT excerpt FROM sources ORDER BY id")[1]["excerpt"] == "午餐吃什麼\n不明的一行"
    [run] = query("SELECT status, attempt, raw_output FROM ai_runs")
    assert run["status"] == "ok" and '"new_due": "11/18"' in run["raw_output"]
    # 送 AI 的任務清單：不含已完成（1）與私人範圍（8）
    sent = ai.calls[0][1]
    assert {t["id"] for t in sent["tasks"]} == {2, 3, 4, 5, 6, 7}
    assert sent["messages"][0] == {"ref": 1, "speaker": "阿德", "spoken_at": "10:12",
                                   "text": "畫面規格 v1 確定延到 11/18"}


def test_ingest_project_scopes_task_list_and_reports_unparsed_lines(client, seed, ai):
    seed(BASE)
    ai.script(NODE, {"items": []})
    r = ingest(client, "開頭沒有發言者\n[10:12] 阿德：好", project_id=2)
    assert r.json()["result"] == {"created": 0, "skipped": 2, "duplicates": 0, "unparsed_lines": [1]}
    assert [t["id"] for t in ai.calls[0][1]["tasks"]] == [7]


PRIVATE_PROJECT = """
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (3, '家裡的事', 'private', 'none', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00');
"""


def test_private_project_ingest_does_not_call_ai(client, seed, ai, query):
    """PR #20 B1：私人專案的原文不送 AI（資安規則 2），原文照存，可手動建任務。"""
    seed(BASE + PRIVATE_PROJECT)
    ai.script(NODE, {"items": []})
    r = ingest(client, "[10:12] 阿德：好", project_id=3)
    assert r.status_code == 200 and r.json()["ai_status"] == "unavailable"
    assert r.json()["result"]["skipped"] == 1
    assert ai.calls == []
    assert count(query, "sources") == 1 and count(query, "ai_runs") == 0


def test_private_project_async_job_does_not_call_ai(client, seed, ai, db, query):
    seed(BASE + PRIVATE_PROJECT)
    job_id = ingest(client, long_text(), project_id=3).json()["job_id"]
    ai.script(NODE, {"items": []})
    worker.run_once(db, ai)
    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert (job["status"], job["result"]["ai_status"]) == ("failed", "unavailable")
    assert ai.calls == [] and count(query, "ai_runs") == 0 and count(query, "sources") == 31


def test_private_project_async_job_error_says_private_not_ai_failure(client, seed, ai, db):
    """審查：私人專案是刻意不送 AI，工作訊息不能說成 AI 解析失敗。"""
    seed(BASE + PRIVATE_PROJECT)
    job_id = ingest(client, long_text(), project_id=3).json()["job_id"]
    worker.run_once(db, ai)
    error = client.get(f"{API}/ingest/jobs/{job_id}").json()["error"]
    assert "私人" in error and "AI 解析失敗" not in error and "手動建立任務" in error


def test_ingest_retention_uses_settings_default_30_days(client, seed, ai, query):
    seed(BASE)
    ai.script(NODE, {"items": []})
    ingest(client, "[10:12] 阿德：好")
    [s] = query("SELECT received_at, expires_at FROM sources")
    assert (s["expires_at"] - s["received_at"]).days == 30


def test_ac38_same_text_twice_counts_duplicates(client, seed, ai, query):
    seed(BASE)
    ai.script(NODE, {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18"}]})
    text = "[10:12] 阿德：畫面規格 v1 確定延到 11/18"
    ingest(client, text)
    r = ingest(client, text)
    assert r.json()["result"]["duplicates"] == 1 and r.json()["result"]["created"] == 0
    assert count(query, "candidates") == 1 and count(query, "sources") == 1
    assert len(ai.calls) == 1   # 全是重複就不送 AI


def test_ingest_too_large_is_413(client, seed):
    seed(BASE)
    r = ingest(client, "阿" * 20_001)
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_ingest_unknown_project_is_404(client, seed):
    seed(BASE)
    assert ingest(client, "[10:12] 阿德：好", project_id=99).status_code == 404


def test_ac40_sync_invalid_output_retries_twice_then_keeps_sources_only(client, seed, ai, query):
    seed(BASE)
    ai.script(NODE, {"bad": 1}, AIInvalidOutput, AITimeout)
    r = ingest(client, "[10:12] 阿德：畫面規格 v1 確定延到 11/18")
    assert r.status_code == 200 and r.json()["ai_status"] == "unavailable"
    assert [x["status"] for x in query("SELECT status FROM ai_runs ORDER BY id")] == [
        "invalid_output", "invalid_output", "timeout"]
    assert count(query, "sources") == 1
    assert count(query, "candidates") == 0 and count(query, "events") == 0


def test_ai_unavailable_does_not_retry(client, seed, ai, query):
    seed(BASE)   # 沒有排任何輸出 → FakeAIClient 視為不可用
    r = ingest(client, "[10:12] 阿德：好")
    assert r.json()["ai_status"] == "unavailable" and r.json()["result"]["skipped"] == 1
    assert [x["status"] for x in query("SELECT status FROM ai_runs")] == ["error"]


def test_ac34_ingest_does_not_change_gantt(client, seed, ai):
    seed(BASE)
    before = client.get(f"{API}/projects/1/gantt").json()
    ai.script(NODE, {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/30"}]})
    ingest(client, "[10:12] 阿德：畫面規格延到 11/30")
    after = client.get(f"{API}/projects/1/gantt").json()
    assert after["rows"] == before["rows"] and after["summary"]["delayed"] == before["summary"]["delayed"]
    assert after["summary"]["open_candidates"] == before["summary"]["open_candidates"] + 1


# ---------- 背景工作（7.5，AC-40、41） ----------

def long_text(n=31):
    return "\n".join(f"[10:{i:02d}] 阿德：訊息 {i}" for i in range(n))


def test_ac41_over_30_lines_goes_async_and_worker_completes(client, seed, ai, db):
    seed(BASE)
    r = ingest(client, long_text())
    assert r.json()["mode"] == "async" and r.json()["status"] == "queued"
    job_id = r.json()["job_id"]
    assert client.get(f"{API}/ingest/jobs/{job_id}").json()["status"] == "queued"
    ai.script(NODE, {"items": [{"ref": 1, "kind": "done", "task_id": 3}]})
    assert worker.run_once(db, ai) == job_id
    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert (job["status"], job["attempts"], job["error"]) == ("succeeded", 1, None)
    assert job["result"]["created"] == 1 and job["result"]["skipped"] == 30
    assert worker.run_once(db, ai) is None


def test_ac40_job_fails_after_three_attempts_and_keeps_excerpts(client, seed, ai, db, query):
    seed(BASE)
    job_id = ingest(client, long_text()).json()["job_id"]
    ai.script(NODE, AIInvalidOutput, AIInvalidOutput, AIInvalidOutput)
    worker.run_once(db, ai)
    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert (job["status"], job["attempts"]) == ("failed", 3)
    assert "手動建立任務" in job["error"]
    assert count(query, "sources") == 31 and count(query, "candidates") == 0 and count(query, "events") == 0
    assert {r["job_id"] for r in query("SELECT job_id FROM ai_runs")} == {job_id}


def test_restart_resets_running_and_keeps_attempts(seed, ai, db, query):
    seed(BASE + """
    INSERT INTO sources (id, channel, speaker, excerpt, excerpt_hash, received_at, expires_at) VALUES
      (1, 'paste', '阿德', '好', 'h1', '2026-11-11T10:00+08:00', '2026-12-11T10:00+08:00');
    INSERT INTO jobs (id, kind, status, attempts, payload, created_at, updated_at) VALUES
      (5, 'ingest', 'running', 2,
       '{"source_ids":[1],"project_id":null,"duplicates":0,"unparsed_lines":[]}',
       '2026-11-11T10:00+08:00', '2026-11-11T10:00+08:00');
    """)
    assert worker.reset_running(db) == 1
    assert query("SELECT status, attempts FROM jobs")[0] == {"status": "queued", "attempts": 2}
    ai.script(NODE, AITimeout, {"items": []})
    worker.run_once(db, ai)
    assert query("SELECT status, attempts FROM jobs")[0] == {"status": "failed", "attempts": 3}
    assert len(ai.calls) == 1   # 只剩一次機會


# ---------- 候選確認（7.6～7.9） ----------

def post(client, cid, action, **body):
    return client.post(f"{API}/candidates/{cid}/{action}", json=body)


def test_list_open_candidates(client, seed):
    seed(BASE + CANDIDATES)
    r = client.get(f"{API}/candidates")
    assert r.json()["total"] == 7
    unmatched = next(c for c in r.json()["items"] if c["id"] == 26)
    assert unmatched["task"] is None and unmatched["quote"] == "報表處理我來"


def test_ac39_ac12a_confirm_delay_not_mine(client, seed, query):
    seed(BASE + CANDIDATES)
    r = post(client, 21, "confirm", expected_version=1)
    assert r.status_code == 200
    body = r.json()
    assert body["needs_mark"] is False and "reason" not in body
    assert body["candidate"]["state"] == "confirmed"
    assert body["task"]["latest_due"] == "2026-11-18" and body["task"]["orig_due"] == "2026-11-13"
    ev = body["event"]
    assert (ev["origin"], ev["origin_ref"], ev["source_id"], ev["reason"], ev["mark"]) == (
        "candidate", 21, 1, None, None)
    [fb] = query("SELECT outcome, target_id FROM ai_feedback")
    assert fb == {"outcome": "accepted", "target_id": 21}
    assert query("SELECT decision, decided_at IS NOT NULL AS d FROM candidates WHERE id = 21")[0] == {
        "decision": "confirm", "d": True}


def test_ac39_confirm_delay_mine_needs_mark_and_edited_date(client, seed, query):
    seed(BASE + CANDIDATES)
    body = post(client, 22, "confirm", expected_version=1, new_due="2026-11-27").json()
    assert body["needs_mark"] is True and body["event"]["mark"] is None
    assert body["task"]["latest_due"] == "2026-11-27"
    assert query("SELECT outcome FROM ai_feedback")[0]["outcome"] == "edited"


def test_confirm_delay_before_start_returns_warning(client, seed):
    # spec 6.2：新日期早於開始日允許，回警告 BEFORE_START（PR #20 審查 A2）
    seed(BASE + CANDIDATES)
    body = post(client, 21, "confirm", expected_version=1, new_due="2026-11-08").json()
    assert body["task"]["latest_due"] == "2026-11-08" and body["warnings"] == ["BEFORE_START"]


def test_clarify_delay_before_start_returns_warning(client, seed):
    seed(BASE + CANDIDATES)
    body = post(client, 25, "clarify", expected_version=1, new_due="2026-11-08").json()
    assert body["warnings"] == ["BEFORE_START"]


def test_confirm_delay_without_warning_has_empty_list_and_others_omit_it(client, seed):
    seed(BASE + CANDIDATES)
    assert post(client, 21, "confirm", expected_version=1).json()["warnings"] == []
    assert "warnings" not in post(client, 24, "confirm", expected_version=2).json()


def test_confirm_done_requires_feedback(client, seed):
    seed(BASE + CANDIDATES)
    body = post(client, 23, "confirm", expected_version=4).json()
    assert body["feedback_required"] is True and body["task"]["status"] == "done"
    assert body["event"]["origin_ref"] == 23


def test_confirm_stuck_sets_blocked(client, seed):
    seed(BASE + CANDIDATES)
    body = post(client, 24, "confirm", expected_version=2).json()
    assert body["task"]["blocked"] is True and body["event"]["field"] == "blocked"


def test_confirm_task_done_keeps_candidate_open(client, seed, query):
    seed(BASE + CANDIDATES)
    r = post(client, 27, "confirm", expected_version=3)
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_DONE"
    assert query("SELECT state FROM candidates WHERE id = 27")[0]["state"] == "open"
    assert count(query, "ai_feedback") == 0


def test_confirm_stale_version(client, seed):
    seed(BASE + CANDIDATES)
    r = post(client, 21, "confirm", expected_version=9)
    assert r.status_code == 409 and r.json()["error"]["code"] == "STALE_VERSION"


def test_candidate_not_open_after_ignore(client, seed, query):
    seed(BASE + CANDIDATES)
    assert post(client, 21, "ignore").json()["candidate"]["state"] == "ignored"
    assert query("SELECT outcome FROM ai_feedback")[0]["outcome"] == "ignored"
    r = post(client, 21, "confirm", expected_version=1)
    assert r.status_code == 409 and r.json()["error"]["code"] == "CANDIDATE_NOT_OPEN"


def test_wrong_endpoint_is_validation_error(client, seed):
    seed(BASE + CANDIDATES)
    r1 = post(client, 25, "confirm", expected_version=1)
    r2 = post(client, 21, "clarify", expected_version=1)
    r3 = post(client, 21, "create-task", title="x", due="2026-11-30")
    assert [r.status_code for r in (r1, r2, r3)] == [422, 422, 422]
    assert r1.json()["error"]["details"]["use"] == "clarify"


def test_clarify_uses_suggestion_and_history_label(client, seed):
    seed(BASE + CANDIDATES)
    body = post(client, 25, "clarify", expected_version=1).json()
    assert body["task"]["latest_due"] == "2026-11-20" and body["needs_mark"] is False
    item = client.get(f"{API}/events", params={"task_id": 2}).json()["items"][0]
    assert item["source"]["label"] == "候選 #25（待釐清，你確認）"


def test_create_task_from_unmatched_defaults_owner_to_speaker(client, seed, query):
    seed(BASE + CANDIDATES)
    r = post(client, 26, "create-task", title="報表處理", due="2026-12-20", project_id=1)
    assert r.status_code == 201
    body = r.json()
    assert (body["task"]["title"], body["task"]["owner"], body["task"]["latest_due"]) == (
        "報表處理", "小薇", "2026-12-20")
    assert body["candidate"]["state"] == "confirmed"
    [fb] = query("SELECT outcome, detail FROM ai_feedback")
    assert fb == {"outcome": "changed", "detail": {"task_id": body["task"]["id"]}}
    [ev] = query("SELECT origin, origin_ref, source_id FROM events WHERE task_id = :t AND field = 'created'",
                 t=body["task"]["id"])
    src = query("SELECT source_id FROM candidates WHERE id = 26")[0]["source_id"]
    assert ev == {"origin": "candidate", "origin_ref": 26, "source_id": src}   # FR-INB-14、FR-HIS-04（R-01）


def test_unknown_candidate_is_404(client, seed):
    seed(BASE)
    assert post(client, 999, "ignore").status_code == 404


# ---------- 審查修正的回歸測試 ----------

def crash_before_final_status(monkeypatch):
    """模擬行程在「候選已存」之後、「工作結案」之前崩潰（#107）：寫最終狀態那一次丟例外。"""
    original = worker.jobs_repo.update

    def update(conn, job_id, fields):
        if fields.get("status") in ("succeeded", "failed"):
            raise RuntimeError("crash")
        return original(conn, job_id, fields)

    monkeypatch.setattr(worker.jobs_repo, "update", update)


def test_107_rerun_after_crash_does_not_duplicate_candidates_or_call_ai(client, seed, ai, db, query, monkeypatch):
    seed(BASE)
    job_id = ingest(client, long_text()).json()["job_id"]
    ai.script(NODE, {"items": [{"ref": 1, "kind": "done", "task_id": 3}]})
    crash_before_final_status(monkeypatch)
    with pytest.raises(RuntimeError):
        worker.run_once(db, ai)
    monkeypatch.undo()
    first_ids = [r["id"] for r in query("SELECT id FROM candidates ORDER BY id")]
    assert query("SELECT status FROM jobs WHERE id = :i", i=job_id)[0]["status"] == "running"

    worker.reset_running(db)
    ai.script(NODE, {"items": [{"ref": 1, "kind": "done", "task_id": 3}]})
    worker.run_once(db, ai)

    assert [r["id"] for r in query("SELECT id FROM candidates ORDER BY id")] == first_ids
    assert count(query, "ai_runs") == 1   # AI-01 只呼叫一次
    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert (job["status"], job["attempts"], job["error"]) == ("succeeded", 1, None)
    assert job["result"]["candidate_ids"] == first_ids
    assert job["result"]["created"] == 1 and job["result"]["skipped"] == 30


def test_107_rerun_after_crash_on_third_attempt_success_is_not_failed(client, seed, ai, db, query, monkeypatch):
    seed(BASE)
    job_id = ingest(client, long_text()).json()["job_id"]
    ai.script(NODE, AIInvalidOutput, AIInvalidOutput, {"items": [{"ref": 1, "kind": "done", "task_id": 3}]})
    crash_before_final_status(monkeypatch)
    with pytest.raises(RuntimeError):
        worker.run_once(db, ai)
    monkeypatch.undo()

    worker.reset_running(db)
    worker.run_once(db, ai)

    job = client.get(f"{API}/ingest/jobs/{job_id}").json()
    assert (job["status"], job["attempts"], job["error"]) == ("succeeded", 3, None)
    assert count(query, "candidates") == 1 and count(query, "ai_runs") == 3


def test_107_rerun_with_only_failed_runs_still_calls_ai(seed, ai, db, query):
    seed(BASE + """
    INSERT INTO sources (id, channel, speaker, excerpt, excerpt_hash, received_at, expires_at) VALUES
      (1, 'paste', '阿德', '報表做完了', 'h1', '2026-11-11T10:00+08:00', '2026-12-11T10:00+08:00');
    INSERT INTO jobs (id, kind, status, attempts, payload, created_at, updated_at) VALUES
      (5, 'ingest', 'running', 1,
       '{"source_ids":[1],"project_id":null,"duplicates":0,"unparsed_lines":[]}',
       '2026-11-11T10:00+08:00', '2026-11-11T10:00+08:00');
    INSERT INTO ai_runs (node_id, job_id, status, attempt, error, created_at) VALUES
      ('AI-01', 5, 'invalid_output', 1, 'AIInvalidOutput', '2026-11-11T10:00+08:00');
    """)
    worker.reset_running(db)
    ai.script(NODE, {"items": [{"ref": 1, "kind": "done", "task_id": 3}]})
    worker.run_once(db, ai)
    assert query("SELECT status, attempts FROM jobs")[0] == {"status": "succeeded", "attempts": 2}
    assert count(query, "candidates") == 1
    assert [r["status"] for r in query("SELECT status FROM ai_runs ORDER BY id")] == ["invalid_output", "ok"]


def test_non_ai_error_from_provider_counts_as_failed_attempt(client, seed, ai, query):
    seed(BASE)
    ai.script(NODE, RuntimeError, ValueError, {"items": []})
    r = ingest(client, "[10:12] 阿德：好")
    assert r.status_code == 200 and r.json()["ai_status"] == "ok"
    assert [x["status"] for x in query("SELECT status FROM ai_runs ORDER BY id")] == ["error", "error", "ok"]


def test_job_calls_ai01_with_longer_timeout_and_sync_keeps_default(client, seed, ai, db, monkeypatch):
    # 13-4-sdd 4.3：150 則實測 25.8 秒，背景工作放寬到 60 秒；同步路徑（≤30 行）維持 20 秒
    seed(BASE)
    timeouts = []
    real_call = ai.call

    def spy(node_id, payload, *, timeout_s=DEFAULT_TIMEOUT_S):
        timeouts.append(timeout_s)
        return real_call(node_id, payload, timeout_s=timeout_s)

    monkeypatch.setattr(ai, "call", spy)
    ai.script(NODE, {"items": []}, {"items": []})
    ingest(client, "[10:12] 阿德：好")
    ingest(client, long_text())
    worker.run_once(db, ai)
    assert timeouts == [DEFAULT_TIMEOUT_S, worker.JOB_TIMEOUT_S]
    assert worker.JOB_TIMEOUT_S == 60


def test_worker_marks_job_failed_on_unexpected_exception(client, seed, ai, db, query, monkeypatch):
    seed(BASE)
    job_id = ingest(client, long_text()).json()["job_id"]

    def explode(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(worker, "process_sources", explode)
    with pytest.raises(RuntimeError):
        worker.run_once(db, ai)
    assert query("SELECT status FROM jobs WHERE id = :i", i=job_id)[0]["status"] == "failed"


def test_purged_excerpt_before_job_runs_is_skipped(client, seed, ai, db, query):
    seed(BASE)
    job_id = ingest(client, long_text()).json()["job_id"]
    db.run(lambda c: c.exec_driver_sql("UPDATE sources SET excerpt = NULL, purged_at = now() WHERE id = 1"))
    ai.script(NODE, {"items": []})
    worker.run_once(db, ai)
    assert [m["ref"] for m in ai.calls[0][1]["messages"]] == list(range(2, 32))
    assert client.get(f"{API}/ingest/jobs/{job_id}").json()["result"]["skipped"] == 31


def test_clarify_without_usable_suggestion_is_rejected(client, seed, query):
    seed(BASE + CANDIDATES + """
    INSERT INTO candidates (id, source_id, kind, certainty, task_id, suggest, state, created_at) VALUES
      (28, 1, 'unclear', 'to_clarify', 3, '{}', 'open', '2026-11-11T10:12+08:00');
    """)
    r = post(client, 28, "clarify", expected_version=4)
    assert r.status_code == 422
    assert query("SELECT blocked FROM tasks WHERE id = 3")[0]["blocked"] is False


# ---------- B5：候選沿用收件時的專案（PR #20 審查 B5、FR-INB-14） ----------

def test_b5_sync_ingest_saves_project_on_candidate(client, seed, ai, query):
    seed(BASE)
    ai.script(NODE, {"items": [{"ref": 1, "kind": "done", "task_id": 7}]},
              {"items": [{"ref": 2, "kind": "done", "task_id": 3}]})   # ref 是 sources.id
    ingest(client, "[10:12] 阿德：做完了", project_id=2)
    ingest(client, "[10:13] 小薇：好了")
    assert [r["project_id"] for r in query("SELECT project_id FROM candidates ORDER BY id")] == [2, None]


def test_b5_async_job_saves_project_on_candidate(client, seed, ai, db, query):
    seed(BASE)
    ingest(client, long_text(), project_id=2)
    ai.script(NODE, {"items": [{"ref": 1, "kind": "done", "task_id": 7}]})
    worker.run_once(db, ai)
    assert [r["project_id"] for r in query("SELECT project_id FROM candidates")] == [2]


def test_b5_create_task_without_project_uses_candidate_project(client, seed, query):
    seed(BASE + CANDIDATES + "UPDATE candidates SET project_id = 2 WHERE id = 26;")
    body = post(client, 26, "create-task", title="報表處理", due="2026-12-20").json()
    assert query("SELECT project_id FROM tasks WHERE id = :t", t=body["task"]["id"])[0]["project_id"] == 2
    assert body["warnings"] == []


ARCHIVE_P2 = "UPDATE candidates SET project_id = 2 WHERE id = 26;" \
             "UPDATE projects SET archived_at = '2026-11-12T09:00+08:00' WHERE id = 2;"


def test_57_auto_project_archived_creates_without_project_and_warns(client, seed, query):
    seed(BASE + CANDIDATES + ARCHIVE_P2)
    r = post(client, 26, "create-task", title="報表處理", due="2026-12-20")
    assert r.status_code == 201
    body = r.json()
    assert query("SELECT project_id FROM tasks WHERE id = :t", t=body["task"]["id"])[0]["project_id"] is None
    assert body["warnings"] == ["PROJECT_ARCHIVED"]


def test_57_sent_archived_project_kept_without_warning(client, seed, query):
    seed(BASE + CANDIDATES + ARCHIVE_P2)
    body = post(client, 26, "create-task", title="報表處理", due="2026-12-20", project_id=2).json()
    assert query("SELECT project_id FROM tasks WHERE id = :t", t=body["task"]["id"])[0]["project_id"] == 2
    assert body["warnings"] == []


def test_57_candidate_without_project_no_warning(client, seed, query):
    seed(BASE + CANDIDATES)
    body = post(client, 26, "create-task", title="報表處理", due="2026-12-20").json()
    assert query("SELECT project_id FROM tasks WHERE id = :t", t=body["task"]["id"])[0]["project_id"] is None
    assert body["warnings"] == []


def test_b5_create_task_sent_project_overrides_candidate(client, seed, query):
    seed(BASE + CANDIDATES + "UPDATE candidates SET project_id = 2 WHERE id = 26;")
    body = post(client, 26, "create-task", title="報表處理", due="2026-12-20", project_id=1).json()
    assert query("SELECT project_id FROM tasks WHERE id = :t", t=body["task"]["id"])[0]["project_id"] == 1


def test_b5_create_task_sent_null_project_means_no_project(client, seed, query):
    seed(BASE + CANDIDATES + "UPDATE candidates SET project_id = 2 WHERE id = 26;")
    body = post(client, 26, "create-task", title="報表處理", due="2026-12-20", project_id=None).json()
    assert query("SELECT project_id FROM tasks WHERE id = :t", t=body["task"]["id"])[0]["project_id"] is None
