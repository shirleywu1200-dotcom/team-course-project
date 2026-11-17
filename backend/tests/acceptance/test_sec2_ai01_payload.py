"""資安規則 2、FR-GOV-05：送給 AI-01 的 payload 只含必要摘錄與任務清單，私人範圍在送出前排除。"""

from app import worker
from tests.acceptance.helpers import MARK, SEED_BASE, SEED_CANDIDATES, ai_calls, ingest, lines
from tests.conftest import TEST_TOKEN

TEXT = "[10:12] 阿德：畫面規格 v1 確定延到 11/18"
PRIVATE_TITLES = ("訂機票祕密行程", "私人健檢預約", "薪資調整試算")


def _payload(client, ai, project_id=1, text=TEXT):
    ai.script("AI-01", {"items": []})
    r = ingest(client, text, project_id=project_id)
    assert r.status_code == 200, r.text
    calls = ai_calls(ai, "AI-01")
    assert len(calls) == 1
    return calls[0]


def test_sec2_payload_has_only_expected_keys(client, seed, ai):
    seed(SEED_BASE)
    p = _payload(client, ai)
    assert set(p) == {"today", "messages", "tasks"}
    assert p["today"] == "2026-11-11"
    assert all(set(m) == {"ref", "speaker", "spoken_at", "text"} for m in p["messages"])
    assert all(set(t) == {"id", "title", "owner", "latest_due"} for t in p["tasks"])
    assert [(m["speaker"], m["spoken_at"], m["text"]) for m in p["messages"]] == [("阿德", "10:12", "畫面規格 v1 確定延到 11/18")]
    assert TEST_TOKEN not in str(p)


def test_sec2_private_tasks_never_sent_with_project(client, seed, ai):
    """審查 3-1：工作專案裡的私人範圍任務也要排除。"""
    seed(SEED_BASE)
    p = _payload(client, ai, project_id=1)
    assert {t["id"] for t in p["tasks"]} == {1, 2, 3}  # 專案 1 未完成且為工作範圍的任務
    assert not any(title in str(p) for title in PRIVATE_TITLES)


def test_sec2_private_tasks_never_sent_without_project(client, seed, ai):
    """審查 3-1：沒指定專案時，私人專案的任務與私人單點任務都不送。"""
    seed(SEED_BASE)
    p = _payload(client, ai, project_id=None)
    ids = {t["id"] for t in p["tasks"]}
    assert ids.isdisjoint({4, 5, 6})
    assert ids == {1, 2, 3, 8, 9}
    assert not any(title in str(p) for title in PRIVATE_TITLES)


def test_sec2_done_tasks_and_other_projects_not_sent(client, seed, ai):
    seed(SEED_BASE)
    p = _payload(client, ai, project_id=3)
    assert [t["id"] for t in p["tasks"]] == [8]


def test_sec2_old_excerpts_are_not_resent(client, seed, ai):
    """只送這次貼上的訊息，不帶資料庫裡既有的摘錄。"""
    seed(SEED_BASE + SEED_CANDIDATES)
    p = _payload(client, ai, text="[11:00] 小薇：首頁文案好了")
    assert len(p["messages"]) == 1
    assert MARK not in str(p)


def test_sec2_duplicate_messages_are_not_resent(client, seed, ai):
    seed(SEED_BASE)
    _payload(client, ai)
    ai.script("AI-01", {"items": []})
    assert ingest(client, TEXT + "\n[10:20] 小薇：首頁文案好了").status_code == 200
    calls = ai_calls(ai, "AI-01")
    assert [m["text"] for m in calls[-1]["messages"]] == ["首頁文案好了"]


def test_sec2_async_payload_follows_same_rules(client, seed, ai, db):
    seed(SEED_BASE)
    assert ingest(client, lines(31), project_id=1).json()["mode"] == "async"
    ai.script("AI-01", {"items": []})
    worker.run_once(db, ai)
    p = ai_calls(ai, "AI-01")[0]
    assert set(p) == {"today", "messages", "tasks"}
    assert {t["id"] for t in p["tasks"]} == {1, 2, 3}
    assert not any(title in str(p) for title in PRIVATE_TITLES)
