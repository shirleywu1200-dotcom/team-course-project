"""Phase 8：設定、量表、原文清除與匯出（AC-52～54，todo 8.1～8.7）。AI 一律 FakeAIClient。"""

import json
from datetime import datetime

from app import scheduler
from app.ai.client import AITimeout
from app.clock import TZ
from tests.unit.seeds import BASE, RUBRIC

API = "/api/v1"
NODE = "AI-06"
LEVELS = ["沒交付", "交了一部分", "照約定交付", "交付且品質好", "超出範圍且品質突出"]
ANSWERS = {"q1": "交付完成且品質達標", "q2": "超出範圍或品質明顯突出", "q3": "否，同一套標準"}

# 1 已過期、2 未過期、3 早已清除；各有事件與候選指向它
SOURCES = """
INSERT INTO sources (id, channel, speaker, spoken_at, excerpt, excerpt_hash, received_at, expires_at, purged_at) VALUES
  (1, 'paste', '阿德', '10:12', '畫面規格 v1 確定延到 11/18', 'h1', '2026-10-01T10:00+08:00', '2026-10-31T10:00+08:00', NULL),
  (2, 'paste', '小薇', '10:20', '報表處理我來', 'h2', '2026-11-01T10:00+08:00', '2026-12-01T10:00+08:00', NULL),
  (3, 'paste', '阿德', '09:00', NULL, 'h3', '2026-09-01T10:00+08:00', '2026-10-01T10:00+08:00',
      '2026-10-01T11:00+08:00');
INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, state, created_at) VALUES
  (21, 1, 'delay', 'sure', 2, '{"new_due":"2026-11-18"}', 'open', '2026-10-01T10:00+08:00'),
  (22, 2, 'done', 'sure', 3, NULL, 'open', '2026-11-01T10:00+08:00');
INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin, origin_ref,
                    source_id) VALUES
  (1, '2026-10-01T10:05+08:00', 1, 2, '畫面規格 v1', 'due', 'latest_due', '2026-11-13', '2026-11-18',
      'candidate', 21, 1);
INSERT INTO idempotency_keys (key, endpoint, response, created_at) VALUES
  ('old', 'POST /api/v1/candidates/21/confirm', '{"status":200,"body":{"quote":"畫面規格"}}', '2026-11-10T09:00+08:00'),
  ('new', 'POST /api/v1/candidates/22/confirm', '{"status":200,"body":{"quote":"報表"}}', '2026-11-11T09:00+08:00');
"""


def count(query, table):
    return query(f"SELECT count(*) AS n FROM {table}")[0]["n"]  # noqa: S608 測試固定表名


def excerpts(query):
    return {r["id"]: (r["excerpt"], r["purged_at"]) for r in query("SELECT id, excerpt, purged_at FROM sources")}


# ---------- 設定（8.1） ----------

def test_get_settings_creates_single_default_row(client, query):
    r = client.get(f"{API}/settings")
    assert r.status_code == 200
    body = r.json()
    assert (body["retention_days"], body["confirm_time"], body["default_scope"], body["onboarded_at"]) == (
        30, "18:00", "work", None)
    assert body["energy_def_high"] == "需要整段專注，做完會明顯疲累"
    assert body["goal_types_enabled"] == ["growth", "time", "expectation"]
    assert "id" not in body
    client.get(f"{API}/settings")
    assert count(query, "settings") == 1


def test_put_settings_updates_only_given_fields(client):
    r = client.put(f"{API}/settings", json={"confirm_time": "21:00", "goal_types_enabled": ["growth"]})
    assert r.status_code == 200
    body = r.json()
    assert (body["confirm_time"], body["goal_types_enabled"], body["confirm_cap_min"]) == ("21:00", ["growth"], 5)
    assert client.get(f"{API}/settings").json()["confirm_time"] == "21:00"


def test_put_settings_rejects_invalid_values(client):
    before = client.get(f"{API}/settings").json()
    for bad in ({"confirm_time": "19:00"}, {"retention_days": 60}, {"foo": 1},
                {"goal_types_enabled": ["growth", "growth"]}, {"goal_types_enabled": ["fun"]},
                {"energy_def_low": "  "}, {"energy_def_low": "字" * 201}):
        r = client.put(f"{API}/settings", json=bad)
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get(f"{API}/settings").json() == before


def test_shorter_retention_recomputes_expiry_and_purges_now(client, seed, query, clock):
    seed(BASE + SOURCES)
    client.put(f"{API}/settings", json={"retention_days": 90})
    rows = {r["id"]: r for r in query("SELECT id, expires_at, excerpt FROM sources")}
    assert rows[1]["expires_at"] == datetime(2026, 12, 30, 10, 0, tzinfo=TZ) and rows[1]["excerpt"]
    assert rows[3]["expires_at"] == datetime(2026, 10, 1, 10, 0, tzinfo=TZ)   # 已清除的不重算

    client.put(f"{API}/settings", json={"retention_days": 30})
    got = excerpts(query)
    assert got[1] == (None, clock.now())                  # 10/01 + 30 天已過，立刻清除
    assert got[2][0] == "報表處理我來"                     # 11/01 + 30 天未到
    assert count(query, "idempotency_keys") == 0           # 快取裡的原句一併清掉
    assert count(query, "events") == 1 and count(query, "candidates") == 2


