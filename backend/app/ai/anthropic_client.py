"""AIClient 的真實實作：Anthropic Claude API（13.4 SDD D-2、D-3）。

- 只呼叫節點登記表（app.ai.nodes）裡有的節點；其他節點丟 AIUnavailable。
- SDK 不自動重試（max_retries=0），重試由呼叫端負責，每次實際呼叫才都有一筆 ai_runs。
- 錯誤對應：逾時、429、5xx、連線中斷 → AITimeout（呼叫端續跑）；其他 HTTP 錯誤或沒有 key → AIUnavailable；
  輸出不合 schema、被截斷或拒答 → AIInvalidOutput。
- log 只記節點、HTTP 狀態碼與 token 數，不記送出或收到的內容（資安規則 3）。
"""

import json
import logging

import anthropic
from pydantic import ValidationError

from app.ai.client import DEFAULT_TIMEOUT_S, AIClient, AIInvalidOutput, AITimeout, AIUnavailable
from app.ai.nodes import NODES

log = logging.getLogger(__name__)

HEALTH_TIMEOUT_S = 3.0
EFFORT = "low"   # 20 秒逾時內要能回來（SDD 2b）


class AnthropicAIClient(AIClient):
    def __init__(self, api_key: str, model: str, sdk=None):
        self.api_key = api_key
        self.model = model
        self.sdk = sdk or (anthropic.Anthropic(api_key=api_key, max_retries=0) if api_key else None)
        self.last_usage = (0, 0)   # 最近一次成功回應的（輸入, 輸出）token 數

    def call(self, node_id: str, payload: dict, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
        node = NODES.get(node_id)
        if node is None or not self.api_key:
            raise AIUnavailable(node_id)
        try:
            resp = self.sdk.messages.create(
                model=self.model, max_tokens=node.max_tokens, system=node.system, timeout=timeout_s,
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}],
                output_config={"effort": EFFORT,
                               "format": {"type": "json_schema", "schema": node.output.model_json_schema()}})
        except anthropic.APIConnectionError as exc:   # 含 APITimeoutError
            log.info("AI %s 連線失敗或逾時", node_id)
            raise AITimeout(node_id) from exc
        except anthropic.APIStatusError as exc:
            log.info("AI %s HTTP %s", node_id, exc.status_code)
            if exc.status_code == 429 or exc.status_code >= 500:
                raise AITimeout(node_id) from exc
            raise AIUnavailable(node_id) from exc
        self.last_usage = (resp.usage.input_tokens, resp.usage.output_tokens)   # 評估腳本計費用
        log.info("AI %s stop=%s in=%s out=%s", node_id, resp.stop_reason, *self.last_usage)
        if resp.stop_reason != "end_turn":   # max_tokens 截斷、refusal 拒答
            raise AIInvalidOutput(node_id)
        text = next((b.text for b in resp.content if b.type == "text"), None)
        try:
            return node.output.model_validate_json(text or "").model_dump()
        except ValidationError as exc:
            raise AIInvalidOutput(node_id) from exc

    def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            self.sdk.models.retrieve(self.model, timeout=HEALTH_TIMEOUT_S)
        except anthropic.APIError:
            return False
        return True
