"""#92（PO 裁定 Q6：排除）：AI-03 不送綁私人專案的 expectation 目標（spec 5.3a〈AI-03〉、5.13 suggest；資安規則 2）。

Dev-A 依 DA-27 暫代撰寫；只經 HTTP、SQL 種子與 FakeAIClient 操作，不讀實作。
測試清單與子代理審查紀錄：.scratch/phase9/testlist-92.md。
種子沿用 test_phase9_ai03 的 BASE 與任務（待關聯的工作任務 21、23），另加私人專案與三個 expectation 目標。
"""

import json

import pytest

from app.ai.client import AIInvalidOutput, AITimeout
from tests.acceptance.helpers import API
from tests.acceptance.test_phase9_ai03 import (
    BASE,
    DECIDED,
    TASKS,
    TS,
    ai03_payloads,
    feedback_rows,
    link,
    ok_output,
    runs,
    seed_tasks,
    suggest,
)

MARK = "私密目標標記"   # 被排除目標的標題、期間、定義都帶它，不能出現在 payload、ai_runs、log
PRIVATE = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at, archived_at) VALUES
 (3, '家裡裝修', 'private', 'none', {TS}, {TS}, NULL),
 (4, '舊私事', 'private', 'none', {TS}, {TS}, '2026-11-05T09:00+08:00');
INSERT INTO goals (id, type, title, period, definition, target, energy_plan, project_id, created_at, archived_at) VALUES
 (16, 'expectation', '{MARK}裝修完工', '{MARK}期間', '{MARK}定義', 0, 'high', 3, {TS}, NULL),
 (17, 'expectation', '{MARK}舊私事', '{MARK}期間', '', 0, 'low', 4, {TS}, NULL),
 (18, 'expectation', '舊專案結案', '2026Q3', '', 0, 'mid', 2, {TS}, NULL);
