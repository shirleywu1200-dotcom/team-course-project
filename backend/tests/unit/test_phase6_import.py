"""Phase 6：專案匯入端點（AC-30～33、55，todo 6.1～6.7）。AI-07 一律 FakeAIClient。"""

import time

import pytest

from app.ai.client import AITimeout
from app.domain.imports import service
from tests.unit.seeds import BASE, RUBRIC

PREVIEW = "/api/v1/projects/import/preview"
COMMIT = "/api/v1/projects/import/commit"
NODE = "AI-07"
PRIVATE_PROJECT = """
INSERT INTO projects (id, name, scope, audience, created_at, updated_at, archived_at) VALUES
  (3, '私人專案', 'private', 'none', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00', NULL),
  (4, '已封存', 'work', 'manager', '2026-11-01T09:00+08:00', '2026-11-01T09:00+08:00', '2026-11-05T09:00+08:00');
"""
# AC-30：7 列，缺結束、結束早於開始各 1；重複名稱、缺負責人各 1
AC30 = "\n".join([
    "任務,負責人,開始,結束",
    "需求確認,我,11/16,11/18",
    "畫面規格,阿德,11/16,",
    "API 定義,小薇,11/20,11/18",
    "需求確認,阿德,11/17,11/19",
    "測試計畫,,11/20,11/25",
    "部署,我,11/26,11/28",
    "驗收,我,11/28,11/30",
])


def count(query, table):
    return query(f"SELECT count(*) AS n FROM {table}")[0]["n"]  # noqa: S608 測試固定表名


def test_ac30_preview_diagnoses_blocking_and_warnings(client, seed, ai, query):
    seed(BASE)
    r = client.post(PREVIEW, json={"text": AC30, "target": "new", "new_name": "新專案"})
    assert r.status_code == 200
    body = r.json()
    assert body["column_map"] == {"title": 0, "owner": 1, "start": 2, "end": 3, "mapped_by": "rule"}
    assert body["summary"] == {"importable": 5, "blocking": 2}
    blocking = {row["index"] for row in body["rows"] if row["blocking"]}
    assert blocking == {1, 2}
    assert [i["code"] for i in body["rows"][3]["issues"]] == ["DUPLICATE_TITLE"]
    assert body["rows"][4]["owner"] == "我" and body["rows"][4]["issues"][0]["level"] == "warn"
    assert ai.calls == []   # 規則能對應就不叫 AI（AC-33）
    assert count(query, "tasks") == 7 and count(query, "projects") == 2   # preview 不寫入


def test_ac33_nonstandard_header_calls_ai(client, seed, ai, query):
    seed(BASE)
    ai.script(NODE, {"title": 0, "owner": 1, "start": 2, "end": 3, "reason": "忽略"})
    r = client.post(PREVIEW, json={"text": "工項,PIC,起,交期\n需求確認,我,11/16,11/18"})
    body = r.json()
    assert body["column_map"]["mapped_by"] == "ai" and body["summary"]["importable"] == 1
    assert ai.calls[0][1] == {"headers": ["工項", "PIC", "起", "交期"], "samples": [["需求確認", "我", "11/16", "11/18"]]}
    assert query("SELECT node_id, status FROM ai_runs") == [{"node_id": "AI-07", "status": "ok"}]


@pytest.mark.parametrize("script", [[], [AITimeout], [{"title": 0, "end": 0}]])
def test_ac33_ai_unavailable_or_invalid_returns_null_mapping(client, seed, ai, script):
    seed(BASE)
    ai.script(NODE, *script)
    body = client.post(PREVIEW, json={"text": "工項,PIC,起,交期\n需求確認,我,11/16,11/18"}).json()
    assert body["column_map"]["mapped_by"] is None and body["ai_status"] in ("unavailable", "invalid_output")
    assert body["column_map"]["owner"] == 1   # 規則已對應的欄位保留
    assert body["rows"] == [] and body["header"] == ["工項", "PIC", "起", "交期"]


def test_manual_column_map_skips_rule_and_ai(client, seed, ai):
    seed(BASE)
    r = client.post(PREVIEW, json={"text": "工項,PIC,起,交期\n需求確認,我,11/16,11/18",
                                   "column_map": {"title": 0, "owner": 1, "start": 2, "end": 3}})
    assert r.json()["column_map"]["mapped_by"] == "manual" and ai.calls == []
    bad = client.post(PREVIEW, json={"text": "a,b\nx,11/18", "column_map": {"title": 0, "end": 5}})
    assert bad.status_code == 422


def test_private_project_never_calls_ai(client, seed, ai):
    seed(BASE + PRIVATE_PROJECT)
    ai.script(NODE, {"title": 0, "end": 3})
    body = client.post(PREVIEW, json={"text": "工項,PIC,起,交期\n需求確認,我,11/16,11/18", "target": 3}).json()
    assert body["column_map"]["mapped_by"] is None and ai.calls == []


def test_preview_payload_too_large(client, seed):
    seed(BASE)
    r = client.post(PREVIEW, json={"text": "任務,結束\n" + "a,11/20\n" * 501})
    assert r.status_code == 413


