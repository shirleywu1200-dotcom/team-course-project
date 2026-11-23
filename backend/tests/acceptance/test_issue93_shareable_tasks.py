"""13.9 前「可對外任務」共用條件：AI-03 只送可對外任務（spec 5.3a〈AI-03〉、5.13 suggest；#93 第 3 題 B；資安規則 2、3）。

可對外任務＝`tasks.scope='work'`，且無專案或專案 `scope='work'`，以送出當下判定。
Dev-A 依 DA-27 暫代撰寫；只經 HTTP、SQL 種子與 FakeAIClient 操作，不讀實作。
測試清單與子代理審查結果的摘要見 PR #144 說明；待 PO 裁定事項（AI-04、excluded_private 等）見 #143。
種子沿用 test_phase9_ai03 的 BASE 與任務（可送的 21、23；私人任務 22），另加私人專案與其底下的工作任務。
FakeAIClient 排的回傳值不放標記字串，避免格式不合的嘗試存下 AI 原始輸出造成誤判。
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
    task_sql,
)

MARK = "私專標記"   # 不可對外任務的標題都帶它，不能出現在 payload、ai_runs、log、冪等快取
PRIVATE_PROJECTS = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at, archived_at) VALUES
 (5, '家裡裝修', 'private', 'none', {TS}, {TS}, NULL),
 (6, '舊私事', 'private', 'none', {TS}, {TS}, '2026-11-05T09:00+08:00');
"""
EXTRA = [
    task_sql(31, f"{MARK}估價 77", project="5", done="2026-11-10"),               # 私人專案底下的工作任務：不送
    task_sql(32, f"{MARK}舊私事收尾", project="6", done="2026-11-09"),            # 已封存的私人專案：不送
    task_sql(33, "個人進修筆記", project="NULL", done="2026-11-08"),              # 無專案的工作任務：照送
    task_sql(34, f"{MARK}私事", project="1", scope="private", done="2026-11-08"),  # 工作專案底下的私人任務：不送
]
SENT = [33, 21, 23]   # 完成日由新到舊：11-08、11-07、11-06（23 在已封存的工作專案底下）


@pytest.fixture
def data(seed):
    seed(BASE)
    seed(PRIVATE_PROJECTS)
    seed_tasks(seed, TASKS + EXTRA, [21, 22, 23, 26, 31, 32, 33, 34])
    seed(DECIDED)


def sent_task_ids(ai, index=0):
    return [t["task_id"] for t in ai03_payloads(ai)[index]["tasks"]]


# A1、A2、A3、A11：正向比對送出的任務集合與順序
def test_a1_sends_exactly_the_shareable_tasks_newest_first(client, data, ai):
    ai.script("AI-03", ok_output())
    suggest(client)
    assert sent_task_ids(ai) == SENT
    assert MARK not in json.dumps(ai03_payloads(ai), ensure_ascii=False)


# A4：以呼叫當下的專案範圍判定，兩個方向都看
def test_a4_scope_is_judged_at_call_time(client, data, seed, ai):
    ai.script("AI-03", ok_output(), ok_output())
    seed("UPDATE projects SET scope = 'work', audience = 'manager' WHERE id = 5;")
    suggest(client)
    assert sent_task_ids(ai, 0) == [31] + SENT
    seed("UPDATE projects SET scope = 'private', audience = 'none' WHERE id = 5;")
    suggest(client)
    assert sent_task_ids(ai, 1) == SENT


# A5：沒有可送的可對外任務 → 不呼叫 AI、不寫 ai_runs（5.13 suggest）
def test_a5_only_non_shareable_pending_tasks_skip_ai(client, seed, ai, query):
    seed(BASE)
    seed(PRIVATE_PROJECTS)
    seed_tasks(seed, EXTRA[:2] + EXTRA[3:], [31, 32, 34])
    assert suggest(client) == {"ai_status": "unavailable", "ai_run_id": None, "items": []}
    assert ai03_payloads(ai) == [] and runs(query) == []


# A6：AI 回了不可對外任務的 task_id → 該項丟棄，回應與 ok 列 raw_output 都沒有它
def test_a6_item_for_excluded_task_dropped_from_response_and_raw_output(client, data, ai, query):
    ai.script("AI-03", ok_output((31, 11, "丟棄原因"), (21, 11, "r21")))
    body = suggest(client)
    assert body["items"] == [{"task_id": 21, "goal_id": 11, "reason": "r21"}]
    assert json.loads(runs(query)[0]["raw_output"]) == {"items": [{"task_id": 21, "goal_id": 11, "reason": "r21"}]}


