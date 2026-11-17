"""AI-01 候選抽取（FR-INB-06）。輸出格式與 `domain/inbox/r2.py` 讀取的欄位一致。

AI 只提議；能變成哪種候選由 R2 規則決定。依 FR-DUE-05a，不要求也不讀取延期原因。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.ai.nodes.base import Node


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: int
    kind: Literal["delay", "done", "stuck", "none"]
    task_id: int | None
    new_due: str | None
    certainty: Literal["sure", "unsure"]


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Item]


SYSTEM = """你是工作承諾帳的訊息判讀員。
輸入是 JSON：today（今天日期）、messages（群組訊息，每則有 ref）、tasks（目前的任務清單）。
對每一則訊息輸出一個 item；一則訊息講到多個任務時，每個任務各輸出一個 item（ref 相同）：
- ref：訊息的 ref，原樣抄回。
- kind：delay＝說某任務會延後或改期；done＝說某任務已完成；stuck＝說某任務卡住、做不下去；
  none＝與任務進度無關（閒聊、問候、單純提問、只是分享資訊）。
- task_id：訊息講的是 tasks 中的哪一個任務的 id。只有能明確對到時才填；對不到或不確定就填 null，不要猜。
- new_due：只有 kind 為 delay 時填新的日期，格式 YYYY-MM-DD；「下週三」「月底」這類說法以 today 換算。其他情況填 null。
- certainty：說話者語氣肯定填 sure；問句、「可能」「大概」「應該」「也許」、條件句或推測填 unsure。
只判斷訊息說了什麼，不推測原因，也不評價任何人。"""

NODE = Node(system=SYSTEM, output=Output, max_tokens=8000)
