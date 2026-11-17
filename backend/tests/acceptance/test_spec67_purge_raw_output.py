"""spec 6.7（PR #20 B2）：清除原文時一併清除 ai_runs.raw_output；清除後原句不殘留在任何地方（資安 5）。

檔名暫用，待指定 AC 編號。
"""

from datetime import datetime

from app import scheduler, worker
from app.clock import TZ, FixedClock, set_clock
from tests.acceptance.helpers import API, MARK, SEED_BASE, ai_calls, count, created, ingest, lines, tables_containing

# 1、2、3 已超過保存天數（30 天）；4、5 尚未。1 是失敗的 AI-01（連不回來源），2 是 AI-06，3 是 AI-07。
SEED_RUNS = f"""
INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, error, created_at) VALUES
 (1, 'AI-01', 'invalid_output', 1, 'garbled {MARK}A', 'AIInvalidOutput', '2026-10-01T09:00+08:00'),
 (2, 'AI-06', 'ok', 1, '["{MARK}B","b","c","d","e"]', NULL, '2026-10-05T09:00+08:00'),
 (3, 'AI-07', 'ok', 1, '{{"title": 0, "end": 1, "echo": "{MARK}C"}}', NULL, '2026-10-10T09:00+08:00'),
 (4, 'AI-01', 'ok', 1, '{{"items": [], "echo": "{MARK}D"}}', NULL, '2026-11-10T09:00+08:00'),
 (5, 'AI-07', 'ok', 1, '{{"title": 0, "end": 1, "echo": "{MARK}E"}}', NULL, '2026-11-11T09:00+08:00');
"""

