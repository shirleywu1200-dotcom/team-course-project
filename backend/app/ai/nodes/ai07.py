"""AI-07 匯入表頭對應（FR-IMP-02）。輸出欄位索引，合法性由 `domain/imports/table.py` 的 valid_map 檢查。"""

from pydantic import BaseModel, ConfigDict

from app.ai.nodes.base import Node


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: int | None
    owner: int | None
    start: int | None
    end: int | None


SYSTEM = """你協助把一份專案時程表的欄位對應到系統欄位。
輸入是 JSON：headers（表頭，依欄位順序）、samples（前幾列資料，用來輔助判斷）。
輸出每個系統欄位對應的表頭索引（從 0 開始）：
- title：任務名稱
- owner：負責人
- start：開始日期
- end：結束日期、期限或完成日
找不到對應的欄位填 null，不要猜；同一個索引不要用兩次。"""

NODE = Node(system=SYSTEM, output=Output, max_tokens=2000)
