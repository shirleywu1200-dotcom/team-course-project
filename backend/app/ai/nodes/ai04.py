"""AI-04 目標回報草稿（FR-GOL-06、07）。payload 與輸出格式見 spec 5.3a（#72、#73）；設計見 docs/dev-b/ai-03-04-sdd.md。

這裡只約束外形與值域（SDD Q2）。draft 空白／字數／NUL 與 R3 對帳只在呼叫端（Dev-A）檢查。
FIGURE_KEYS 是 stats 的數字鍵（巢狀以「.」攤平）；呼叫端合併後由測試綁住兩者（SDD 2.3）。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.ai.nodes.base import Node

FIGURE_KEYS = ("linked", "avg_actual", "avg_expected", "overdue_count",
               "energy.high", "energy.mid", "energy.low", "progress_pct")


class Figure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: Literal[FIGURE_KEYS]
    value: float


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: str
    figures: list[Figure]


SYSTEM = """你協助把一個目標的統計，整理成對內的目標回報草稿。統計由程式算好，你只負責寫成文字。
輸入是 JSON：
- goal：type（growth＝能力成長、time＝時間配置、expectation＝績效期待）、title（目標名稱）、
  period（期間，例如 2026Q4）、energy_plan（預期精力：high 高、mid 中、low 低）。
- stats：linked（已關聯的完成工作件數）、avg_actual（實際平均星數）、avg_expected（事前預設平均星數）、
  overdue_count（逾期件數）、energy（實際精力分布，high／mid／low 各幾件）、progress_pct（進度百分比）、
  judgement（程式判讀：「一致」「建議檢視」，或 null）。
- tasks：關聯的工作任務。task_id、title、done_date（完成日）。私人任務不列在這裡，但已算進 stats。

輸出兩個欄位：
1. draft：台灣繁體中文，固定五段，依序如下，段落之間空一行：
   【目標】目標名稱（類型，期間，預期精力：高／中／低）
   【進度】已關聯 linked 件完成工作，進度 progress_pct%；
   實際平均 avg_actual 星，事前預設 avg_expected 星；逾期 overdue_count 件。
   【精力分布】高 energy.high 件、中 energy.mid 件、低 energy.low 件。
   【相關工作】每個任務一行，以「・」開頭：「・任務名稱（月/日）」，日期不補零，例如 11/9；
   tasks 為空時寫「・無可列出的工作」。
   【判讀】照抄 judgement；judgement 為 null 時寫「樣本不足，不下判讀。」
   某個統計值是 null 時，寫「無資料」，不要寫數字。
2. figures：draft 用到的每個 stats 數字各一項，key 用上面的鍵名（energy 的寫成 energy.high 這種形式），
   value 照抄 stats 的值。

數字規則（程式會逐一核對，不符就不顯示草稿）：
- 數字一律用阿拉伯數字，不用國字數字。
- 只能寫 stats 的值，或照抄目標名稱、期間、任務名稱、完成日裡本來就有的數字。
- 不自己計算：不寫差值、加總、比例、換算，也不寫 tasks 的筆數（linked 才是總件數）。
- 判讀段不寫任何門檻或樣本數。

其他規則：
- 依統計陳述事實，不推測原因，不評價目標、任務或任何人的表現或態度；預期精力和實際分布不同時，只陳述兩者。
- 不加開頭問候、結語或段落以外的說明。"""

NODE = Node(system=SYSTEM, output=Output, max_tokens=8000)
