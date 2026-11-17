"""週報端點驗收測試（spec 5.14、FR-RPT-01～04、AC-25、48～51、65～67）。

Dev-A 暫代撰寫：issue #18 裁定 QC 帳號定案前由 Dev-A 自補，QC-1 帳號定案後移交複核或接手。
只經 HTTP 與 SQL 種子操作，不呼叫 app 內部函式。
#18 H1、H2、J1～J10 尚待產品負責人確認，本檔依預設撰寫；AI-05 的輸出格式依 #22 的提案，定案後調整。
"""

import copy
import json
from datetime import datetime

import pytest
from sqlalchemy import text

from app.ai.client import DEFAULT_TIMEOUT_S, AIInvalidOutput, AITimeout, AIUnavailable, FakeAIClient
from app.clock import TZ

DRAFT = "/api/v1/reports/weekly/draft"
ONE = "/api/v1/reports/weekly/{}"
MANUAL = "/api/v1/reports/weekly/{}/manual"
WEEK = "2026-11-09"
MARK = "機密標記XYZ"
KEYS = {"id", "week_start", "ai_status", "excluded_private", "draft", "items", "validated", "manual_text",
        "updated_at"}

TS = "'2026-11-01T09:00+08:00'"
DATA = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '工作專案', 'work', 'manager', {TS}, {TS});
INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, blocked, version, created_at, updated_at) VALUES
  (1, 1, '本週完成', '我',   'work',    '2026-11-01', '2026-11-10', '2026-11-10', 'done', '2026-11-10', false, 2, {TS}, {TS}),
  (2, 1, '延期任務', '小薇', 'work',    '2026-11-01', '2026-11-12', '2026-11-15', 'todo', NULL, false, 2, {TS}, {TS}),
  (3, 1, '下週到期', '我',   'work',    '2026-11-01', '2026-11-18', '2026-11-18', 'todo', NULL, false, 1, {TS}, {TS}),
  (4, 1, '私人機密任務', '我', 'private', '2026-11-01', '2026-11-12', '2026-11-18', 'todo', NULL, false, 2, {TS}, {TS});
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    delta_days, mine) VALUES
  (11, '2026-11-10T18:00+08:00', 1, 1, '本週完成', 'status', 'status', 'todo', 'done', 'manual', NULL, true),
  (21, '2026-11-10T10:00+08:00', 1, 2, '延期任務', 'due', 'latest_due', '2026-11-12', '2026-11-15', 'manual', 3, false),
  (41, '2026-11-11T10:00+08:00', 1, 4, '私人機密任務', 'due', 'latest_due', '2026-11-12', '2026-11-18', 'manual', 6, true);
"""

AI_ITEMS = [{"section": "done", "task_id": 1, "event_id": 11},
            {"section": "delay", "task_id": 2, "event_id": 21},
            {"section": "next", "task_id": 3, "event_id": None}]
AI_OK = {"draft": "本週（11/09–11/15）工作進度\n【本週完成】本週完成", "items": AI_ITEMS}
FALLBACK = [{"section": "done", "task_id": 1, "event_id": 11},
            {"section": "delay", "task_id": 2, "event_id": 21},
            {"section": "next", "task_id": 2, "event_id": None},    # 2：最新預計 11/15，早於下週一（G6、H1）
            {"section": "next", "task_id": 3, "event_id": None}]


@pytest.fixture
def data(seed):
    seed(DATA)


def draft(client, week=WEEK):
    return client.post(DRAFT, json={"week_start": week})


def ids(items):
    """只取三個識別鍵；可讀欄位另由第四段的測試驗證（2026-11-17 #23 新增可讀內容）。"""
    return [{k: i[k] for k in ("section", "task_id", "event_id")} for i in items]


def rows(query):
    return query("SELECT id, ai_status, ai_draft, ai_items, manual_text, excluded_private FROM reports")


# ---------- AI 不可用（AC-50）與第一次產生 ----------

def test_first_draft_with_ai_unavailable_returns_fallback(client, data, query):
    r = draft(client)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == KEYS
    assert (body["ai_status"], body["validated"], body["draft"], body["manual_text"]) == \
        ("unavailable", False, None, None)
    assert ids(body["items"]) == FALLBACK and body["excluded_private"] == 1 and body["week_start"] == WEEK
    assert body["updated_at"].endswith("+08:00")
    [row] = rows(query)
    assert (row["ai_status"], row["ai_draft"], row["ai_items"]) == ("unavailable", None, None)


def test_empty_week_creates_a_row(client, query):
    body = draft(client).json()
    assert (body["items"], body["excluded_private"]) == ([], 0) and len(rows(query)) == 1


def test_second_draft_reuses_the_same_row(client, data, query):
    first = draft(client).json()["id"]
    assert draft(client).json()["id"] == first and len(rows(query)) == 1


# ---------- AC-48：私人範圍 ----------