# ---------- commit ----------

def rows_from(preview_body):
    return [{k: row[k] for k in ("index", "title", "owner", "start", "end")} | {"skip": row["blocking"]}
            for row in preview_body["rows"]]


def test_ac31_commit_with_unskipped_error_rows_is_rejected(client, seed, query):
    seed(BASE)
    rows = rows_from(client.post(PREVIEW, json={"text": AC30}).json())
    for r in rows:
        r["skip"] = False
    resp = client.post(COMMIT, json={"target": "new", "new_name": "新專案", "rows": rows})
    assert resp.status_code == 422 and resp.json()["error"]["details"]["rows"] == [1, 2]
    assert count(query, "tasks") == 7 and count(query, "projects") == 2 and count(query, "events") == 0


def test_commit_does_not_trust_client_blocking_flags(client, seed):
    seed(BASE)
    rows = [{"index": 0, "title": "a", "owner": "我", "start": "2026-11-20", "end": "2026-11-18"}]
    assert client.post(COMMIT, json={"target": 1, "rows": rows}).status_code == 422


def test_ac32_commit_new_project_creates_tasks_and_one_baseline_event(client, seed, query):
    seed(BASE + RUBRIC)
    rows = rows_from(client.post(PREVIEW, json={"text": AC30}).json())
    r = client.post(COMMIT, json={"target": "new", "new_name": "會員系統 3.0", "rows": rows})
    assert r.status_code == 201
    body = r.json()
    assert (body["created"], body["skipped"]) == (5, 2)
    tasks = query("SELECT title, owner_name, start_date, orig_due, latest_due, star_source, scope, rubric_id "
                  "FROM tasks WHERE project_id = :p ORDER BY id", p=body["project_id"])
    assert len(tasks) == 5
    first = tasks[0]
    assert first["orig_due"] == first["latest_due"] and first["orig_due"].isoformat() == "2026-11-18"
    assert {t["star_source"] for t in tasks} == {"import_default"}
    assert tasks[3]["owner_name"] == "我" and tasks[0]["rubric_id"] == 2   # RUBRIC（version 1）為目前量表
    [ev] = query("SELECT id, kind, field, origin, task_id, to_value, extra FROM events WHERE kind = 'baseline'")
    assert (ev["id"], ev["field"], ev["origin"], ev["task_id"], ev["to_value"]) == (
        body["event_id"], "import", "import", None, "5")
    assert ev["extra"]["created"] == 5 and ev["extra"]["skipped"] == 2 and len(ev["extra"]["task_ids"]) == 5
    detail = client.get(f"/api/v1/projects/{body['project_id']}").json()
    assert detail["baseline_saved_at"] is not None


def test_ac32_commit_failure_leaves_nothing(client, seed, query, monkeypatch):
    seed(BASE)
    rows = rows_from(client.post(PREVIEW, json={"text": AC30}).json())

    def boom(*args, **kwargs):
        raise RuntimeError("中途失敗")

    monkeypatch.setattr(service, "write_event", boom)
    r = client.post(COMMIT, json={"target": "new", "new_name": "x", "rows": rows})
    assert r.status_code == 500
    assert count(query, "tasks") == 7 and count(query, "projects") == 2


def test_commit_into_existing_project_and_guards(client, seed, query):
    seed(BASE + PRIVATE_PROJECT)
    row = [{"index": 0, "title": "私事", "owner": "", "start": "", "end": "11/30"}]
    body = client.post(COMMIT, json={"target": 3, "rows": row}).json()
    assert body["project_id"] == 3
    assert query("SELECT scope, start_date FROM tasks WHERE project_id = 3")[0]["scope"] == "private"
    assert client.post(COMMIT, json={"target": 4, "rows": row}).status_code == 422   # 已封存
    assert client.post(COMMIT, json={"target": 99, "rows": row}).status_code == 404
    skipped_all = [r | {"skip": True} for r in row]
    resp = client.post(COMMIT, json={"target": 3, "rows": skipped_all})
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "EMPTY_SELECTION"
    assert client.post(COMMIT, json={"target": "new", "new_name": " ", "rows": row}).status_code == 422


def test_ac55_preview_500_rows_under_2_seconds(client, seed):
    seed(BASE)
    text = "任務,負責人,開始,結束\n" + "\n".join(f"任務 {i},我,11/{(i % 20) + 1},12/{(i % 20) + 5}" for i in range(500))
    started = time.perf_counter()
    r = client.post(PREVIEW, json={"text": text})
    elapsed = time.perf_counter() - started
    assert r.status_code == 200 and r.json()["summary"]["importable"] == 500
    assert elapsed < 2.0, elapsed


def test_ai_invalid_output_reports_invalid_output_status(client, seed, ai):
    seed(BASE)
    ai.script(NODE, {"title": "x"})
    body = client.post(PREVIEW, json={"text": "工項,PIC,起,交期\n需求確認,我,11/16,11/18"}).json()
    assert body["ai_status"] == "invalid_output" and body["column_map"]["mapped_by"] is None


# ---------- 12.7 D-3：AI-07 表頭對應回饋（FR-AI-04，#8） ----------

