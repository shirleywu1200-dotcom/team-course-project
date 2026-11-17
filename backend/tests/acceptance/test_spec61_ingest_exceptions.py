"""spec 6.1 例外表（審查 1-8）：部分行無法解析、同一則訊息同時含延期與完成。檔名暫用，待指定 AC 編號。"""

import pytest

from tests.acceptance.helpers import SEED_BASE, count, ingest

DELAY = {"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/19", "certainty": "sure"}
DONE = {"ref": 1, "kind": "done", "task_id": 2, "certainty": "sure"}


def test_spec61_unparseable_line_is_skipped_and_other_lines_still_processed(client, seed, ai, query):
    """審查 1-8(a)：沒有時間也沒有發言者的那一行略過並計入 skipped，其他行照常建候選。"""
    seed(SEED_BASE)
    ai.script("AI-01", {"items": [DELAY]})
    r = ingest(client, "這一行沒有時間也沒有發言者\n[10:15] 我：API 介面定義要延到 11/19")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["result"]["created"] == 1
    assert body["result"]["skipped"] == 1
    assert [c["kind"] for c in body["candidates"]] == ["delay"]
    assert query("SELECT kind, task_id FROM candidates") == [{"kind": "delay", "task_id": 2}]


@pytest.mark.parametrize("items", [[DELAY, DONE], [DONE, DELAY]])
def test_spec61_delay_and_done_in_one_message_keeps_only_done(client, seed, ai, query, items):
    """審查 1-8(c)〔假設〕：同一則訊息同時含延期與完成，只取完成；與 AI 回傳的先後無關。"""
    seed(SEED_BASE)
    ai.script("AI-01", {"items": items})
    r = ingest(client, "[10:15] 我：API 介面定義完成了，原本說要延到 11/19 就不用了")
    assert r.status_code == 200, r.text
    assert [c["kind"] for c in r.json()["candidates"]] == ["done"]
    assert query("SELECT kind, task_id FROM candidates") == [{"kind": "done", "task_id": 2}]
    assert count(query, "events") == 0