"""
SENT = [11, 12, 13, 18]   # growth、time、工作專案（含已封存的工作專案 2）的 expectation；14 已封存


@pytest.fixture
def data(seed):
    seed(BASE)
    seed_tasks(seed, TASKS, [21, 22, 23, 26])
    seed(DECIDED)
    seed(PRIVATE)


def sent_goal_ids(ai, index=0):
    return [g["goal_id"] for g in ai03_payloads(ai)[index]["goals"]]


# Q1～Q3、必補 3、4：正向比對送出的目標集合；私人專案（含已封存的）照樣排除，已封存的工作專案照送
def test_q1_q3_sends_exactly_the_non_private_goals(client, data, ai):
    ai.script("AI-03", ok_output())
    suggest(client)
    assert sent_goal_ids(ai) == SENT
    assert MARK not in json.dumps(ai03_payloads(ai), ensure_ascii=False)


# Q4、建議 9：未封存目標全部被排除（另有一個已封存目標）→ 不呼叫 AI、不寫 ai_runs
def test_q4_all_sendable_goals_excluded_skips_ai(client, data, seed, ai, query):
    seed("UPDATE goals SET archived_at = '2026-11-05T09:00+08:00' WHERE id IN (11, 12, 13, 18);")
    assert suggest(client) == {"ai_status": "unavailable", "ai_run_id": None, "items": []}
    assert ai03_payloads(ai) == [] and runs(query) == []


# Q5、必補 2：AI 回了被排除目標 → 該項丟棄，回應與 ok 列 raw_output 都沒有它
def test_q5_item_with_excluded_goal_dropped_from_response_and_raw_output(client, data, ai, query):
    ai.script("AI-03", ok_output((21, 16, "r21"), (23, 11, "r23")))
    body = suggest(client)
    assert body["items"] == [{"task_id": 23, "goal_id": 11, "reason": "r23"}]
    stored = json.loads(runs(query)[0]["raw_output"])
    assert stored == {"items": [{"task_id": 23, "goal_id": 11, "reason": "r23"}]}


# Q6：以呼叫當下的專案範圍判定
def test_q6_scope_is_judged_at_call_time(client, data, seed, ai):
    ai.script("AI-03", ok_output(), ok_output())
    seed("UPDATE projects SET scope = 'work', audience = 'manager' WHERE id = 3;")
    suggest(client)
    assert 16 in sent_goal_ids(ai, 0)
    seed("UPDATE projects SET scope = 'private', audience = 'none' WHERE id = 3;")
    suggest(client)
    assert 16 not in sent_goal_ids(ai, 1)


# 必補 5：每一次嘗試都排除
def test_every_retry_attempt_excludes_private_goals(client, data, ai):
    ai.script("AI-03", AITimeout, AIInvalidOutput, ok_output())
    assert suggest(client)["ai_status"] == "ok"
    assert [sent_goal_ids(ai, i) for i in range(3)] == [SENT, SENT, SENT]


# Q7：使用者仍可手動關聯到被排除的目標
def test_q7_manual_link_to_excluded_goal_still_works(client, data, query):
    r = link(client, 21, 16, 2)
    assert r.status_code == 200, r.text
    assert query("SELECT goal_id FROM tasks WHERE id = 21")[0]["goal_id"] == 16
    assert r.json()["event"]["to_value"] == "16"


# 必補 1a：建議被丟掉的任務，改手動關聯到被排除目標 → 關聯照常、不寫回饋（5.13「建議裡沒有這個任務」）
def test_link_to_excluded_goal_after_dropped_suggestion_writes_no_feedback(client, data, ai, query):
    ai.script("AI-03", ok_output((21, 16, "r21"), (23, 11, "r23")))
    run_id = suggest(client)["ai_run_id"]
    assert link(client, 21, 16, 2, ai_run_id=run_id).status_code == 200
    assert feedback_rows(query) == []


# 必補 1b：建議可送的目標，使用者改選被排除目標 → changed，detail 只含整數
def test_changed_to_excluded_goal_writes_changed_feedback(client, data, ai, query):
    ai.script("AI-03", ok_output((21, 11, "r21")))
    run_id = suggest(client)["ai_run_id"]
    assert link(client, 21, 16, 2, ai_run_id=run_id).status_code == 200
    fb = feedback_rows(query)
    assert [f["outcome"] for f in fb] == ["changed"]
    assert fb[0]["detail"] == {"ai_run_id": run_id, "task_id": 21, "ai": 11, "final": 16}


# Q8：只影響 AI 送出；目標列表、統計、矩陣照常（5.13 的定義只看封存狀態）
def test_q8_goal_reads_still_include_excluded_goal(client, data):
    assert 16 in [g["id"] for g in client.get(f"{API}/goals").json()["items"]]
    assert client.get(f"{API}/goals/16/stats").status_code == 200
    assert 16 in [g["goal_id"] for g in client.get(f"{API}/goals/matrix").json()["items"]]


# Q9、建議 6、7：被排除目標的標題、期間、定義不出現在 log 與 ai_runs（suggest 與後續關聯都看）
def test_q9_excluded_goal_text_not_in_logs_or_ai_runs(client, data, ai, query, caplog):
    ai.script("AI-03", RuntimeError("x"), {"items": [{"task_id": 21, "goal_id": "x", "reason": "r"}]},
              ok_output((21, 16, "r21")))
    with caplog.at_level("DEBUG"):
        run_id = suggest(client)["ai_run_id"]
        link(client, 21, 16, 2, ai_run_id=run_id)
    assert MARK not in caplog.text
    assert MARK not in json.dumps(runs(query), ensure_ascii=False, default=str)


# 建議 8：冪等重送回第一次的結果，不再呼叫 AI；快取只有 id 與 reason，沒有被排除目標的文字
def test_idempotent_resend_after_scope_change_returns_first_result(client, data, seed, ai, query):
    seed("UPDATE projects SET scope = 'work', audience = 'manager' WHERE id = 3;")
    ai.script("AI-03", ok_output((21, 16, "r21")))
    first = suggest(client, headers={"Idempotency-Key": "q92-1"})
    seed("UPDATE projects SET scope = 'private', audience = 'none' WHERE id = 3;")
    assert suggest(client, headers={"Idempotency-Key": "q92-1"}) == first
    assert len(ai03_payloads(ai)) == 1
    cached = json.dumps(query("SELECT response FROM idempotency_keys"), ensure_ascii=False, default=str)
    assert MARK not in cached