def test_private_tasks_never_reach_ai_or_response(client, data, ai):
    ai.script("AI-05", AI_OK)
    body = draft(client).json()
    sent = json.dumps(ai.calls, ensure_ascii=False, default=str)
    assert "私人機密任務" not in sent and '"task_id": 4' not in sent and "41" not in sent
    out = json.dumps(body, ensure_ascii=False)
    assert "私人機密任務" not in out and body["excluded_private"] == 1


# ---------- AI 成功、對帳（AC-49、AC-66、G4）----------

def test_successful_draft_is_stored_and_returned(client, data, ai, query):
    ai.script("AI-05", {"draft": AI_OK["draft"],
                        "items": [dict(i, title=MARK) for i in AI_ITEMS]})   # 多餘的鍵不保存
    body = draft(client).json()
    assert (body["ai_status"], body["validated"], body["draft"]) == ("ok", True, AI_OK["draft"])
    assert ids(body["items"]) == AI_ITEMS and body["items"][0]["title"] == "本週完成" and MARK not in json.dumps(body, ensure_ascii=False)
    [row] = rows(query)
    assert row["ai_status"] == "ok" and row["ai_items"] == AI_ITEMS and MARK not in json.dumps(row, default=str)


@pytest.mark.parametrize("bad", [
    {"section": "delay", "task_id": 2, "event_id": 999},   # AC-49：歷程中找不到
    {"section": "done", "task_id": 1, "event_id": 21},     # 別的任務的事件
    {"section": "next", "task_id": 4, "event_id": None},   # 私人任務（G4）
    {"section": "next", "task_id": 999, "event_id": None},  # 不存在的任務
])
def test_unreconciled_items_fall_back(client, data, ai, query, bad):
    ai.script("AI-05", {"draft": "x", "items": [*AI_ITEMS, bad]})
    body = draft(client).json()
    assert (body["validated"], body["draft"], ids(body["items"]), body["ai_status"]) == \
        (False, None, FALLBACK, "invalid_output")
    [row] = rows(query)
    assert (row["ai_status"], row["ai_draft"], row["ai_items"]) == ("invalid_output", None, None)


@pytest.mark.parametrize("output", [
    {"items": AI_ITEMS},                                    # 缺 draft
    {"draft": "x", "items": "not a list"},
    {"draft": "x", "items": [{"section": "done", "task_id": "1", "event_id": 11}]},
    {"draft": 3, "items": []},
])
def test_malformed_output_is_invalid(client, data, ai, output):
    ai.script("AI-05", output, output, output)   # 格式錯誤會重試，共 3 次（spec 5.14；2026-11-16 第三段修改）
    body = draft(client).json()
    assert (body["ai_status"], body["validated"]) == ("invalid_output", False)


@pytest.mark.parametrize(("error", "status"), [(AIInvalidOutput, "invalid_output"), (AITimeout, "unavailable"),
                                               (RuntimeError(MARK), "unavailable")])
def test_ai_errors_map_to_status_and_leak_nothing(client, data, ai, caplog, error, status):
    ai.script("AI-05", error, error, error)   # 逾時與格式錯誤會重試，共 3 次（spec 5.14；2026-11-16 第三段修改）
    r = draft(client)
    assert r.status_code == 200 and r.json()["ai_status"] == status
    assert MARK not in r.text and MARK not in caplog.text


# ---------- H2、AC-51：重新產生 ----------

def test_failed_regenerate_keeps_previous_success(client, data, ai, query):
    ai.script("AI-05", AI_OK)
    rid = draft(client).json()["id"]
    before = rows(query)
    again = draft(client).json()                      # 沒排輸出 → 不可用
    assert (again["ai_status"], again["validated"], again["draft"]) == ("unavailable", False, None)
    assert rows(query) == before                      # 整列不動（J4）
    got = client.get(ONE.format(rid)).json()
    assert (got["ai_status"], got["validated"], got["draft"]) == ("ok", True, AI_OK["draft"])


def test_failure_then_success_and_manual_text_kept(client, data, ai, query):
    rid = draft(client).json()["id"]
    client.put(MANUAL.format(rid), json={"manual_text": "我的人工版"})
    ai.script("AI-05", AI_OK, {"draft": "第二版", "items": AI_ITEMS})
    assert draft(client).json()["ai_status"] == "ok"
    body = draft(client).json()
    assert (body["draft"], body["manual_text"]) == ("第二版", "我的人工版")   # AC-51


def test_concurrent_row_creation_does_not_fail(client, data, db, query):
    # AI 呼叫期間，同一週的列被另一個請求建立了：仍回 200、只有一列，對方寫的人工版不被蓋掉
    class Racing(FakeAIClient):
        def call(self, node_id, payload, **kw):
            db.run(lambda c: c.execute(text(
                "INSERT INTO reports (kind, period_start, manual_text, created_at, updated_at) "
                "VALUES ('weekly', '2026-11-09', '他處人工版', now(), now())")))
            return AI_OK
    client.app.state.ai = Racing()
    r = draft(client)
    assert r.status_code == 200 and r.json()["validated"] is True
    [row] = rows(query)
    assert row["manual_text"] == "他處人工版" and row["ai_status"] == "ok"


