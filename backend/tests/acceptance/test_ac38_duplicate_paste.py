"""AC-38：同一段文字貼兩次只回報重複數，不新增候選（FR-INB-04，沒有日期標頭的原規則）。"""

import pytest

from tests.acceptance.helpers import API, MARK, SEED_BASE, count, ingest

TEXT = "[10:12] 阿德：畫面規格 v1 確定延到 11/18\n[10:15] 我：API 介面定義要延到 11/19"
FIRST = {"items": [
    {"ref": 1, "kind": "delay", "task_id": 1, "new_due": "11/18", "certainty": "sure"},
    {"ref": 2, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"}]}
# 第二次貼上時新訊息的來源 id 無法事先得知，所以把可能的 id 都排進去；不屬於這次訊息的項目應被丟棄。
ANY_NEW = {"items": [{"ref": i, "kind": "stuck", "task_id": 3, "certainty": "sure"} for i in range(1, 12)]}


def _first(client, ai):
    ai.script("AI-01", FIRST)
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert r.json()["result"] == {**r.json()["result"], "created": 2, "duplicates": 0}


def test_ac38_second_paste_counts_duplicates_and_adds_nothing(client, seed, ai, query):
    seed(SEED_BASE)
    _first(client, ai)
    ai.script("AI-01", ANY_NEW)
    r = ingest(client, TEXT)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["duplicates"] == 2
    assert r.json()["result"]["created"] == 0
    assert r.json()["candidates"] == []
    assert count(query, "candidates") == 2
    assert count(query, "sources") == 2


def test_ac38_partially_new_paste_only_adds_new_messages(client, seed, ai, query):
    seed(SEED_BASE)
    _first(client, ai)
    ai.script("AI-01", ANY_NEW)
    r = ingest(client, TEXT + "\n[10:20] 小薇：測試環境建置卡住了")
    assert r.status_code == 200, r.text
    assert r.json()["result"]["duplicates"] == 2
    assert r.json()["result"]["created"] == 1
    assert count(query, "sources") == 3
    assert count(query, "candidates") == 3
    new = query("SELECT s.excerpt FROM candidates c JOIN sources s ON s.id = c.source_id WHERE c.kind = 'stuck'")
    assert new == [{"excerpt": "測試環境建置卡住了"}]


@pytest.mark.parametrize("line", [
    "[10:13] 阿德：畫面規格 v1 確定延到 11/18",   # 時間不同
    "[10:12] 小薇：畫面規格 v1 確定延到 11/18",   # 發言者不同
    "[10:12] 阿德：畫面規格 v1 確定延到 11/19",   # 內容不同
])
def test_ac38_different_time_speaker_or_content_is_not_duplicate(client, seed, ai, query, line):
    seed(SEED_BASE)
    _first(client, ai)
    ai.script("AI-01", {"items": []})
    r = ingest(client, line)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["duplicates"] == 0
    assert count(query, "sources") == 3


def test_ac38_same_text_in_another_project_is_still_duplicate(client, seed, ai, query):
    """雜湊只看時間、發言者、內容。"""
    seed(SEED_BASE)
    _first(client, ai)
    ai.script("AI-01", ANY_NEW)
    r = ingest(client, TEXT, project_id=3)
    assert r.json()["result"]["duplicates"] == 2
    assert count(query, "sources") == 2


def test_fr_inb04_duplicates_are_not_merged(client, seed, ai, query):
    """只回報重複數，不改動既有來源與候選。"""
    seed(SEED_BASE)
    _first(client, ai)
    before = (query("SELECT * FROM sources ORDER BY id"), query("SELECT * FROM candidates ORDER BY id"))
    ai.script("AI-01", ANY_NEW)
    ingest(client, TEXT)
    assert (query("SELECT * FROM sources ORDER BY id"), query("SELECT * FROM candidates ORDER BY id")) == before


def test_ac38_repaste_after_purge_is_duplicate_and_stays_purged(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": []})
    text = f"[10:12] 阿德：畫面規格 v1 確定延到 11/18 {MARK}"
    assert ingest(client, text).status_code == 200
    assert client.post(f"{API}/sources/purge", json={"confirm": True}).status_code == 200
    ai.script("AI-01", ANY_NEW)
    r = ingest(client, text)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["duplicates"] == 1
    assert query("SELECT excerpt FROM sources") == [{"excerpt": None}]
