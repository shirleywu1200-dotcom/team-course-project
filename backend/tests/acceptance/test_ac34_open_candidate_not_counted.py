"""AC-34：open 候選不進甘特圖與統計（FR-INB-09、不可破原則 1）。

週報沒有端點（Phase 9 不在本 PR），週報部分移交 AC-48。
"""

from tests.acceptance.helpers import API, SEED_BASE, SEED_CANDIDATES, count, ingest


def _gantt(client, project_id=1):
    r = client.get(f"{API}/projects/{project_id}/gantt")
    assert r.status_code == 200, r.text
    return r.json()


def test_ac34_gantt_ignores_open_candidates(client, seed):
    seed(SEED_BASE)
    before = _gantt(client)
    seed(SEED_CANDIDATES)
    after = _gantt(client)
    assert after["rows"] == before["rows"]
    assert after["summary"]["done"] == before["summary"]["done"] == 1
    assert after["summary"]["delayed"] == before["summary"]["delayed"] == 0
    assert after["summary"]["total"] == before["summary"]["total"]
    row = next(r for r in after["rows"] if r["task_id"] == 2)
    assert (row["latest_due"], row["delta_days"], row["blocked"], row["status"]) == ("2026-11-14", 0, False, "doing")


def test_ac34_gantt_counts_open_candidates_separately(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    # 專案 1 的任務有 7 筆 open 候選；待配對（沒有任務）的那筆不屬於任何專案（審查 2-10）
    assert _gantt(client)["summary"]["open_candidates"] == 7
    assert _gantt(client, 3)["summary"]["open_candidates"] == 0


def test_ac34_decided_candidates_leave_open_count(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    assert client.post(f"{API}/candidates/3/ignore").status_code == 200
    assert _gantt(client)["summary"]["open_candidates"] == 6


def test_ac34_time_management_stats_ignore_open_candidates(client, seed):
    seed(SEED_BASE)
    before = client.get(f"{API}/stats/time-management").json()
    seed(SEED_CANDIDATES)
    after = client.get(f"{API}/stats/time-management").json()
    assert after == before
    assert after["unmarked"] == 0 and after["better"]["count"] == 0 and after["worse"]["count"] == 0


def test_ac34_ingest_writes_no_event_and_changes_no_task(client, seed, ai, query):
    seed(SEED_BASE)
    tasks_before = query("SELECT * FROM tasks ORDER BY id")
    ai.script("AI-01", {"items": [
        {"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"},
        {"ref": 2, "kind": "done", "task_id": 3, "certainty": "sure"},
        {"ref": 3, "kind": "stuck", "task_id": 1, "certainty": "sure"}]})
    r = ingest(client, "[10:15] 我：API 介面定義要延到 11/19\n[10:16] 我：測試環境建置完成了\n[10:17] 阿德：畫面規格 v1 卡住了")
    assert r.status_code == 200, r.text
    assert r.json()["result"]["created"] == 3
    assert {c["state"] for c in r.json()["candidates"]} == {"open"}
    assert count(query, "events") == 0
    assert query("SELECT * FROM tasks ORDER BY id") == tasks_before


def test_ac34_task_list_and_history_ignore_open_candidates(client, seed):
    seed(SEED_BASE + SEED_CANDIDATES)
    assert client.get(f"{API}/events").json()["total"] == 0
    r = client.get(f"{API}/tasks/2")
    assert r.status_code == 200
    assert "2026-11-19" not in r.text


def test_ac34_open_count_excludes_confirmed_ignored_and_unmatched(client, seed):
    """審查 2-10：專案 1 的任務有 open、confirmed、ignored 候選與 open 的待釐清；只算 open。"""
    seed(SEED_BASE + SEED_CANDIDATES + """
        UPDATE candidates SET state = 'confirmed', decision = 'confirm', decided_at = '2026-11-11T09:30+08:00' WHERE id = 1;
        UPDATE candidates SET state = 'ignored', decision = 'ignore', decided_at = '2026-11-11T09:30+08:00' WHERE id = 3;
    """)
    # 剩 2、6、7（open）與 4、8（open 的待釐清）；5 是待配對，沒有任務，不屬於任何專案
    assert _gantt(client)["summary"]["open_candidates"] == 5