# ---------- GET 重新對帳（第 1 點 (b)、AC-25、J1）----------

def generate_ok(client, ai):
    ai.script("AI-05", AI_OK)
    return draft(client).json()["id"]


def test_get_revalidates_after_task_turns_private(client, data, ai, seed):
    rid = generate_ok(client, ai)
    seed("UPDATE tasks SET scope = 'private' WHERE id = 2;")
    got = client.get(ONE.format(rid)).json()
    assert (got["validated"], got["draft"]) == (False, None)
    assert client.put(MANUAL.format(rid), json={"manual_text": "x"}).json()["validated"] is False


def test_get_revalidates_after_baseline_correction(client, data, ai, seed):
    rid = generate_ok(client, ai)
    seed("UPDATE tasks SET orig_due = '2026-11-15' WHERE id = 2;"
         "INSERT INTO events (ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, mine) "
         "VALUES ('2026-11-11T11:00+08:00', 1, 2, '延期任務', 'baseline', 'orig_due', '2026-11-12', '2026-11-15', "
         "'baseline_correction', false);")
    assert client.get(ONE.format(rid)).json()["validated"] is False


def test_get_tolerates_next_drift(client, data, ai, seed):
    rid = generate_ok(client, ai)
    seed("UPDATE tasks SET latest_due = '2026-12-30' WHERE id = 3;")   # 改期到下下週之後
    assert client.get(ONE.format(rid)).json()["validated"] is True


# ---------- GET、PUT（AC-67、J5、J10）----------

def test_put_manual_updates_only_manual_text(client, data, ai, query, clock):
    rid = generate_ok(client, ai)
    before = client.get(ONE.format(rid)).json()
    clock.set(datetime(2026, 11, 11, 12, 0, tzinfo=TZ))
    body = client.put(MANUAL.format(rid), json={"manual_text": "人工版", "ai_status": "invalid_output",
                                                 "excluded_private": 99}).json()
    assert body["manual_text"] == "人工版" and body["updated_at"] != before["updated_at"]
    for k in ("ai_status", "draft", "items", "excluded_private", "week_start"):
        assert body[k] == before[k]
    assert client.put(MANUAL.format(rid), json={"manual_text": None}).json()["manual_text"] is None


def test_manual_text_limits(client, data):
    rid = draft(client).json()["id"]
    assert client.put(MANUAL.format(rid), json={"manual_text": "字" * 20_000}).status_code == 200
    r = client.put(MANUAL.format(rid), json={"manual_text": MARK + "字" * 20_000})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE" and MARK not in r.text
    r = client.put(MANUAL.format(rid), json={"manual_text": f"{MARK}\x00"})
    assert r.status_code == 422 and MARK not in r.text
    assert client.put(MANUAL.format(rid), json={}).status_code == 422


@pytest.mark.parametrize("rid", ["999", "abc", "0", "-1", "99999999999999999999"])
def test_unknown_or_bad_ids(client, rid):
    for r in (client.get(ONE.format(rid)), client.put(MANUAL.format(rid), json={"manual_text": "x"})):
        assert r.status_code in (404, 422)
        assert r.json()["error"]["code"] in ("NOT_FOUND", "VALIDATION_ERROR")


def test_goal_report_id_is_not_found(client, seed, query):
    seed("INSERT INTO reports (id, kind, created_at, updated_at) VALUES (50, 'goal', now(), now());")
    assert client.get(ONE.format(50)).status_code == 404
    assert client.put(MANUAL.format(50), json={"manual_text": "x"}).status_code == 404


def test_get_and_put_do_not_call_ai(client, data, ai):
    rid = draft(client).json()["id"]
    calls = len(ai.calls)
    client.get(ONE.format(rid))
    client.put(MANUAL.format(rid), json={"manual_text": "x"})
    assert len(ai.calls) == calls


def test_endpoints_never_touch_history(client, data, ai, query):
    def snapshot():
        return query("SELECT count(*) AS n FROM events")[0]["n"], query("SELECT id, version FROM tasks ORDER BY id")

    before = snapshot()
    rid = generate_ok(client, ai)
    client.get(ONE.format(rid))
    client.put(MANUAL.format(rid), json={"manual_text": "x"})
    assert snapshot() == before


# ---------- J7：不存冪等快取 ----------

def test_draft_replay_with_same_key_reconciles_again(client, data, ai, seed, query):
    """重播若回快取，會略過重新對帳，回過期的 validated=true（#18 J7）。"""
    h = {"Idempotency-Key": "weekly-draft-1"}
    ai.script("AI-05", AI_OK)
    assert client.post(DRAFT, json={"week_start": WEEK}, headers=h).json()["validated"] is True
    seed("UPDATE tasks SET scope = 'private' WHERE id = 2;")
    ai.script("AI-05", AI_OK)
    again = client.post(DRAFT, json={"week_start": WEEK}, headers=h)
    assert again.headers.get("Idempotent-Replay") is None
    assert (again.json()["validated"], again.json()["draft"]) == (False, None)
    assert query("SELECT count(*) AS n FROM idempotency_keys")[0]["n"] == 0


