"""FR-INB-03（審查 3-5）：只存必要摘錄，不存整段對話。檔名暫用，待指定 AC 編號。"""

from tests.acceptance.helpers import MARK, SEED_BASE, count, ingest, lines

FIVE_LINES = lines(5, MARK)


def _strings(value):
    """走訪 JSON，取出所有字串值。"""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def test_fr_inb03_no_source_row_holds_the_whole_paste(client, seed, ai, query):
    seed(SEED_BASE)
    ai.script("AI-01", {"items": []})
    assert ingest(client, FIVE_LINES).status_code == 200
    excerpts = [r["excerpt"] for r in query("SELECT excerpt FROM sources")]
    assert len(excerpts) == 5  # 一則訊息一列
    for e in excerpts:
        assert e != FIVE_LINES
        assert "\n" not in e and len(e) < len(FIVE_LINES)
    assert count(query, "jobs") == 0


def test_fr_inb03_job_payload_does_not_hold_the_whole_paste(client, seed, query):
    seed(SEED_BASE)
    text = lines(31, MARK)
    r = ingest(client, text)
    assert r.status_code == 200 and r.json()["mode"] == "async", r.text
    payload = query("SELECT payload FROM jobs")[0]["payload"]
    for s in _strings(payload):
        assert text not in s
        assert s.count("\n") < 30  # 也不是換個欄位名把整段存進去
    assert query("SELECT count(*) AS n FROM sources WHERE excerpt = :t", t=text)[0]["n"] == 0
