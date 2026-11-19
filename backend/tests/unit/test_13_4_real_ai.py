"""13.4 真實 AI 供應商（docs/dev-b/13-4-sdd.md D-1～D-4）。

不連網：以假的 SDK 物件取代 `anthropic.Anthropic`，只驗證對應規則。
真實呼叫的冒煙測試在檔尾，標 `real_ai`，沒有 AI_PROVIDER=anthropic 與 key 時跳過。
"""

import json
import os
from datetime import date
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.ai.anthropic_client import AnthropicAIClient
from app.ai.client import AIInvalidOutput, AITimeout, AIUnavailable, FakeAIClient
from app.ai.nodes import NODES
from app.ai.provider import ai_from_settings
from app.config import Settings
from app.domain import ai05
from app.domain.weekly_report import SECTIONS, WeekData, reconcile

REQ = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
AI01_PAYLOAD = {"today": "2026-11-11", "messages": [{"ref": 1, "speaker": "王", "spoken_at": None, "text": "報價單延到 11/18"}],
                "tasks": [{"id": 2, "title": "報價單", "owner": "王", "latest_due": "2026-11-14"}]}
AI01_OUT = {"items": [{"ref": 1, "kind": "delay", "task_id": 2, "new_due": "11/18", "certainty": "sure"}]}


def _status_error(cls, code):
    return cls("x", response=httpx2.Response(code, request=REQ), body=None)


def _reply(obj, stop_reason="end_turn"):
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))