def test_manual_replay_with_same_key_is_not_cached(client, data, ai, query):
    """快取會多存一份人工版，清除與匯出範圍外又多一份副本（#18 J7）。"""
    rid = generate_ok(client, ai)
    h = {"Idempotency-Key": "weekly-manual-1"}
    client.put(MANUAL.format(rid), json={"manual_text": f"第一版{MARK}"}, headers=h)
    again = client.put(MANUAL.format(rid), json={"manual_text": "第二版"}, headers=h)
    assert again.headers.get("Idempotent-Replay") is None
    assert again.json()["manual_text"] == "第二版"
    assert query("SELECT count(*) AS n FROM idempotency_keys")[0]["n"] == 0


# ---------- week_start（第 5 點、G7、J6）----------

@pytest.mark.parametrize("week", ["2026-11-10", "2026-11-08", "2026-11-16", "2026-11-9", "x", None])
def test_bad_week_start(client, week):
    r = client.post(DRAFT, json={"week_start": week})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["week_start"]


def test_missing_week_start(client):
    r = client.post(DRAFT, json={})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["week_start"]


def test_past_monday_ok_and_too_old_rejected(client):
    assert draft(client, "2026-11-02").status_code == 200
    r = draft(client, "2025-11-03")     # 早於今天前 365 天
    assert r.status_code == 422 and r.json()["error"]["code"] == "DATE_OUT_OF_RANGE"


@pytest.mark.parametrize(("now", "week", "status"), [
    (datetime(2026, 11, 15, 23, 59, tzinfo=TZ), "2026-11-16", 422),   # 台北週日晚上，下週一還不行
    (datetime(2026, 11, 16, 0, 30, tzinfo=TZ), "2026-11-16", 200),    # 台北週一 00:30（UTC 仍是週日）
])
def test_this_week_follows_taipei_clock(client, clock, now, week, status):
    clock.set(now)
    assert draft(client, week).status_code == status


# ---------- 認證（資安規則 1）----------

