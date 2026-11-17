"""AC-55：500 列匯入的 preview 在 2 秒內完成（不含 AI-07）；大小上限（FR-IMP-01）。"""

import time

from tests.acceptance.helpers import API, ai_calls

HEADER = "任務,負責人,開始,結束"


def _table(n):
    return "\n".join([HEADER] + [f"任務{i},我,2026-11-16,2026-11-18" for i in range(n)])


def _preview(client, text):
    return client.post(f"{API}/projects/import/preview", json={"text": text, "target": "new", "new_name": "大專案"})


def test_ac55_preview_500_rows_within_2_seconds(client, ai):
    text = _table(500)
    assert len(text) <= 50000
    start = time.perf_counter()
    r = _preview(client, text)
    elapsed = time.perf_counter() - start
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["importable"] == 500
    assert ai_calls(ai, "AI-07") == []
    assert elapsed < 2.0, f"preview 花了 {elapsed:.2f} 秒"


def test_fr_imp01_501_rows_is_too_large(client):
    r = _preview(client, _table(501))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_fr_imp01_over_50000_chars_is_too_large(client):
    text = HEADER + "\n" + "長" * 50001 + ",我,2026-11-16,2026-11-18"
    r = _preview(client, text)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_fr_imp01_commit_over_500_rows_is_too_large(client, query):
    rows = [{"index": i, "title": f"任務{i}", "owner": "我", "start": "2026-11-16", "end": "2026-11-18"} for i in range(501)]
    r = client.post(f"{API}/projects/import/commit", json={"target": "new", "new_name": "大專案", "rows": rows})
    assert r.status_code == 413
    assert query("SELECT count(*) AS n FROM tasks")[0]["n"] == 0