class FakeSDK:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.kwargs = result, error, None
        self.messages = SimpleNamespace(create=self._create)
        self.models = SimpleNamespace(retrieve=self._retrieve)

    def _create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result

    def _retrieve(self, model, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(id=model)


def _client(sdk, api_key="k"):
    return AnthropicAIClient(api_key=api_key, model="claude-sonnet-5-5", sdk=sdk)


def test_ai01_ok_returns_dict_and_sends_schema_and_timeout():
    sdk = FakeSDK(result=_reply(AI01_OUT))
    assert _client(sdk).call("AI-01", AI01_PAYLOAD, timeout_s=7) == AI01_OUT
    assert sdk.kwargs["model"] == "claude-sonnet-5-5"
    assert sdk.kwargs["timeout"] == 7
    assert sdk.kwargs["output_config"]["effort"] == "low"
    assert sdk.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "報價單延到 11/18" in sdk.kwargs["messages"][0]["content"]


AI06_PAYLOAD = {"q1": "交付物可用、沒有返工", "q2": "提前完成且主管直接採用", "q3": "共用一套",
                "current": ["未達成", "部分達成", "符合預設", "優於預設", "遠超預設"]}
AI07_PAYLOAD = {"headers": ["項目", "負責", "起", "截止"], "samples": [["報價單", "王", "11/1", "11/14"]]}


@pytest.mark.parametrize(("node", "out"), [
    ("AI-06", {"levels": ["a", "b", "c", "d", "e"]}),
    ("AI-07", {"title": 0, "owner": 1, "start": 2, "end": 3}),
])
def test_registered_nodes_parse(node, out):
    assert _client(FakeSDK(result=_reply(out))).call(node, {}) == out


# AI-05（docs/dev-b/ai-05-sdd.md）：輸出範例取自 spec 5.3a
AI05_OUT = {"draft": "本週（11/09–11/15）工作進度…",
            "items": [{"section": "done", "task_id": 3, "event_id": 41},
                      {"section": "next", "task_id": 5, "event_id": None}]}


def test_ai05_registered_and_parses_spec_example():
    assert "AI-05" in NODES
    assert _client(FakeSDK(result=_reply(AI05_OUT))).call("AI-05", {}) == AI05_OUT


def test_ai05_section_values_match_weekly_report_sections():
    # 值域只有一份事實：weekly_report.SECTIONS；節點 schema 必須與它相同（SDD 2.1、Q1）
    schema = NODES["AI-05"].output.model_json_schema()
    item = schema["$defs"]["Item"]["properties"]["section"]
    assert set(item["enum"]) == set(SECTIONS)


def test_ai05_schema_forbids_extra_keys():
    # 送給供應商的 schema 要帶 additionalProperties: false；拿掉 extra="forbid" 時只有這則會紅（#53 Dev-A 審查）
    schema = NODES["AI-05"].output.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["Item"]["additionalProperties"] is False


@pytest.mark.parametrize("bad", [
    {"draft": "x", "items": [{"section": "other", "task_id": 3, "event_id": 41}]},
    {"draft": "x", "items": [{"section": "done", "task_id": "abc", "event_id": 41}]},   # "3" 會被寬鬆轉型成 3，與其他節點一致
    {"items": []},
])
def test_ai05_rejects_out_of_shape_output(bad):
    with pytest.raises(AIInvalidOutput):
        _client(FakeSDK(result=_reply(bad))).call("AI-05", {})


# AI-03、AI-04（docs/dev-b/ai-03-04-sdd.md）：輸出範例與 stats 範例取自 spec 5.3a（#73）
AI03_OUT = {"items": [{"task_id": 7, "goal_id": 2, "reason": "任務內容與 SQL 學習相關"},
                      {"task_id": 8, "goal_id": None, "reason": "沒有內容相關的目標"}]}
AI04_OUT = {"draft": "…", "figures": [{"key": "linked", "value": 3}, {"key": "avg_actual", "value": 4.0}]}
AI04_STATS = {"linked": 3, "avg_actual": 4.0, "avg_expected": 3.3, "overdue_count": 1,
              "energy": {"high": 2, "mid": 1, "low": 0}, "progress_pct": 100, "judgement": None}


@pytest.mark.parametrize(("node", "out"), [("AI-03", AI03_OUT), ("AI-04", AI04_OUT)])
def test_goal_nodes_registered_and_parse_spec_example(node, out):
    assert node in NODES
    assert _client(FakeSDK(result=_reply(out))).call(node, {}) == out


@pytest.mark.parametrize("node", ["AI-03", "AI-04"])
def test_goal_nodes_schema_forbids_extra_keys(node):
    schema = NODES[node].output.model_json_schema()
    assert schema["additionalProperties"] is False
    assert all(d["additionalProperties"] is False for d in schema["$defs"].values())


@pytest.mark.parametrize("bad", [
    {"items": [{"task_id": 7, "goal_id": "abc", "reason": "x"}]},
    {"items": [{"task_id": 7, "goal_id": 2}]},
    {"items": [{"task_id": 7, "goal_id": 2, "reason": "x", "score": 5}]},
])
def test_ai03_rejects_out_of_shape_output(bad):
    with pytest.raises(AIInvalidOutput):
        _client(FakeSDK(result=_reply(bad))).call("AI-03", {})


@pytest.mark.parametrize("bad", [
    {"draft": "x", "figures": [{"key": "total", "value": 3}]},
    {"draft": "x"},
])
def test_ai04_rejects_out_of_shape_output(bad):
    with pytest.raises(AIInvalidOutput):
        _client(FakeSDK(result=_reply(bad))).call("AI-04", {})


def _numeric_keys(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _numeric_keys(v, f"{prefix}{k}.")
        elif isinstance(v, int | float) and not isinstance(v, bool):
            yield prefix + k


def test_ai04_figure_keys_cover_stats_numeric_keys():
    # 鍵名值域＝5.3a stats 的數字鍵（巢狀攤平）；呼叫端合併後改綁呼叫端的 stats（SDD 2.3）
    schema = NODES["AI-04"].output.model_json_schema()
    assert set(schema["$defs"]["Figure"]["properties"]["key"]["enum"]) == set(_numeric_keys(AI04_STATS))


def test_sdk_retries_disabled():
    assert AnthropicAIClient(api_key="k", model="m").sdk.max_retries == 0


def test_sdk_open_telemetry_disabled_even_if_env_asks_for_content(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_OPEN_TELEMETRY_TRACES_CONTENT_MODE", "content")
    assert AnthropicAIClient(api_key="k", model="m").sdk.open_telemetry["traces"]["enabled"] is False


@pytest.mark.parametrize("error", [
    anthropic.APITimeoutError(request=REQ),
    anthropic.APIConnectionError(request=REQ),
    _status_error(anthropic.RateLimitError, 429),
    _status_error(anthropic.InternalServerError, 500),
    _status_error(anthropic.APIStatusError, 529),
])
def test_transient_errors_map_to_timeout(error):
    with pytest.raises(AITimeout):
        _client(FakeSDK(error=error)).call("AI-01", AI01_PAYLOAD)


@pytest.mark.parametrize("error", [
    _status_error(anthropic.AuthenticationError, 401),
    _status_error(anthropic.PermissionDeniedError, 403),
    _status_error(anthropic.BadRequestError, 400),
    _status_error(anthropic.NotFoundError, 404),
])
def test_permanent_errors_map_to_unavailable(error):
    with pytest.raises(AIUnavailable):
        _client(FakeSDK(error=error)).call("AI-01", AI01_PAYLOAD)


@pytest.mark.parametrize("reply", [
    _reply("不是 JSON"),
    _reply({"items": [{"ref": 1, "kind": "maybe", "task_id": 2, "new_due": None, "certainty": "sure"}]}),
    _reply(AI01_OUT, stop_reason="max_tokens"),
])
def test_bad_output_maps_to_invalid_output(reply):
    with pytest.raises(AIInvalidOutput):
        _client(FakeSDK(result=reply)).call("AI-01", AI01_PAYLOAD)


def test_refusal_maps_to_unavailable():   # 重試通常仍拒答，直接走退路（SDD 第 2 節第 10 題）
    with pytest.raises(AIUnavailable):
        _client(FakeSDK(result=_reply(AI01_OUT, stop_reason="refusal"))).call("AI-01", AI01_PAYLOAD)


def test_unregistered_node_is_unavailable_without_calling():
    sdk = FakeSDK(result=_reply({}))
    with pytest.raises(AIUnavailable):
        _client(sdk).call("AI-99", {})   # 永遠不登記的節點；原本用 AI-05，AI-05 已登記（ai-05-sdd）
    assert sdk.kwargs is None


def test_missing_key_is_unavailable():
    client = AnthropicAIClient(api_key="", model="m")
    with pytest.raises(AIUnavailable):
        client.call("AI-01", AI01_PAYLOAD)
    assert client.health() is False


def test_health():
    assert _client(FakeSDK()).health() is True
    assert _client(FakeSDK(error=_status_error(anthropic.AuthenticationError, 401))).health() is False
    assert _client(FakeSDK(error=anthropic.APIConnectionError(request=REQ))).health() is False


def _settings(**kw):
    return Settings(database_url="unused", api_token="unused", bind_host="127.0.0.1", port=0, **kw)  # noqa: S106 測試假值


def test_provider_defaults_off():
    ai = ai_from_settings(_settings())
    assert isinstance(ai, FakeAIClient) and ai.health() is False


def test_provider_anthropic():
    ai = ai_from_settings(_settings(ai_provider="anthropic", ai_model="claude-sonnet-5-5", anthropic_api_key="k"))
    assert isinstance(ai, AnthropicAIClient) and ai.model == "claude-sonnet-5-5"


def test_provider_unknown_value_is_off():
    assert isinstance(ai_from_settings(_settings(ai_provider="openai")), FakeAIClient)


real_ai = pytest.mark.skipif(
    os.environ.get("AI_PROVIDER") != "anthropic" or not os.environ.get("ANTHROPIC_API_KEY"),
    reason="真實 AI 冒煙測試：需 AI_PROVIDER=anthropic 與 ANTHROPIC_API_KEY（會產生費用）")


def _real():
    return AnthropicAIClient(api_key=os.environ["ANTHROPIC_API_KEY"],
                             model=os.environ.get("AI_MODEL", "claude-sonnet-5-5"))


@pytest.mark.real_ai
@real_ai
def test_real_ai01_smoke():
    out = _real().call("AI-01", AI01_PAYLOAD)
    assert out["items"] and out["items"][0]["ref"] == 1


@pytest.mark.real_ai
@real_ai
def test_real_ai06_smoke():
    assert len(_real().call("AI-06", AI06_PAYLOAD)["levels"]) == 5


@pytest.mark.real_ai
@real_ai
def test_real_ai07_smoke():
    assert _real().call("AI-07", AI07_PAYLOAD) == {"title": 0, "owner": 1, "start": 2, "end": 3}


# #22 Dev-A 給的樣本 2（小型；任務 2 同時延期又逾期，出現在 delay 與 next）
AI05_PAYLOAD = {
    "week": {"start": "2026-11-09", "end": "2026-11-15"},
    "done": [{"task_id": 1, "title": "本週完成", "owner": "我", "done_date": "2026-11-10", "event_id": 11}],
    "delay": [{"task_id": 2, "title": "延期任務", "owner": "小薇", "orig_due": "2026-11-12",
               "latest_due": "2026-11-15", "event_ids": [21]}],
    "next": [{"task_id": 2, "title": "延期任務", "owner": "小薇", "latest_due": "2026-11-15", "blocked": False},
             {"task_id": 3, "title": "下週到期", "owner": "我", "latest_due": "2026-11-18", "blocked": False}],
}


@pytest.mark.real_ai
@real_ai
def test_real_ai05_smoke():
    data = WeekData(week_start=date(2026, 11, 9), week_end=date(2026, 11, 15), excluded_private=0,
                    **{s: AI05_PAYLOAD[s] for s in SECTIONS})
    draft, items = ai05.parse_output(_real().call("AI-05", AI05_PAYLOAD, timeout_s=20))
    assert reconcile(items, data)
    assert {(i["section"], i["task_id"]) for i in items} == {("done", 1), ("delay", 2), ("next", 2), ("next", 3)}


AI03_PAYLOAD = {
    "goals": [{"goal_id": 2, "type": "growth", "title": "學會 SQL 視窗函式", "period": "2026Q4"},
              {"goal_id": 3, "type": "time", "title": "每週留時間做客戶拜訪", "period": "2026Q4"}],
    "tasks": [{"task_id": 7, "title": "報表查詢改寫成視窗函式", "done_date": "2026-11-12"},
              {"task_id": 8, "title": "辦公室搬遷打包", "done_date": "2026-11-13"}],
}


@pytest.mark.real_ai
@real_ai
def test_real_ai03_smoke():
    items = _real().call("AI-03", AI03_PAYLOAD, timeout_s=20)["items"]
    assert {i["task_id"] for i in items} == {7, 8}
    assert {i["goal_id"] for i in items} <= {2, 3, None}


AI04_PAYLOAD = {"goal": {"type": "growth", "title": "學會 SQL 視窗函式", "period": "2026Q4", "energy_plan": "high"},
                "stats": AI04_STATS,
                "tasks": [{"task_id": 7, "title": "報表查詢改寫", "done_date": "2026-11-12"}]}


@pytest.mark.real_ai
@real_ai
def test_real_ai04_smoke():
    # R3 第 1 點：figures 都等於 stats 同名值；第 2 點（草稿內數字）由 scripts/eval_ai04.py 量（SDD Q1）
    out = _real().call("AI-04", AI04_PAYLOAD, timeout_s=20)
    flat = {"energy." + k: v for k, v in AI04_STATS["energy"].items()} | AI04_STATS
    assert out["draft"].strip()
    assert all(flat[f["key"]] == f["value"] for f in out["figures"])