def test_requires_token_and_has_no_side_effect(app, data, query):
    from fastapi.testclient import TestClient
    with TestClient(app) as anon:
        assert anon.post(DRAFT, json={"week_start": WEEK}).status_code == 401
        assert anon.get(ONE.format(1), headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert rows(query) == []


# ---------- 第三段：AI-05 的 ai_runs 紀錄與重試（FR-AI-02、spec 5.14、#22、#18 K1～K8 預設）----------

TOKEN_LIKE = "sk-ant-機密標記XYZ-0000"


def runs(query):
    return query("SELECT node_id, job_id, status, attempt, latency_ms, raw_output, error FROM ai_runs ORDER BY id")


def statuses(query):
    return [(r["status"], r["attempt"]) for r in runs(query)]


def test_success_writes_one_run(client, data, ai, query):
    ai.script("AI-05", AI_OK)
    draft(client)
    [r] = runs(query)
    assert (r["node_id"], r["job_id"], r["status"], r["attempt"], r["error"], r["raw_output"]) == \
        ("AI-05", None, "ok", 1, None, None)   # K1：AI-05 不存 raw_output
    assert r["latency_ms"] >= 0


@pytest.mark.parametrize(("script", "expected", "final"), [
    ([AITimeout, AI_OK], [("timeout", 1), ("ok", 2)], "ok"),
    ([AIInvalidOutput, AI_OK], [("invalid_output", 1), ("ok", 2)], "ok"),
    ([{"items": []}, AI_OK], [("invalid_output", 1), ("ok", 2)], "ok"),            # 回傳物件驗證不過
    ([AITimeout, AIInvalidOutput, AI_OK], [("timeout", 1), ("invalid_output", 2), ("ok", 3)], "ok"),
    ([AIInvalidOutput] * 4, [("invalid_output", 1), ("invalid_output", 2), ("invalid_output", 3)], "invalid_output"),
    ([AITimeout] * 4, [("timeout", 1), ("timeout", 2), ("timeout", 3)], "unavailable"),
    ([AIInvalidOutput, AITimeout, AITimeout], [("invalid_output", 1), ("timeout", 2), ("timeout", 3)], "unavailable"),
    ([AIInvalidOutput, AIUnavailable], [("invalid_output", 1), ("error", 2)], "unavailable"),   # 不可用立刻停
    # 其他例外也算一次失敗、繼續重試；只有 AI 不可用立刻停（#22 Dev-B 對齊 process_sources；2026-11-17 修改）
    ([RuntimeError("x")] * 3, [("error", 1), ("error", 2), ("error", 3)], "unavailable"),
    ([RuntimeError("x"), AI_OK], [("error", 1), ("ok", 2)], "ok"),
    ([RuntimeError("x"), AIUnavailable], [("error", 1), ("error", 2)], "unavailable"),
])
def test_retry_sequences(client, data, ai, query, script, expected, final):
    ai.script("AI-05", *script)
    r = draft(client)
    assert r.status_code == 200 and r.json()["ai_status"] == final   # AC-50：失敗也 200
    assert statuses(query) == expected and len(ai.calls) == len(expected)
    if final != "ok":
        assert r.json()["draft"] is None and r.json()["validated"] is False


class ProviderDown(AIUnavailable):
    """真實供應商可能丟出的子類別（Phase 13）。"""


class ProviderSlow(AITimeout):
    pass


def test_exception_subclasses_follow_their_base_class(client, data, ai, query):
    """停不停、記什麼狀態依例外的類別階層判斷，不依名稱（與 process_sources 的 status_for 一致）。"""
    ai.script("AI-05", ProviderSlow, ProviderDown, AI_OK)
    assert draft(client).json()["ai_status"] == "unavailable"
    assert [(r["status"], r["error"]) for r in runs(query)] == [("timeout", "ProviderSlow"), ("error", "ProviderDown")]
    assert len(ai.calls) == 2


def test_unavailable_writes_one_error_run(client, data, ai, query):
    draft(client)   # 沒排輸出 → AIUnavailable
    assert [(r["status"], r["error"]) for r in runs(query)] == [("error", "AIUnavailable")]


def test_r4_mismatch_is_recorded_and_not_retried(client, data, ai, query):
    bad = {"draft": f"{MARK} 初稿", "items": [{"section": "delay", "task_id": 2, "event_id": 999}]}
    ai.script("AI-05", bad, AI_OK)
    r = draft(client)
    assert (r.json()["ai_status"], r.json()["validated"], r.json()["draft"]) == ("invalid_output", False, None)
    assert [(x["status"], x["error"]) for x in runs(query)] == [("invalid_output", "R4_MISMATCH")]   # K2
    assert len(ai.calls) == 1 and MARK not in r.text
    assert MARK not in json.dumps(rows(query), ensure_ascii=False, default=str)


def test_invalid_then_r4_mismatch_stops(client, data, ai, query):
    ai.script("AI-05", AIInvalidOutput, {"draft": "x", "items": [{"section": "done", "task_id": 1, "event_id": 21}]})
    assert draft(client).json()["ai_status"] == "invalid_output"
    assert [(x["status"], x["error"]) for x in runs(query)] == \
        [("invalid_output", "AIInvalidOutput"), ("invalid_output", "R4_MISMATCH")]


@pytest.mark.parametrize("exc", [AITimeout(TOKEN_LIKE), AIInvalidOutput(TOKEN_LIKE), AIUnavailable(TOKEN_LIKE),
                                 RuntimeError(TOKEN_LIKE)])
def test_error_column_and_log_carry_only_class_names(client, data, ai, query, caplog, exc):
    ai.script("AI-05", exc, exc, exc)
    r = draft(client)
    everything = json.dumps(runs(query), ensure_ascii=False, default=str)
    assert TOKEN_LIKE not in everything and TOKEN_LIKE not in caplog.text and TOKEN_LIKE not in r.text
    assert {x["error"] for x in runs(query)} == {type(exc).__name__}


def test_no_log_of_titles_or_draft_on_failures(client, data, ai, caplog):
    ai.script("AI-05", AIInvalidOutput, {"draft": MARK, "items": [{"section": "next", "task_id": 4, "event_id": None}]})
    draft(client)
    assert "本週完成" not in caplog.text and MARK not in caplog.text


@pytest.mark.parametrize("bad_draft", ["", "   ", "字" * 20_001, "本週\x00進度"])   # NUL 會讓存檔失敗
def test_draft_bounds(client, data, ai, query, bad_draft):
    out = {"draft": bad_draft, "items": AI_ITEMS}
    ai.script("AI-05", out, out, out)
    assert draft(client).json()["ai_status"] == "invalid_output"   # K8


@pytest.mark.parametrize("output", [
    {"draft": "x", "items": [{"section": "later", "task_id": 1, "event_id": 11}]},
    {"draft": "x", "items": [{"section": "done", "task_id": 1, "event_id": None}]},
    {"draft": "x", "items": [{"section": "next", "task_id": 3, "event_id": 11}]},
    {"draft": "x", "items": ["not an object"]},
    {"draft": "x"},
    ["not", "an", "object"],
])
def test_more_malformed_outputs(client, data, ai, query, output):
    ai.script("AI-05", output, output, output)
    assert draft(client).json()["ai_status"] == "invalid_output"
    assert [x["status"] for x in runs(query)] == ["invalid_output"] * 3   # 結構錯誤會重試（spec 5.14）


def test_attempts_restart_per_request(client, data, ai, query):
    ai.script("AI-05", AITimeout, AI_OK, AI_OK)
    draft(client)
    draft(client)
    assert statuses(query) == [("timeout", 1), ("ok", 2), ("ok", 1)]


def test_payload_whitelist_and_same_on_every_attempt(client, data, ai, seed):
    seed("UPDATE tasks SET title = '本週完成（改名）' WHERE id = 1;")   # 事件快照仍是舊標題
    snapshots = []

    class Recording(FakeAIClient):
        def call(self, node_id, payload, **kw):
            snapshots.append(copy.deepcopy(payload))
            return super().call(node_id, payload, **kw)

    rec = Recording()
    rec.script("AI-05", AITimeout, AI_OK)
    client.app.state.ai = rec
    draft(client)
    assert len(snapshots) == 2 and snapshots[0] == snapshots[1]
    p = snapshots[0]
    assert set(p) == {"week", "done", "delay", "next"} and p["week"] == {"start": "2026-11-09", "end": "2026-11-15"}
    assert all(set(i) == {"task_id", "title", "owner", "done_date", "event_id"} for i in p["done"])
    assert all(set(i) == {"task_id", "title", "owner", "orig_due", "latest_due", "event_ids"} for i in p["delay"])
    assert all(set(i) == {"task_id", "title", "owner", "latest_due", "blocked"} for i in p["next"])
    assert p["done"][0]["title"] == "本週完成（改名）"
    assert "私人機密任務" not in json.dumps(p, ensure_ascii=False)


def test_uses_default_timeout(client, data):
    seen = []

    class Timing(FakeAIClient):
        def call(self, node_id, payload, *, timeout_s=DEFAULT_TIMEOUT_S):
            seen.append(timeout_s)
            return AI_OK

    client.app.state.ai = Timing()
    draft(client)
    assert seen == [20.0]   # FR-AI-05


def test_rejected_requests_never_call_ai(app, client, data, ai, query):
    from fastapi.testclient import TestClient
    with TestClient(app) as anon:
        anon.post(DRAFT, json={"week_start": WEEK})
    client.post(DRAFT, json={"week_start": "2026-11-10"})
    rid = draft(client).json()["id"]
    before = len(ai.calls)
    client.get(ONE.format(rid))
    client.put(MANUAL.format(rid), json={"manual_text": "x"})
    assert len(ai.calls) == before == 1 and len(runs(query)) == 1


# ---------- 第四段：按週讀取與 items 可讀內容（2026-11-17 產品負責人裁定，#23；AC-66）----------

WEEKLY = "/api/v1/reports/weekly"
ITEM_KEYS = {"section", "task_id", "event_id", "title", "owner", "done_date", "orig_due", "latest_due",
             "blocked", "event"}
EVENT_KEYS = {"id", "ts", "from_value", "to_value", "delta_days"}
DONE_1 = {"section": "done", "task_id": 1, "event_id": 11, "title": "本週完成", "owner": "我",
          "done_date": "2026-11-10", "orig_due": None, "latest_due": None, "blocked": None,
          "event": {"id": 11, "ts": "2026-11-10T18:00:00+08:00", "from_value": "todo", "to_value": "done",
                    "delta_days": None}}
DELAY_2 = {"section": "delay", "task_id": 2, "event_id": 21, "title": "延期任務", "owner": "小薇",
           "done_date": None, "orig_due": "2026-11-12", "latest_due": "2026-11-15", "blocked": None,
           "event": {"id": 21, "ts": "2026-11-10T10:00:00+08:00", "from_value": "2026-11-12",
                     "to_value": "2026-11-15", "delta_days": 3}}


def next_item(task_id, title, owner, latest_due, blocked=False):
    return {"section": "next", "task_id": task_id, "event_id": None, "title": title, "owner": owner,
            "done_date": None, "orig_due": None, "latest_due": latest_due, "blocked": blocked, "event": None}


NEXT_3 = next_item(3, "下週到期", "我", "2026-11-18")
NEXT_2 = next_item(2, "延期任務", "小薇", "2026-11-15")


def by_week(client, week=WEEK):
    return client.get(WEEKLY, params={"week_start": week})


def assert_shape(body):
    """每個 item 的鍵集合完全相等；不屬於該段的欄位為 null；event 只有五個鍵（5.14 表）。"""
    for item in body["items"]:
        assert set(item) == ITEM_KEYS
        section = item["section"]
        assert (item["done_date"] is not None) == (section == "done")
        assert (item["orig_due"] is not None) == (section == "delay")
        assert (item["latest_due"] is not None) == (section in ("delay", "next"))
        assert (item["blocked"] is not None) == (section == "next")
        assert (item["event"] is not None) == (section in ("done", "delay"))
        if item["event"] is not None:
            assert set(item["event"]) == EVENT_KEYS and item["event"]["id"] == item["event_id"]


def ai_runs_count(query):
    return query("SELECT count(*) AS n FROM ai_runs")[0]["n"]


# 缺口 1：按週讀取

def test_by_week_returns_same_report_as_by_id_without_calling_ai(client, data, ai, query):
    rid = generate_ok(client, ai)
    before = (rows(query), ai_runs_count(query), len(ai.calls))
    r = by_week(client)
    assert r.status_code == 200 and r.json() == client.get(ONE.format(rid)).json()
    assert {i["section"] for i in r.json()["items"]} == {"done", "delay", "next"}   # 三段都有內容才算比對
    assert (rows(query), ai_runs_count(query), len(ai.calls)) == before


@pytest.mark.parametrize("week", ["2026-11-02", "9999-12-27", "0001-01-01"])
def test_by_week_not_generated_is_404(client, data, week):
    r = by_week(client, week)
    assert r.status_code == 404
    assert (r.json()["error"]["code"], r.json()["error"]["details"]) == ("NOT_FOUND", {"week_start": week})


def test_by_week_reads_only_weekly_rows(client, seed):
    seed(f"INSERT INTO reports (id, kind, period_start, created_at, updated_at) "
         f"VALUES (50, 'goal', '{WEEK}', now(), now());")
    assert by_week(client).status_code == 404


# 格式錯誤由框架驗證，fields 沿用查詢參數的既有錯誤格式 query.<名稱>（error_handlers）；
# 是日期但不是星期一由 domain 檢查，fields 為 week_start（與 POST draft 同一個 check_monday）。
@pytest.mark.parametrize(("week", "field"), [("2026-11-10", "week_start"), ("2026-02-30", "query.week_start"),
                                             ("2026/11/09", "query.week_start"), ("20261109", "query.week_start"),
                                             ("abc", "query.week_start")])
def test_by_week_bad_week_start(client, data, week, field):
    r = by_week(client, week)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["details"] == {"fields": [field]} and week not in r.text   # 不回顯輸入


def test_by_week_missing_week_start(client):
    r = client.get(WEEKLY)
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["query.week_start"]}


