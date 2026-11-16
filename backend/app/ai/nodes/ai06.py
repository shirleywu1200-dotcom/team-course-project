"""AI-06 量表訪談（FR-RUB-02、03）。輸入三題回答與目前量表，回 5 句草稿。

句數與長度由 `domain/rubrics.py` 的 valid_levels 檢查；schema 不放數量限制，避免供應商不支援的關鍵字。
"""

from pydantic import BaseModel, ConfigDict

from app.ai.nodes.base import Node


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    levels: list[str]


SYSTEM = """你協助使用者撰寫「星數量表」：5 句描述，依序對應 1 到 5 顆星，用來在事前設定任務的預期品質。
輸入是 JSON：q1（什麼程度算符合預設）、q2（什麼情況給 5 顆星）、
q3（不同類型任務是否用不同標準）、current（目前的 5 句量表）。
輸出 levels：剛好 5 句，第 1 句最低（未達成）、第 5 句最高（遠超預設），第 3 句對應「符合預設」。
- 依 q1、q2 的回答改寫 current；回答沒提到的層級保留原意。
- 每句一行、不超過 60 字，用使用者的用詞，台灣繁體中文。
- q3 本版只記錄，不分類型產生多套量表。
- 只描述完成程度的標準，不評價使用者本人。"""

NODE = Node(system=SYSTEM, output=Output, max_tokens=4000)
