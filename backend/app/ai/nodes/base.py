from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class Node:
    system: str               # 系統提示：任務說明與規則
    output: type[BaseModel]   # 輸出 schema：送給供應商約束格式，回來再用它驗證
    max_tokens: int