@pytest.mark.parametrize("change", [
    "UPDATE tasks SET scope = 'private' WHERE id = 2;",
    "UPDATE tasks SET orig_due = '2026-11-15' WHERE id = 2;"
    "INSERT INTO events (ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, mine) "
    "VALUES ('2026-11-11T11:00+08:00', 1, 2, '延期任務', 'baseline', 'orig_due', '2026-11-12', '2026-11-15', "
    "'baseline_correction', false);",
])
def test_by_week_revalidates_and_never_calls_ai(client, data, ai, seed, change):
    generate_ok(client, ai)
    seed(change)
    body = by_week(client).json()
    assert (body["validated"], body["draft"]) == (False, None) and len(ai.calls) == 1
    assert_shape(body)


def test_by_week_hides_task_turned_private(client, data, ai, seed):
    generate_ok(client, ai)
    seed("UPDATE tasks SET scope = 'private' WHERE id = 2;")
    r = by_week(client)
    assert all(i["task_id"] != 2 and i["event_id"] != 21 for i in r.json()["items"])
    assert "延期任務" not in r.text and "小薇" not in r.text


def test_by_week_picks_the_requested_week(client, data, ai):
    ai.script("AI-05", AI_OK)
    rid = draft(client).json()["id"]
    other = draft(client, "2026-11-02").json()["id"]
    assert rid != other
    assert (by_week(client).json()["id"], by_week(client, "2026-11-02").json()["id"]) == (rid, other)