# A7：每一次嘗試都排除
def test_a7_every_retry_attempt_excludes(client, data, ai):
    ai.script("AI-03", AITimeout, AIInvalidOutput, ok_output())
    assert suggest(client)["ai_status"] == "ok"
    assert [sent_task_ids(ai, i) for i in range(3)] == [SENT, SENT, SENT]


# A8：被排除任務仍可手動關聯；帶 ai_run_id 時不寫回饋（建議裡沒有這個任務）
def test_a8_manual_link_of_excluded_task_writes_no_feedback(client, data, ai, query):
    ai.script("AI-03", ok_output((21, 11, "r21")))
    run_id = suggest(client)["ai_run_id"]
    r = link(client, 31, 11, 1, ai_run_id=run_id)
    assert r.status_code == 200, r.text
    assert query("SELECT goal_id FROM tasks WHERE id = 31")[0]["goal_id"] == 11
    assert feedback_rows(query) == []


# A9：只影響送 AI；待關聯清單照常列出
def test_a9_pending_list_still_includes_excluded_tasks(client, data):
    r = client.get(f"{API}/goal-links/pending")
    assert r.status_code == 200, r.text
    assert {31, 32, 34} <= {i["task_id"] for i in r.json()["items"]}


# A10：標記不出現在 log 與 ai_runs（suggest 與後續關聯都看）
def test_a10_excluded_titles_not_in_logs_or_ai_runs(client, data, ai, query, caplog):
    ai.script("AI-03", RuntimeError("x"), {"items": [{"task_id": 31, "goal_id": "x", "reason": "r"}]},
              ok_output((31, 11, "r31"), (21, 11, "r21")))
    with caplog.at_level("DEBUG"):
        run_id = suggest(client)["ai_run_id"]
        link(client, 31, 11, 1, ai_run_id=run_id)
    assert MARK not in caplog.text
    assert MARK not in json.dumps(runs(query), ensure_ascii=False, default=str)


# A12：20 筆上限在排除之後才算
def test_a12_limit_counts_only_shareable_tasks(client, seed, ai):
    seed(BASE)
    seed(PRIVATE_PROJECTS)
    shareable = list(range(100, 121))                                  # 21 筆；完成日 11-01～11-11
    newest_private = [200, 201, 202]                                   # 完成日 11-12，最新
    tasks = [task_sql(t, f"任務{t}", done=f"2026-11-{(t - 100) // 2 + 1:02d}") for t in shareable]
    tasks += [task_sql(t, f"{MARK}{t}", project="5", done="2026-11-12") for t in newest_private]
    seed_tasks(seed, tasks, shareable + newest_private)
    ai.script("AI-03", ok_output())
    suggest(client)
    assert sent_task_ids(ai) == sorted(shareable, reverse=True)[:20]


# A13：冪等快取沒有被丟棄的項目與標記；同鍵重送不呼叫 AI、不新增 ai_runs
def test_a13_idempotency_cache_carries_only_validated_items(client, data, ai, query):
    ai.script("AI-03", ok_output((31, 11, "丟棄原因"), (21, 11, "r21")))
    first = suggest(client, headers={"Idempotency-Key": "i93-1"})
    assert suggest(client, headers={"Idempotency-Key": "i93-1"}) == first
    assert first["items"] == [{"task_id": 21, "goal_id": 11, "reason": "r21"}]
    assert len(ai03_payloads(ai)) == 1 and len(runs(query)) == 1
    cached = json.dumps(query("SELECT response FROM idempotency_keys"), ensure_ascii=False, default=str)
    assert MARK not in cached and "丟棄原因" not in cached


# A14：回饋比對的是當次 raw_output，不是目前的範圍：建議當下可對外，之後專案改私人仍照寫回饋
def test_a14_feedback_follows_raw_output_after_scope_change(client, data, seed, ai, query):
    seed("UPDATE projects SET scope = 'work', audience = 'manager' WHERE id = 5;")
    ai.script("AI-03", ok_output((31, 11, "r31")))
    run_id = suggest(client)["ai_run_id"]
    seed("UPDATE projects SET scope = 'private', audience = 'none' WHERE id = 5;")
    assert link(client, 31, 11, 1, ai_run_id=run_id).status_code == 200
    fb = feedback_rows(query)
    assert [f["outcome"] for f in fb] == ["accepted"]
    assert fb[0]["detail"] == {"ai_run_id": run_id, "task_id": 31, "ai": 11, "final": 11}
