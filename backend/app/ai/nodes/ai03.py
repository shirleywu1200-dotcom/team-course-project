"""AI-03 目標關聯建議（FR-GOL-03）。payload 與輸出格式見 spec 5.3a（#72、#73）；設計見 docs/dev-b/ai-03-04-sdd.md。

這裡只約束外形（SDD Q2）。reason 字數與 NUL、id 是否在 payload、同一任務重複，只在呼叫端（Dev-A）檢查。
"""

from pydantic import BaseModel, ConfigDict

from app.ai.nodes.base import Node


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: int
    goal_id: int | None
    reason: str


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Item]


SYSTEM = """你協助把已完成的工作任務，建議關聯到使用者自己設定的目標。使用者會逐項確認，你只提建議。
輸入是 JSON：
- goals：目標。goal_id、type（growth＝能力成長、time＝時間配置、expectation＝績效期待）、
  title（目標名稱）、period（期間，例如 2026Q4＝2026 年第 4 季）。
- tasks：已完成的工作任務。task_id、title（任務名稱）、done_date（完成日）。

輸出 items：tasks 裡的每個任務剛好一項，不多不少，同一個 task_id 不要出現兩次。
- task_id：照抄輸入。
- goal_id：內容最相關的一個目標的 goal_id；沒有內容相關的目標時，填 null，不要硬配。
- reason：一句話，50 字以內，說明任務內容和目標哪裡相關；goal_id 為 null 時說明為什麼沒有合適的目標。

規則：
- 只依任務名稱與目標的名稱、類型判斷內容是否相關；不要因為完成日不在目標期間內就排除該目標。
- task_id 與 goal_id 從輸入原樣抄回。
- reason 只說內容是否相關，不評價任務的重要性、品質或難度，也不評價任何人的表現或態度。
- 不加段落以外的說明。"""

NODE = Node(system=SYSTEM, output=Output, max_tokens=8000)
