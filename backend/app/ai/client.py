"""AI 供應商介面（FR-AI-05）。

客戶內容只經這個介面送出；其他程式不直接呼叫任何 LLM 用戶端。
契約擁有者為 Dev-B（todo 5.7）；本檔由 Dev-A 在 Phase 0.6 建立骨架，
簽名變動前先與 Dev-B 確認。
"""

from abc import ABC, abstractmethod
from collections import defaultdict, deque

DEFAULT_TIMEOUT_S = 20.0


class AIError(Exception):
    """AI 呼叫失敗的共同基底。訊息只放錯誤類型，不放送出或收到的內容。"""


class AITimeout(AIError):
    pass


class AIInvalidOutput(AIError):
    pass


class AIUnavailable(AIError):
    pass


class AIClient(ABC):
    @abstractmethod
    def call(self, node_id: str, payload: dict, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
        """呼叫一個 AI 節點（AI-01～AI-07），回傳結構化輸出。失敗時丟 AIError 子類別。"""

    @abstractmethod
    def health(self) -> bool:
        """供應商是否可用，供 `/meta/health` 使用。"""


class FakeAIClient(AIClient):
    """測試用：依節點預先排好回傳值或例外，依序吐出。沒排到時視為不可用。"""

    def __init__(self, available: bool = True):
        self.available = available
        self.calls: list[tuple[str, dict]] = []
        self._scripts: dict[str, deque] = defaultdict(deque)

    def script(self, node_id: str, *outputs) -> None:
        self._scripts[node_id].extend(outputs)

    def call(self, node_id: str, payload: dict, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
        self.calls.append((node_id, payload))
        if not self.available or not self._scripts[node_id]:
            raise AIUnavailable(node_id)
        out = self._scripts[node_id].popleft()
        if isinstance(out, type) and issubclass(out, Exception):
            raise out(node_id)
        if isinstance(out, Exception):
            raise out
        return out

    def health(self) -> bool:
        return self.available
