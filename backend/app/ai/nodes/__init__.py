"""AI 節點登記表（13.4 SDD D-1）：node_id → 該節點的 prompt 與輸出 schema。

表內沒有的節點，真實 client 丟 AIUnavailable，呼叫端走 spec 6.6 退路。
新增節點：在本目錄加一個檔案定義 `NODE`（型別見 base.py），再登記到下方 NODES。
"""

from app.ai.nodes import ai01
from app.ai.nodes.base import Node

NODES: dict[str, Node] = {
    "AI-01": ai01.NODE,
}
