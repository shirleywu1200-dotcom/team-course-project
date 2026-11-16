"""AC-37：認不出任務的訊息成為待配對，系統不猜（FR-INB-07、FR-INB-14）。"""

from tests.acceptance.helpers import API, SEED_BASE, SEED_CANDIDATES, count, created, ingest

TEXT = "[10:30] 阿德：報表處理我來接"


def test_ac37_message_without_task_becomes_unmatched(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "delay", "task_id": None, "new_due": "12/20", "certainty": "sure"}]})
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    cands = r.json()["candidates"]
    assert [(c["kind"], c["certainty"], c["task"]) for c in cands] == [("unmatched", "to_match", None)]
    assert query("SELECT kind, task_id FROM candidates") == [{"kind": "unmatched", "task_id": None}]


def test_ac37_unknown_task_id_is_never_mapped_to_an_existing_task(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "stuck", "task_id": 999, "certainty": "sure"}]})
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert all(c["task"] is None for c in r.json()["candidates"])
    assert query("SELECT count(*) AS n FROM candidates WHERE task_id IS NOT NULL")[0]["n"] == 0
    assert query("SELECT count(*) AS n FROM tasks WHERE blocked")[0]["n"] == 0


def test_ac37_task_outside_given_project_is_not_matched(client, seed, ai, query):
    """收件指定專案 1，AI 卻回專案 3 的任務：不採用。"""
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "stuck", "task_id": 8, "certainty": "sure"}]})
    r = ingest(client, TEXT, project_id=1)
    assert r.status_code == 200, r.text
    assert query("SELECT count(*) AS n FROM candidates WHERE task_id = 8")[0]["n"] == 0


def test_ac37_private_task_id_from_ai_is_not_matched(client, seed, ai, query):
    """私人任務沒送給 AI，AI 回了它的 id 也不能掛上去。"""
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "stuck", "task_id": 6, "certainty": "sure"}]})
    r = ingest(client, TEXT, project_id=1)
    assert r.status_code == 200, r.text
    assert query("SELECT count(*) AS n FROM candidates WHERE task_id = 6")[0]["n"] == 0


def test_fr_inb07_irrelevant_message_is_skipped_and_counted(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [{"ref": 1, "kind": "none"}]})
    r = ingest(client, "[12:00] 小薇：中午吃什麼")
    assert r.status_code == 200, r.text
    assert r.json()["result"]["created"] == 0
    assert r.json()["result"]["skipped"] == 1
    assert count(query, "candidates") == 0


def test_fr_inb14_create_task_from_unmatched(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    body = created(client.post(f"{API}/candidates/5/create-task",
                               json={"title": "報表處理", "owner": "阿德", "due": "2026-12-20", "project_id": 1}))
    assert body["candidate"]["state"] == "confirmed"
    task = query("SELECT title, owner_name, project_id, orig_due::text AS o, latest_due::text AS l "
                 "FROM tasks WHERE id = :i", i=body["task"]["id"])[0]
    assert task == {"title": "報表處理", "owner_name": "阿德", "project_id": 1, "o": "2026-12-20", "l": "2026-12-20"}
    ev = query("SELECT kind, task_id FROM events")
    assert ev == [{"kind": "task", "task_id": body["task"]["id"]}]
    assert query("SELECT state FROM candidates WHERE id = 5")[0]["state"] == "confirmed"


def test_spec51_create_task_from_candidate_returns_201(client, seed):
    """spec 5.1（DA-20，2026-11-16 擴充）：由候選建任務會建立資源，回 201。"""
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/5/create-task", json={"title": "報表處理", "owner": "阿德", "due": "2026-12-20"})
    assert r.status_code == 201


def test_fr_inb14_unmatched_cannot_use_confirm_endpoint(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    r = client.post(f"{API}/candidates/5/confirm", json={"expected_version": 1})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert query("SELECT state FROM candidates WHERE id = 5")[0]["state"] == "open"


def test_fr_inb14_create_task_only_for_unmatched(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    before = count(query, "tasks")
    r = client.post(f"{API}/candidates/2/create-task", json={"title": "報表處理", "due": "2026-12-20"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "tasks") == before


def test_fr_inb15_ignore_unmatched_keeps_record(client, seed, query):
    seed(SEED_BASE + SEED_CANDIDATES)
    before = count(query, "tasks")
    assert client.post(f"{API}/candidates/5/ignore").status_code == 200
    assert query("SELECT state FROM candidates WHERE id = 5")[0]["state"] == "ignored"
    assert count(query, "tasks") == before
    assert count(query, "events") == 0


def test_fr_inb14_create_task_without_due_is_rejected_and_stays_open(client, seed, query):
    """審查 2-13(b)：期限由使用者確認，缺 due 不建任務。"""
    seed(SEED_BASE + SEED_CANDIDATES)
    before = count(query, "tasks")
    r = client.post(f"{API}/candidates/5/create-task", json={"title": "報表處理"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert query("SELECT state FROM candidates WHERE id = 5")[0]["state"] == "open"
    assert count(query, "tasks") == before
    assert count(query, "events") == 0


def test_fr_inb14_create_task_without_owner_uses_speaker(client, seed, query):
    """審查 2-13(c)：沒帶 owner 時，負責人為發言者（候選 5 的發言者是阿德）。"""
    seed(SEED_BASE + SEED_CANDIDATES)
    body = created(client.post(f"{API}/candidates/5/create-task", json={"title": "報表處理", "due": "2026-12-20"}))
    assert query("SELECT owner_name FROM tasks WHERE id = :i", i=body["task"]["id"])[0]["owner_name"] == "阿德"