def test_onboarding_complete_sets_time_once_and_ensures_v0(client, query, clock):
    r = client.post(f"{API}/settings/onboarding/complete", json={"skipped": True})
    assert r.status_code == 200
    first = r.json()["onboarded_at"]
    assert first is not None
    assert query("SELECT version, source FROM rubrics") == [{"version": 0, "source": "default"}]
    clock.set(datetime(2026, 11, 12, 9, 0))
    assert client.post(f"{API}/settings/onboarding/complete", json={"skipped": False}).json()["onboarded_at"] == first


# ---------- 量表（8.2～8.4） ----------

def test_rubrics_default_v0_and_active(client):
    body = client.get(f"{API}/rubrics").json()
    assert body["total"] == 1
    [v0] = body["items"]
    assert (v0["version"], v0["source"], v0["levels"]) == (
        0, "default", ["未達成", "部分達成", "符合預設", "優於預設", "遠超預設"])
    assert client.get(f"{API}/rubrics", params={"active": True}).json()["items"] == [v0]


def test_interview_returns_draft_and_sends_only_answers_and_current(client, seed, ai, query):
    seed(BASE + RUBRIC + SOURCES)
    ai.script(NODE, {"levels": LEVELS, "reason": "丟棄"})
    r = client.post(f"{API}/rubrics/interview", json=ANSWERS)
    assert r.status_code == 200
    assert r.json() == {"ai_status": "ok", "draft": LEVELS}
    [(node, payload)] = ai.calls
    assert node == NODE
    assert payload == ANSWERS | {"current": ["未達成", "部分達成", "符合預設", "優於預設", "遠超預設"]}
    [run] = query("SELECT node_id, status, raw_output FROM ai_runs")
    assert (run["node_id"], run["status"]) == (NODE, "ok") and "交付且品質好" in run["raw_output"]
    assert count(query, "rubrics") == 1                    # 草稿不入庫


def test_interview_retries_bad_output_then_succeeds(client, seed, ai, query):
    seed(RUBRIC)
    ai.script(NODE, {"levels": LEVELS[:4]}, AITimeout, {"levels": LEVELS[:4] + [" "]}, {"levels": LEVELS})
    r = client.post(f"{API}/rubrics/interview", json=ANSWERS)
    assert r.status_code == 503                            # 3 次都失敗，第 4 個不會被叫到
    assert r.json()["error"]["code"] == "AI_UNAVAILABLE"
    assert [x["status"] for x in query("SELECT status FROM ai_runs ORDER BY id")] == [
        "invalid_output", "timeout", "invalid_output"]

    r = client.post(f"{API}/rubrics/interview", json=ANSWERS)
    assert r.status_code == 200 and r.json()["draft"] == LEVELS


def test_interview_unavailable_is_503_without_retry(client, seed, query):
    seed(RUBRIC)
    r = client.post(f"{API}/rubrics/interview", json=ANSWERS)
    assert r.status_code == 503
    assert [x["status"] for x in query("SELECT status FROM ai_runs")] == ["error"]
    assert count(query, "rubrics") == 1


def test_interview_rejects_empty_answer(client, seed, ai):
    seed(RUBRIC)
    assert client.post(f"{API}/rubrics/interview", json=ANSWERS | {"q2": ""}).status_code == 422
    assert ai.calls == []


def test_confirm_creates_next_version_and_keeps_old(client, seed, query):
    seed(RUBRIC)
    r = client.post(f"{API}/rubrics", json={"levels": LEVELS, "interview": ANSWERS})
    assert r.status_code == 201
    assert r.json()["version"] == 1
    rows = query("SELECT version, levels, source, interview FROM rubrics ORDER BY version")
    assert rows[0]["levels"] == ["未達成", "部分達成", "符合預設", "優於預設", "遠超預設"]
    assert (rows[1]["levels"], rows[1]["source"], rows[1]["interview"]) == (LEVELS, "interview", ANSWERS)
    assert client.get(f"{API}/rubrics", params={"active": True}).json()["items"][0]["version"] == 1
    assert client.post(f"{API}/rubrics", json={"levels": LEVELS, "interview": ANSWERS}).json()["version"] == 2


def test_confirm_requires_exactly_five_non_empty_levels(client, seed, query):
    seed(RUBRIC)
    for bad in (LEVELS[:4], LEVELS + ["多一句"], LEVELS[:4] + [""], LEVELS[:4] + ["字" * 201]):
        r = client.post(f"{API}/rubrics", json={"levels": bad, "interview": ANSWERS})
        assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "rubrics") == 1