def test_by_week_after_first_failure_returns_fallback(client, data):
    draft(client)   # AI 不可用：建一列，AI 欄位為 null
    body = by_week(client).json()
    assert (body["ai_status"], body["validated"], body["draft"]) == ("unavailable", False, None)
    assert body["items"] == [DONE_1, DELAY_2, NEXT_2, NEXT_3]


def test_by_week_after_failed_regenerate_keeps_previous_success(client, data, ai):
    generate_ok(client, ai)
    assert draft(client).json()["validated"] is False   # 重新產生時不可用（H2）
    body = by_week(client).json()
    assert (body["ai_status"], body["validated"], body["draft"]) == ("ok", True, AI_OK["draft"])
    assert body["items"] == [DONE_1, DELAY_2, NEXT_3]


def test_by_week_requires_token(app, client, data, ai):
    from fastapi.testclient import TestClient
    generate_ok(client, ai)
    with TestClient(app) as anon:
        r = anon.get(WEEKLY, params={"week_start": WEEK})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"
    assert "本週完成" not in r.text and WEEK not in r.text


def test_by_week_errors_and_fallback_log_no_content(client, data, caplog):
    by_week(client, "2026-11-02")
    by_week(client, "2026-11-10")
    draft(client)
    by_week(client)
    for text_ in ("本週完成", "延期任務", "下週到期", "小薇", MARK):
        assert text_ not in caplog.text


# 缺口 2：items 可讀內容

def test_ai_items_carry_readable_fields_on_every_endpoint(client, data, ai):
    ai.script("AI-05", AI_OK)
    posted = draft(client).json()
    rid = posted["id"]
    for body in (posted, client.get(ONE.format(rid)).json(), by_week(client).json(),
                 client.put(MANUAL.format(rid), json={"manual_text": "人工版"}).json()):
        assert body["validated"] is True and body["items"] == [DONE_1, DELAY_2, NEXT_3]
        assert_shape(body)


