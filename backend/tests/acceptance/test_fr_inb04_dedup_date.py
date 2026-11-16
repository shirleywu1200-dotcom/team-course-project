"""FR-INB-04（PR #20 B3）：有日期標頭時，日期併入去重判斷；沒有標頭維持原規則。檔名暫用，待指定 AC 編號。"""

from tests.acceptance.helpers import SEED_BASE, count, ingest

MSG = "[10:12] 阿德：今天進度正常"
TWO_DAYS = f"2026/11/10（二）\n{MSG}\n2026/11/11（三）\n{MSG}"
ONE_DAY = f"2026/11/11（三）\n{MSG}\n[10:15] 小薇：首頁文案好了"
NONE = {"items": []}


def test_fr_inb04_same_message_on_two_dates_is_not_duplicate(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", NONE)
    r = ingest(client, TWO_DAYS)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["duplicates"] == 0
    src = query("SELECT excerpt, excerpt_hash FROM sources ORDER BY id")
    assert [s["excerpt"] for s in src] == ["今天進度正常", "今天進度正常"]
    assert src[0]["excerpt_hash"] != src[1]["excerpt_hash"]


def test_fr_inb04_date_header_is_not_stored_as_a_message(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", NONE)
    assert ingest(client, ONE_DAY).status_code == 200
    assert count(query, "sources") == 2
    assert query("SELECT count(*) AS n FROM sources WHERE excerpt LIKE '%2026/11/11%'")[0]["n"] == 0


def test_fr_inb04_same_dated_paste_twice_is_duplicate(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", NONE)
    assert ingest(client, ONE_DAY).json()["result"]["duplicates"] == 0
    ai.script("AI-01", NONE)
    r = ingest(client, ONE_DAY)
    assert r.json()["result"]["duplicates"] == 2
    assert r.json()["result"]["created"] == 0
    assert count(query, "sources") == 2


def test_fr_inb04_same_message_under_a_new_date_is_new(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", NONE)
    ingest(client, f"2026/11/10（二）\n{MSG}")
    ai.script("AI-01", NONE)
    r = ingest(client, f"2026/11/11（三）\n{MSG}")
    assert r.json()["result"]["duplicates"] == 0
    assert count(query, "sources") == 2


def test_fr_inb04_without_date_header_original_rule_still_applies(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", NONE)
    assert ingest(client, MSG).json()["result"]["duplicates"] == 0
    ai.script("AI-01", NONE)
    r = ingest(client, MSG)
    assert r.json()["result"]["duplicates"] == 1
    assert count(query, "sources") == 1


def test_fr_inb04_message_before_date_header_uses_original_rule(client, seed, ai, query):
    """審查 2-6(a)：標頭之前的訊息沒有日期可用，照原規則；之後不帶標頭再貼同一則算重複。"""
    seed(SEED_BASE)
    ai.script("AI-01", NONE)
    r = ingest(client, f"{MSG}\n2026/11/11（三）\n[10:15] 小薇：首頁文案好了")
    assert r.status_code == 200, r.text
    assert r.json()["result"]["duplicates"] == 0
    assert count(query, "sources") == 2
    ai.script("AI-01", NONE)
    again = ingest(client, MSG)
    assert again.status_code == 200, again.text
    assert again.json()["result"]["duplicates"] == 1
    assert count(query, "sources") == 2