FLOW_TEXT = "\n".join([
    f"[10:12] 阿德：畫面規格 v1 確定延到 11/18 {MARK}",
    f"[10:15] 我：API 介面定義要延到 11/19 {MARK}",
    f"[10:20] 小薇：測試環境建置會不會卡住？ {MARK}",
    f"[10:30] 阿德：報表處理我來接 {MARK}",
    f"[10:35] 小薇：首頁文案卡住了 {MARK}",
])
FLOW_AI = {"items": [
    {"ref": 1, "kind": "delay", "task_id": 1, "new_due": "11/18", "certainty": "sure", "echo": f"{MARK} 畫面規格 v1 確定延到"},
    {"ref": 2, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"},
    {"ref": 3, "kind": "stuck", "task_id": 3, "certainty": "sure"},
    {"ref": 4, "kind": "delay", "task_id": None, "new_due": "12/20", "certainty": "sure"},
    {"ref": 5, "kind": "stuck", "task_id": 8, "certainty": "sure"},
]}


def _raw(query):
    return {r["id"]: r["raw_output"] for r in query("SELECT id, raw_output FROM ai_runs ORDER BY id")}


def test_spec67_purge_all_nulls_every_raw_output(client, seed, query):
    seed(SEED_BASE + SEED_RUNS)
    before = query("SELECT id, node_id, status, attempt, error, created_at FROM ai_runs ORDER BY id")
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    assert set(_raw(query).values()) == {None}
    assert query("SELECT id, node_id, status, attempt, error, created_at FROM ai_runs ORDER BY id") == before


def test_spec67_schedule_nulls_only_raw_output_past_retention(seed, db, query):
    seed(SEED_BASE + SEED_RUNS)
    scheduler.run_once(db)
    raw = _raw(query)
    assert raw[1] is None and raw[2] is None and raw[3] is None  # 不分節點，也不需要連得回來源
    assert MARK in raw[4] and MARK in raw[5]
    assert count(query, "ai_runs") == 5


def test_spec67_schedule_follows_retention_setting(seed, db, query):
    seed(SEED_BASE + SEED_RUNS + "UPDATE settings SET retention_days = 90;")
    scheduler.run_once(db)
    assert all(v is not None for v in _raw(query).values())


def test_spec67_export_after_purge_has_no_raw_output(client, seed):
    seed(SEED_BASE + SEED_RUNS)
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    r = client.post(f"{API}/export")
    assert r.status_code == 200, r.text
    assert all("raw_output" not in run for run in r.json()["tables"]["ai_runs"])   # #40：匯出整欄不帶（原為 null）
    assert MARK not in r.text


def _run_full_flow(client, seed, ai):
    """實際走一次：收件 → 確認（帶冪等鍵）→ 釐清 → 建任務 → 忽略。回傳含原句的回應數。"""
    seed(SEED_BASE)
    ai.script("AI-01", FLOW_AI)
    r = ingest(client, FLOW_TEXT, project_id=None)
    assert r.status_code == 200, r.text
    cands = {c["speaker"] + c["spoken_at"]: c for c in r.json()["candidates"]}
    assert len(cands) == 5, r.text
    key = {"Idempotency-Key": "qc-flow-1"}
    assert client.post(f"{API}/candidates/{cands['阿德10:12']['id']}/confirm", json={"expected_version": 1}, headers=key).status_code == 200
    assert client.post(f"{API}/candidates/{cands['我10:15']['id']}/confirm", json={"expected_version": 1, "new_due": "2026-11-21"},
                       headers={"Idempotency-Key": "qc-flow-2"}).status_code == 200
    assert client.post(f"{API}/candidates/{cands['小薇10:20']['id']}/clarify", json={"expected_version": 1},
                       headers={"Idempotency-Key": "qc-flow-3"}).status_code == 200
    created(client.post(f"{API}/candidates/{cands['阿德10:30']['id']}/create-task",
                        json={"title": "報表處理", "owner": "阿德", "due": "2026-12-20"}, headers={"Idempotency-Key": "qc-flow-4"}))
    assert client.post(f"{API}/candidates/{cands['小薇10:35']['id']}/ignore", headers={"Idempotency-Key": "qc-flow-5"}).status_code == 200


def _assert_no_residue(client, query):
    assert tables_containing(query, MARK) == {}
    for path in ("/events", "/candidates", "/tasks", "/tasks/1", "/tasks/2", "/projects/1/history", "/projects/1/gantt"):
        r = client.get(f"{API}{path}")
        assert r.status_code == 200, path
        assert MARK not in r.text, path
    export = client.post(f"{API}/export")
    assert export.status_code == 200
    assert MARK not in export.text


def test_spec67_full_flow_then_purge_all_leaves_no_trace(client, seed, ai, query):
    """審查 3-3：以原句字串掃所有表的所有欄位、API 回應與匯出全文。"""
    _run_full_flow(client, seed, ai)
    assert tables_containing(query, MARK)  # 清除前確實找得到，掃描本身有效
    events_before = query("SELECT * FROM events ORDER BY id")
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    _assert_no_residue(client, query)
    assert query("SELECT * FROM events ORDER BY id") == events_before
    assert count(query, "candidates") == 5


def test_spec67_full_flow_then_scheduled_purge_leaves_no_trace(client, seed, ai, query, db):
    """審查 3-3：保存期限過後由排程清除，同樣不留痕跡。"""
    _run_full_flow(client, seed, ai)
    events_before = query("SELECT * FROM events ORDER BY id")
    set_clock(FixedClock(datetime(2027, 3, 1, 10, 0, tzinfo=TZ)))
    scheduler.run_once(db)
    _assert_no_residue(client, query)
    assert query("SELECT * FROM events ORDER BY id") == events_before


def test_spec67_queued_job_purged_before_worker_runs_sends_nothing(client, seed, ai, query, db):
    """審查 2-2：背景工作排隊時先清除原文，worker 之後才執行，已清除的原句不得送給 AI，也不留在任何表。"""
    seed(SEED_BASE)
    job_id = ingest(client, lines(31, MARK)).json()["job_id"]
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    ai.script("AI-01", {"items": []}, {"items": []}, {"items": []})
    for _ in range(4):
        worker.run_once(db, ai)
    assert MARK not in str(ai_calls(ai))
    assert tables_containing(query, MARK) == {}
    assert count(query, "candidates") == 0
    job = client.get(f"{API}/ingest/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] in ("succeeded", "failed")
    assert MARK not in job.text


def test_spec67_failed_job_then_purge_leaves_no_trace(client, seed, ai, query, db):
    """失敗的工作保留摘錄；清除後 jobs 的 payload、result、error 也不得留原文。"""
    from app.ai.client import AIInvalidOutput

    seed(SEED_BASE)
    ingest(client, lines(31, MARK))
    ai.script("AI-01", *[AIInvalidOutput(f"echo {MARK}") for _ in range(6)])
    for _ in range(6):
        worker.run_once(db, ai)
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    assert tables_containing(query, MARK) == {}


def _run_async_flow(client, seed, ai, db, query):
    """審查 3-3 的背景路徑：超過 30 行 → worker 產生候選 → 帶冪等鍵確認。回傳工作編號。"""
    seed(SEED_BASE)
    r = ingest(client, f"[09:00] 我：API 介面定義要延到 11/19 {MARK}\n" + lines(30, MARK))
    assert r.status_code == 200 and r.json()["mode"] == "async", r.text
    job_id = r.json()["job_id"]
    first = query("SELECT min(id) AS i FROM sources")[0]["i"]
    ai.script("AI-01", {"items": [
        {"ref": first, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure", "echo": f"{MARK} 要延到"}]})
    worker.run_once(db, ai)
    assert client.get(f"{API}/ingest/jobs/{job_id}").json()["status"] == "succeeded"
    cid = query("SELECT id FROM candidates")[0]["id"]
    assert client.post(f"{API}/candidates/{cid}/confirm", json={"expected_version": 1},
                       headers={"Idempotency-Key": "qc-async-1"}).status_code == 200
    return job_id


def test_spec67_async_flow_then_purge_all_leaves_no_trace(client, seed, ai, query, db):
    """審查 3-3：背景收件走完後全部清除，jobs、ai_runs、冪等暫存都不留原句。"""
    job_id = _run_async_flow(client, seed, ai, db, query)
    assert tables_containing(query, MARK)  # 清除前確實找得到
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    _assert_no_residue(client, query)
    assert MARK not in client.get(f"{API}/ingest/jobs/{job_id}").text
    assert count(query, "candidates") == 1 and count(query, "events") == 1


def test_spec67_async_flow_then_scheduled_purge_leaves_no_trace(client, seed, ai, query, db):
    """審查 3-3：背景收件走完後由排程清除。"""
    job_id = _run_async_flow(client, seed, ai, db, query)
    set_clock(FixedClock(datetime(2027, 3, 1, 10, 0, tzinfo=TZ)))
    scheduler.run_once(db)
    _assert_no_residue(client, query)
    assert MARK not in client.get(f"{API}/ingest/jobs/{job_id}").text
    assert count(query, "candidates") == 1 and count(query, "events") == 1
