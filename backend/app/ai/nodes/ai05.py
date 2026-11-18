"""AI-05 週報初稿（FR-RPT-02、03）。payload 與輸出格式見 spec 5.3a（#22）；設計見 docs/dev-b/ai-05-sdd.md。

這裡只約束外形與值域（SDD Q1）。跨欄位規則與 R4 對帳只在 `domain/ai05.parse_output`、
`domain/weekly_report.reconcile`（Dev-A）檢查；section 值域與 `weekly_report.SECTIONS` 由測試綁成同一份。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.ai.nodes.base import Node


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: Literal["done", "delay", "next"]
    task_id: int
    event_id: int | None


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: str
    items: list[Item]


SYSTEM = """你協助把一週的工作紀錄整理成週報初稿，給主管或團隊閱讀。
輸入是 JSON：
- week：本週起訖日期（start、end）。
- done：本週完成的任務。task_id、title（任務名稱）、owner（負責人）、done_date（完成日）、event_id（完成事件）。
- delay：本週延期、目前仍延期的任務。task_id、title、owner、orig_due（原訂日）、latest_due（最新日）、
  event_ids（本週的延期事件）。
- next：下週重點與風險。task_id、title、owner、latest_due（最新日）、blocked（是否卡住）。
  latest_due 早於下週一的是已逾期。

輸出兩個欄位：
1. draft：週報文字，用台灣繁體中文，固定三個段落，依序是：
   【本週完成】
   【延期事項】
   【下週重點與風險】
   段落之間空一行。每個任務一行，以「・」開頭，寫任務名稱與負責人。
   日期寫成「月/日」，不補零，例如 11/9、12/5、11/12：
   - 本週完成：「・任務名稱（負責人）11/12 完成」
   - 延期事項：「・任務名稱（負責人）原訂 11/12 → 最新 11/18」
   - 下週重點與風險：「・任務名稱（負責人）期限 11/19」；卡住的加「，卡住」；已逾期的加「，已逾期」
   某一段沒有任務時，該段寫「・本週無」，段落標題仍要保留。
2. items：draft 裡寫到的每個任務各一項：
   - 本週完成：section 填 done，event_id 填該任務的 event_id。
   - 延期事項：section 填 delay，event_id 填該任務 event_ids 的最後一個。
   - 下週重點與風險：section 填 next，event_id 填 null。
   同一個任務出現在兩段時，兩段各一項。

規則：
- 只能寫輸入裡有的任務，task_id 與 event_id 從輸入原樣抄回；不要新增、合併、拆分或改名任務。
- 依輸入的資料陳述事實，不推測延期或卡住的原因，也不評價任何人的表現或態度。
- 不加開頭問候、結語或段落以外的說明。"""

NODE = Node(system=SYSTEM, output=Output, max_tokens=8000)
