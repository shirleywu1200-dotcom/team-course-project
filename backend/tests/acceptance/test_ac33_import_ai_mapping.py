"""AC-33：表頭規則對不上時才呼叫 AI-07；AI 不可用時可手動指定（FR-IMP-02、spec 6.6）。"""

import pytest

from app.ai.client import AIInvalidOutput, AIUnavailable
from tests.acceptance.helpers import API, ai_calls, count

# 非標準表頭；第 3 列以後的內容不該送給 AI（樣本最多 2 列）。
TABLE = """工項,PIC,起,交期
需求確認,我,2026-11-16,2026-11-18
畫面設計,小薇,2026-11-17,2026-11-21
ROW3SECRET,阿德,2026-11-20,2026-11-24
ROW4SECRET,阿德,2026-11-22,2026-11-26"""
AI_MAP = {"title": 0, "owner": 1, "start": 2, "end": 3}


def _preview(client, **extra):
    r = client.post(f"{API}/projects/import/preview", json={"text": TABLE, "target": "new", "new_name": "新專案", **extra})
    assert r.status_code == 200, r.text
    return r.json()


def test_ac33_unknown_header_calls_ai07_and_marks_mapped_by_ai(client, ai, query):
    ai.script("AI-07", AI_MAP)
    body = _preview(client)
    assert len(ai_calls(ai, "AI-07")) == 1
    assert body["ai_status"] == "ok"
    cm = body["column_map"]
    assert cm["mapped_by"] == "ai"
    assert {k: cm[k] for k in AI_MAP} == AI_MAP
    assert body["summary"]["importable"] == 4
    run = query("SELECT id, node_id, status FROM ai_runs")
    assert run == [{"id": cm["ai_run_id"], "node_id": "AI-07", "status": "ok"}]


def test_ac33_ai_unavailable_returns_mapped_by_null(client, ai):
    ai.script("AI-07", AIUnavailable())
    body = _preview(client)
    assert body["ai_status"] == "unavailable"
    assert body["column_map"]["mapped_by"] is None
    assert body["rows"] == []
    assert body["column_map"].get("ai_run_id") is None


def test_ac33_ai_invalid_output_returns_mapped_by_null(client, ai):
    ai.script("AI-07", AIInvalidOutput())
    body = _preview(client)
    assert body["ai_status"] == "invalid_output"
    assert body["column_map"]["mapped_by"] is None


def test_ac33_ai_mapping_missing_required_column_is_invalid(client, ai):
    ai.script("AI-07", {"title": 0, "owner": 1, "start": 2, "end": None})
    body = _preview(client)
    assert body["ai_status"] == "invalid_output"
    assert body["column_map"]["mapped_by"] is None


def test_ac33_ai07_is_not_retried(client, ai):
    ai.script("AI-07", AIInvalidOutput(), AI_MAP)
    _preview(client)
    assert len(ai_calls(ai, "AI-07")) == 1


def test_ac33_manual_column_map_works_without_ai(client, ai):
    body = _preview(client, column_map=AI_MAP)
    assert ai_calls(ai, "AI-07") == []
    assert body["column_map"]["mapped_by"] == "manual"
    assert body["summary"] == {"importable": 4, "blocking": 0}
    assert body["rows"][0]["title"] == "需求確認" and body["rows"][0]["end"] == "2026-11-18"


def test_ac33_preview_with_ai_writes_no_business_data(client, ai, query):
    ai.script("AI-07", AI_MAP)
    _preview(client)
    for t in ("projects", "tasks", "events", "ai_feedback"):
        assert count(query, t) == 0


def test_sec2_ai07_payload_has_headers_and_at_most_two_samples(client, ai):
    """資安 2、FR-GOV-05：AI-07 只收到表頭與最多 2 列樣本。"""
    ai.script("AI-07", AI_MAP)
    _preview(client)
    payload = ai_calls(ai, "AI-07")[0]
    assert set(payload) == {"headers", "samples"}
    assert payload["headers"] == ["工項", "PIC", "起", "交期"]
    assert len(payload["samples"]) <= 2
    assert "SECRET" not in str(payload)


@pytest.mark.parametrize("bad_map", [
    {"title": 9, "owner": 1, "start": 2, "end": 3},   # 索引超出欄數（表格只有 4 欄）
    {"title": 0, "owner": 1, "start": 2, "end": 0},   # 兩欄指向同一索引
])
def test_spec82_ai07_out_of_range_or_duplicate_index_is_invalid_output(client, ai, query, bad_map):
    """審查 2-9：AI 輸出須通過結構驗證（spec 8.2），不合格降級而不是回 500（spec 5.3）。"""
    ai.script("AI-07", bad_map)
    body = _preview(client)  # 內含 200 的檢查
    assert body["ai_status"] == "invalid_output"
    assert body["column_map"]["mapped_by"] is None
    for t in ("projects", "tasks", "events"):
        assert count(query, t) == 0