AI_TEXT = "工項,PIC,起,交期\n需求確認,我,11/16,11/18"
AI_MAP = {"title": 0, "owner": 1, "start": 2, "end": 3}


def ai_preview(client, ai):
    ai.script(NODE, AI_MAP | {"reason": "表頭『工項』是任務名稱"})   # 夾帶文字，不可進 detail
    return client.post(PREVIEW, json={"text": AI_TEXT}).json()


def commit_with(client, body, **extra):
    return client.post(COMMIT, json={"target": "new", "new_name": "匯入", "rows": rows_from(body)} | extra)


def feedback(query):
    return query("SELECT node_id, target_type, target_id, outcome, detail FROM ai_feedback ORDER BY id")


def test_d3_preview_returns_ai_run_id_only_when_ai_mapped(client, seed, ai, query):
    seed(BASE)
    body = ai_preview(client, ai)
    [run] = query("SELECT id FROM ai_runs")
    assert body["column_map"] == AI_MAP | {"mapped_by": "ai", "ai_run_id": run["id"]}
    manual = client.post(PREVIEW, json={"text": AI_TEXT, "column_map": AI_MAP}).json()
    assert "ai_run_id" not in manual["column_map"]


def test_d3_accepted_mapping_writes_one_feedback_with_indexes_only(client, seed, ai, query):
    seed(BASE)
    body = ai_preview(client, ai)
    run_id = body["column_map"]["ai_run_id"]
    r = commit_with(client, body, ai_run_id=run_id, column_map=AI_MAP)
    assert r.status_code == 201
    assert feedback(query) == [{"node_id": "AI-07", "target_type": "import_map", "target_id": r.json()["event_id"],
                                "outcome": "accepted",
                                "detail": {"ai_run_id": run_id, "ai": AI_MAP, "final": AI_MAP}}]


def test_d3_changed_mapping_records_changed(client, seed, ai, query):
    seed(BASE)
    body = ai_preview(client, ai)
    final = AI_MAP | {"owner": None, "start": 1}
    r = commit_with(client, body, ai_run_id=body["column_map"]["ai_run_id"], column_map=final)
    assert r.status_code == 201
    [fb] = feedback(query)
    assert fb["outcome"] == "changed" and fb["detail"]["ai"] == AI_MAP and fb["detail"]["final"] == final


def test_d3_without_ai_run_id_writes_no_feedback(client, seed, ai, query):
    seed(BASE)
    r = commit_with(client, ai_preview(client, ai))
    assert r.status_code == 201 and set(r.json()) == {"project_id", "created", "skipped", "event_id"}
    assert feedback(query) == []


@pytest.mark.parametrize("extra", ["ai_run_id", "column_map"])
def test_d3_ai_run_id_and_column_map_must_come_together(client, seed, ai, query, extra):
    seed(BASE)
    body = ai_preview(client, ai)
    value = {"ai_run_id": body["column_map"]["ai_run_id"], "column_map": AI_MAP}[extra]
    r = commit_with(client, body, **{extra: value})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "tasks") == 7 and feedback(query) == []


AI_RUNS_OTHER = """
INSERT INTO ai_runs (id, node_id, status, attempt, raw_output, created_at) VALUES
  (901, 'AI-01', 'ok', 1, '{"title": 0, "end": 3}', '2026-11-15T09:00+08:00'),
  (902, 'AI-07', 'timeout', 1, NULL, '2026-11-15T09:00+08:00');
"""


@pytest.mark.parametrize("run_id", [901, 902, 999])
def test_d3_ai_run_id_must_be_an_ok_ai07_run(client, seed, query, run_id):
    seed(BASE + AI_RUNS_OTHER)
    rows = [{"index": 0, "title": "需求確認", "owner": "我", "start": "11/16", "end": "11/18"}]
    r = client.post(COMMIT, json={"target": "new", "new_name": "匯入", "rows": rows,
                                  "ai_run_id": run_id, "column_map": AI_MAP})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert count(query, "tasks") == 7 and feedback(query) == []


def test_d3_same_ai_run_id_twice_imports_but_feedback_once(client, seed, ai, query):
    seed(BASE)
    body = ai_preview(client, ai)
    run_id = body["column_map"]["ai_run_id"]
    first = commit_with(client, body, ai_run_id=run_id, column_map=AI_MAP)
    second = commit_with(client, body, ai_run_id=run_id, column_map=AI_MAP | {"start": None})
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["project_id"] != second.json()["project_id"]
    assert [fb["outcome"] for fb in feedback(query)] == ["accepted"]


def test_d3_commit_failure_rolls_back_feedback(client, seed, ai, query, monkeypatch):
    seed(BASE)
    body = ai_preview(client, ai)

    def boom(*args, **kwargs):
        raise RuntimeError("中途失敗")

    monkeypatch.setattr(service, "write_event", boom)
    r = commit_with(client, body, ai_run_id=body["column_map"]["ai_run_id"], column_map=AI_MAP)
    assert r.status_code == 500 and feedback(query) == [] and count(query, "tasks") == 7