def test_confirm_records_ai_feedback_when_draft_given(client, seed, query):
    seed(RUBRIC)
    client.post(f"{API}/rubrics", json={"levels": LEVELS, "interview": ANSWERS | {"draft": LEVELS}})
    edited = ["改過"] + LEVELS[1:]
    client.post(f"{API}/rubrics", json={"levels": edited, "interview": ANSWERS | {"draft": LEVELS}})
    client.post(f"{API}/rubrics", json={"levels": LEVELS, "interview": ANSWERS})
    rows = query("SELECT node_id, target_type, target_id, outcome FROM ai_feedback ORDER BY id")
    ids = [r["id"] for r in query("SELECT id FROM rubrics WHERE version > 0 ORDER BY version")]
    assert rows == [{"node_id": NODE, "target_type": "rubric", "target_id": ids[0], "outcome": "accepted"},
                    {"node_id": NODE, "target_type": "rubric", "target_id": ids[1], "outcome": "edited"}]
    assert "draft" not in query("SELECT interview FROM rubrics WHERE version = 1")[0]["interview"]


# ---------- 到期清除（8.5，AC-52） ----------

def test_ac52_scheduled_purge_clears_only_expired_excerpts(db, seed, query, clock):
    seed(BASE + SOURCES)
    assert scheduler.run_once(db) == 1
    got = excerpts(query)
    assert got[1] == (None, clock.now())
    assert got[2] == ("報表處理我來", None)
    assert got[3] == (None, datetime(2026, 10, 1, 11, 0, tzinfo=TZ))
    assert count(query, "events") == 1 and count(query, "candidates") == 2
    assert count(query, "idempotency_keys") == 0           # 快取可能含剛清掉的原句，全部刪除
    assert scheduler.run_once(db) == 0                    # 冪等


def test_purge_without_expired_sources_only_drops_stale_cache(db, seed, query):
    seed(BASE + SOURCES.replace("'2026-10-31T10:00+08:00', NULL", "'2026-12-31T10:00+08:00', NULL"))
    assert scheduler.run_once(db) == 0
    assert [r["key"] for r in query("SELECT key FROM idempotency_keys")] == ["new"]   # 只刪超過 24 小時的


# ---------- 刪除所有原文（8.6，AC-53） ----------

def test_ac53_purge_all_requires_confirm_true(client, seed, query):
    seed(BASE + SOURCES)
    before = excerpts(query)
    for bad in ({}, {"confirm": False}, {"confirm": "true"}, {"confirm": 1}):
        r = client.post(f"{API}/sources/purge", json=bad)
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert excerpts(query) == before
    assert count(query, "idempotency_keys") == 2


def test_ac53_purge_all_clears_every_excerpt_and_idempotency_cache(client, seed, query, clock):
    seed(BASE + SOURCES)
    r = client.post(f"{API}/sources/purge", json={"confirm": True})
    assert r.status_code == 200 and r.json() == {"purged": 2}
    got = excerpts(query)
    assert all(e is None for e, _ in got.values())
    assert got[1][1] == clock.now() and got[3][1] == datetime(2026, 10, 1, 11, 0, tzinfo=TZ)
    assert count(query, "idempotency_keys") == 0
    assert count(query, "events") == 1 and count(query, "candidates") == 2
    quote = client.get(f"{API}/candidates").json()["items"][0]["quote"]
    assert quote is None


# ---------- 匯出（8.7，AC-54） ----------

def test_ac54_export_contains_every_table_with_matching_counts(client, seed, query):
    seed(BASE + RUBRIC + SOURCES)
    r = client.post(f"{API}/export")
    assert r.status_code == 200
    assert r.headers["content-disposition"] == 'attachment; filename="export-20261111-100000.json"'
    data = json.loads(r.content)
    tables = [t["table_name"] for t in query(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
        "AND table_type = 'BASE TABLE' AND table_name <> 'alembic_version'")]
    assert len(tables) == 17
    assert sorted(data["tables"]) == sorted(tables) == sorted(data["counts"])
    for t in tables:
        assert len(data["tables"][t]) == data["counts"][t] == count(query, t), t
    src = {s["id"]: s for s in data["tables"]["sources"]}
    assert src[3]["excerpt"] is None and src[1]["received_at"] == "2026-10-01T10:00:00+08:00"
    assert data["tables"]["rubrics"][0]["levels"][0] == "未達成"
    assert data["schema_version"] and data["exported_at"] == "2026-11-11T10:00:00+08:00"
    # 連線池重用連線（pool_pre_ping 會先送 SELECT 1）時，快照設定仍須是交易第一句
    client.get(f"{API}/settings")
    assert client.post(f"{API}/export").status_code == 200


def test_export_is_not_stored_in_idempotency_cache(client, seed, query):
    seed(BASE + SOURCES)
    r = client.post(f"{API}/export", headers={"Idempotency-Key": "exp-1"})
    assert r.status_code == 200
    assert [k["key"] for k in query("SELECT key FROM idempotency_keys ORDER BY key")] == ["new", "old"]