def test_fallback_items_carry_readable_fields(client, data):
    body = draft(client).json()
    assert body["items"] == [DONE_1, DELAY_2, NEXT_2, NEXT_3]
    assert_shape(body)


def test_readable_fields_follow_current_values(client, data, ai, seed):
    rid = generate_ok(client, ai)
    seed("UPDATE tasks SET title = '新標題', owner_name = '阿德' WHERE id = 1;"
         "UPDATE tasks SET latest_due = '2026-11-17' WHERE id = 2;"   # 仍延期，但與事件的後值不同
         "UPDATE tasks SET blocked = true WHERE id = 3;")
    body = client.get(ONE.format(rid)).json()
    assert body["validated"] is True
    done, delay, nxt = body["items"]
    assert (done["title"], done["owner"]) == ("新標題", "阿德")
    assert (delay["latest_due"], delay["event"]["to_value"]) == ("2026-11-17", "2026-11-15")
    assert nxt["blocked"] is True


def test_next_drift_shows_current_due(client, data, ai, seed):
    rid = generate_ok(client, ai)
    seed("UPDATE tasks SET latest_due = '2026-12-30' WHERE id = 3;")
    body = client.get(ONE.format(rid)).json()
    assert body["validated"] is True and body["items"][2] == next_item(3, "下週到期", "我", "2026-12-30")


LEAK = f"""
INSERT INTO sources (id, channel, speaker, excerpt, excerpt_hash, received_at, expires_at)
  VALUES (1, 'paste', '阿德', '{MARK} 原句', 'h-leak', now(), now() + interval '30 days');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    source_id, reason, note, delta_days, mine, extra) VALUES
  (22, '2026-11-11T09:00+08:00', 1, 2, '延期任務', 'due', 'latest_due', '2026-11-15', '2026-11-16', 'candidate',
   1, '{MARK} 原因', '{MARK} 備註', 1, false, '{{"x": "{MARK}"}}');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    reason, note, mark, mine, ref_event_id) VALUES
  (23, '2026-11-11T10:00+08:00', 1, 2, '延期任務', 'annotation', 'mark', NULL, 'worse', 'manual',
   '{MARK} 註記原因', '{MARK} 註記備註', 'worse', false, 22),
  (24, '2026-11-11T11:00+08:00', 1, 1, '本週完成', 'feedback', 'feedback', NULL, '{MARK} 回報', 'manual',
   NULL, '{MARK} 回報備註', NULL, true, NULL);
UPDATE tasks SET latest_due = '2026-11-16', done_when = '{MARK} 完成條件' WHERE id = 2;
"""


def test_no_evaluation_fields_or_source_text_on_any_path(client, data, ai, seed):
    seed(LEAK)
    fallback = draft(client)                       # AI 不可用：退路清單含事件 22
    assert {i["event_id"] for i in fallback.json()["items"]} >= {11, 21, 22}
    assert all(i["event_id"] not in (23, 24) for i in fallback.json()["items"])
    ai.script("AI-05", {"draft": "x", "items": [*AI_ITEMS, {"section": "delay", "task_id": 2, "event_id": 22}]})
    posted = draft(client)
    rid = posted.json()["id"]
    responses = [fallback, posted, client.get(ONE.format(rid)), by_week(client),
                 client.put(MANUAL.format(rid), json={"manual_text": "x"})]
    assert posted.json()["validated"] is True
    for r in responses:
        assert MARK not in r.text
        assert_shape(r.json())
        for item in r.json()["items"]:
            if item["section"] == "done":
                assert item["event"]["to_value"] == "done"


def test_standalone_task_carries_readable_fields(client, data, seed):
    seed("INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, status, "
         "done_date, blocked, version, created_at, updated_at) VALUES (5, NULL, '單點完成', '阿德', 'work', "
         "'2026-11-01', '2026-11-11', '2026-11-11', 'done', '2026-11-11', false, 2, now(), now());"
         "INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, mine) "
         "VALUES (12, '2026-11-11T09:00+08:00', NULL, 5, '單點完成', 'status', 'status', 'doing', 'done', 'manual', false);")
    item = next(i for i in draft(client).json()["items"] if i["task_id"] == 5)
    assert (item["title"], item["owner"], item["done_date"], item["event"]["from_value"]) == \
        ("單點完成", "阿德", "2026-11-11", "doing")


def test_task_turned_private_during_ai_call_is_not_listed(client, data, db):
    """失敗路徑的退路清單用呼叫 AI 前的彙整；AI 呼叫期間任務改成私人，回應不能帶出它的事件證據（code-review）。"""
    class Racing(FakeAIClient):
        def call(self, node_id, payload, **kw):
            db.run(lambda c: c.execute(text("UPDATE tasks SET scope = 'private' WHERE id = 2")))
            raise AIUnavailable("down")
    client.app.state.ai = Racing()
    r = draft(client)
    assert r.status_code == 200 and r.json()["validated"] is False
    assert all(i["task_id"] != 2 for i in r.json()["items"])
    assert "2026-11-12" not in r.text and "小薇" not in r.text
