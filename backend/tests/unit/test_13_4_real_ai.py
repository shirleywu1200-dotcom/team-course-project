"""13.4 真實 AI 供應商（docs/dev-b/13-4-sdd.md D-1～D-4）。

不連網：以假的 SDK 物件取代 `anthropic.Anthropic`，只驗證對應規則。
真實呼叫的冒煙測試在檔尾，標 `real_ai`，沒有 AI_PROVIDER=anthropic 與 key 時跳過。
"""

import json
import os
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.ai.anthropic_client import AnthropicAIClient
from app.ai.client import AIInvalidOutput, AITimeout, AIUnavailable, FakeAIClient
from app.ai.provider import ai_from_settings
from app.config import Settings

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


def test_sdk_retries_disabled():
    assert AnthropicAIClient(api_key="k", model="m").sdk.max_retries == 0


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
    _reply(AI01_OUT, stop_reason="refusal"),
])
def test_bad_output_maps_to_invalid_output(reply):
    with pytest.raises(AIInvalidOutput):
        _client(FakeSDK(result=reply)).call("AI-01", AI01_PAYLOAD)


def test_unregistered_node_is_unavailable_without_calling():
    sdk = FakeSDK(result=_reply({}))
    with pytest.raises(AIUnavailable):
        _client(sdk).call("AI-05", {})
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
