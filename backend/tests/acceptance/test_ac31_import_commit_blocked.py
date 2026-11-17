"""AC-31：有未略過的錯誤列時，commit 整批拒絕（FR-IMP-05）。"""

from tests.acceptance.helpers import API, count, created

GOOD = {"index": 0, "title": "需求確認", "owner": "我", "start": "2026-11-16", "end": "2026-11-18"}
NO_END = {"index": 1, "title": "畫面設計CELLX", "owner": "小薇", "start": "2026-11-17", "end": None}
END_BEFORE_START = {"index": 2, "title": "API 開發", "owner": "阿德", "start": "2026-11-25", "end": "2026-11-20"}


def _commit(client, rows):
    return client.post(f"{API}/projects/import/commit", json={"target": "new", "new_name": "新專案", "rows": rows})


def _nothing_written(query):
    return all(count(query, t) == 0 for t in ("projects", "tasks", "events"))


def test_ac31_blocking_row_rejects_whole_commit(client, query):
    r = _commit(client, [GOOD, NO_END])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _nothing_written(query)


def test_ac31_server_revalidates_rows_without_preview(client, query):
    """不信前端：沒有 blocking 標記的不合法列一樣被擋。"""
    r = _commit(client, [GOOD, END_BEFORE_START])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _nothing_written(query)


def test_ac31_missing_title_rejects_commit(client, query):
    r = _commit(client, [GOOD, {"index": 1, "title": "", "owner": "我", "start": "2026-11-16", "end": "2026-11-18"}])
    assert r.status_code == 422
    assert _nothing_written(query)


def test_ac31_skipped_error_rows_allow_commit(client, query):
    r = _commit(client, [GOOD, {**NO_END, "skip": True}, {**END_BEFORE_START, "skip": True}])
    body = created(r)
    assert body["created"] == 1
    assert body["skipped"] == 2
    assert count(query, "tasks") == 1


def test_fr_imp05_no_importable_row_is_empty_selection(client, query):
    r = _commit(client, [{**GOOD, "skip": True}])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "EMPTY_SELECTION"
    assert _nothing_written(query)


def test_sec3_commit_validation_error_does_not_echo_cells(client):
    """資安 3：錯誤 details 只放列號與欄位名，不放儲存格內容。"""
    r = _commit(client, [GOOD, NO_END])
    assert r.status_code == 422
    assert "CELLX" not in r.text
