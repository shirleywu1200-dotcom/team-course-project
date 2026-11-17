# AI-05 SDD：週報初稿的 prompt 與真實節點（Dev-B，13.4）

依據：spec 3.14（FR-RPT-01～05）、5.3a「AI-05 週報初稿」、FR-AI-05、FR-AI-06；13.4 SDD D-1（節點登記表）、D-3（重試只在呼叫端）、D-5（真實供應商測試）；#22（分工：Dev-A 呼叫端、Dev-B prompt 與節點）；CLAUDE.md 資安規則 2、3。
狀態：**已定案、實作中**（2026-11-17 Mora：Q1～Q3 都採 A；Q4 實測後再定）。分支 `dev-b/ai05-node`。

## 0. 現況盤點

- 呼叫端已在 main（Dev-A，#23）：`domain/weekly_service.py` 組 payload（`domain/ai05.build_payload`）→ `ai.call("AI-05", payload, timeout_s=20)` → `ai05.parse_output` 驗證 → `weekly_report.reconcile`（R4）。最多 3 次；`AIUnavailable` 與 R4 失敗立刻停；不存 `raw_output`。
- **缺的只有節點**：`ai/nodes/__init__.py` 的 `NODES` 沒有 AI-05，真實 client 一律丟 `AIUnavailable` → 週報在 `AI_PROVIDER=anthropic` 下永遠走退路事件清單；衡量值 1（R4 通過率，#48）也只會收到失敗資料。
- 評估樣本：Dev-A 在 #22 給了 3 個 payload（空的一週、小型、較完整的邊界案例），由測試種子實際跑 `build_payload` 產生。
- 依 #22「不改對方的檔案」：本票只新增／修改 `ai/nodes/`、測試與 `scripts/`，不動 `domain/ai05.py`、`weekly_service.py`、`weekly_report.py`。

## 1. 範圍與檔案

| 檔案 | 動作 | 內容 |
| --- | --- | --- |
| `backend/app/ai/nodes/ai05.py` | 新增 | `Output`、`SYSTEM`、`NODE` |
| `backend/app/ai/nodes/__init__.py` | 改一行 | `"AI-05": ai05.NODE` |
| `backend/tests/unit/test_13_4_real_ai.py` | 加測試 | 見第 4 節（既有的節點與真實 client 測試都在這個檔） |
| `scripts/e2e_seeds/weekly.sql` | 新增 | 驗收第 3 點用：一週內有完成、延期、下週到期的工作任務各數筆，另加一筆私人任務 |
| `scripts/eval_ai05.py`、`scripts/eval_data/ai05_cases.json` | 新增（依第 3 節 Q3） | 見第 5 節 |
| `docs/dev-b/13-4-sdd.md` | 改文件 | 第 1a 題改寫：AI-05 依 #22 由 Dev-B；AI-03、04 由 Dev-A 隨 Phase 9 登記（#50）；AI-02 依 D-01 不做 |

不做：改逾時、改重試、改 payload 或輸出格式（都屬 Dev-A 或需改 spec 5.3a）；姓名遮蔽（D-03 未決）。

## 2. 設計

### 2.1 `Output`（送給供應商的 JSON schema，也是 client 端的第一道驗證）

```python
class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section: Literal["done", "delay", "next"]
    task_id: int
    event_id: int | None

class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: str
    items: list[Item]
```

- 只約束**外形與值域**；跨欄位規則（`next` 的 `event_id` 必須為 null、`done`／`delay` 必填、`draft` 空白／20,000 字／NUL、重複合併）與 R4 仍只在 Dev-A 的 `parse_output`、`reconcile` 檢查。規則只有一處，改格式時不必兩邊同步。
- `section` 的值域和 `weekly_report.SECTIONS` 是同一份事實：用一則測試斷言兩者相等，任何一邊改了測試就紅（第 4 節 T2）。
- 真實 client 回傳 `Output(...).model_dump()`，形狀與 spec 5.3a 的輸出範例相同，`parse_output` 可直接吃。

### 2.2 `SYSTEM`（prompt 要點）

依 FR-RPT-02、03 與 FR-AI-06 寫成規則，不放任何使用者資料：

1. 輸入是 JSON：`week`、`done`、`delay`、`next`（欄位意義逐一說明，例如 `orig_due` 原訂、`latest_due` 最新、`blocked` 卡住）。
2. **只能用輸入裡有的任務與事件**：不得新增、合併或改寫任務；`draft` 提到的每個任務都要在 `items` 裡有一項（R4 不檢查 `draft` 文字，只能靠 prompt 約束，見 spec 3.14 已知限制）。
3. `items` 的規則：`done` 帶該項的 `event_id`；`delay` 從該項的 `event_ids` 取一個（取最後一個）；`next` 的 `event_id` 填 null。
4. `draft` 的格式見第 3 節 Q2。
5. **不評價、不推測原因**（FR-AI-06）：不寫「拖延」「表現不佳」「因為…所以延期」；payload 本來就沒有原因與自評。
6. 某段沒有資料時寫「本週無」，不要省略段落，也不要讓 `draft` 空白（空白算 `invalid_output`）。

### 2.3 `max_tokens`

先設 8,000（同 AI-01），涵蓋 `draft` 與 effort `low` 的思考；以第 5 節的評估實測 `output_tokens` 後再調。若截斷（`stop_reason=max_tokens`），client 丟 `AIInvalidOutput`，呼叫端會重試。

## 3. 待 Mora 確認（依「答錯的返工量」排序）

### Q1 `Output` 要多嚴？
- **A（建議）**：外形＋值域（上面 2.1）。後果：供應商依 schema 產生，`section` 打錯字、`task_id` 給字串這類錯誤在源頭就不會出現，少浪費重試；跨欄位規則仍只在 `parse_output` 一處。
- B：只約束外形（`items` 是任意物件陣列）。後果：和 `parse_output` 零重疊，但模型較容易回出值域外的 `section`，每次都要靠重試補。
- C：連跨欄位規則都寫進 schema。後果：和 `parse_output` 兩份規則，違反單一事實來源。

### Q2 `draft` 寫給誰看、長什麼樣？
spec 只說「提供文字供你複製」（FR-RPT-05），沒寫讀者與格式。
- **A（建議）**：寫給主管或團隊的週報，三個段落標題（本週完成／延期事項／下週重點與風險），每項一行條列，段落間空一行，日期寫成 `11/12`、不補零（`11/9`；第 1 輪評估後 Mora 定），延期寫「原訂 11/12 → 最新 11/18」，語氣中性、第三人稱。後果：可以直接複製貼上；格式固定，人工版修改量小。
- B：一段敘述文。後果：讀起來較順，但項目容易被合併或漏掉，和 `items` 對不齊，使用者要自己核對。

### Q3 怎麼驗 prompt？
- **A（建議）**：寫 `scripts/eval_ai05.py`，照 `eval_ai01.py` 的模式（先印估算費用、輸入 y 才送、`--max-cost` 上限、終端機只印統計）。指標：格式通過率（`parse_output` 不丟例外）、R4 通過率（用 payload 組出允許的（段落、任務、事件）組合比對）、延遲、token。案例＝#22 的 3 個樣本＋2 個自擬（一週 15～20 個任務的大型週，用來看 20 秒逾時夠不夠；一個含相似標題的任務，用來看會不會張冠李戴）。全部是虛構資料。約 2 小時。
- B：只加一則 `real_ai` 冒煙測試（樣本 2 跑一次，斷言格式與 R4 通過）。約 30 分鐘，但量不到 R4 通過率，也看不出大型週的延遲。

不論選哪個，都會加一則 `real_ai` 冒煙測試（第 4 節 T4）。

### Q4 大型週超過 20 秒怎麼辦？（先量再決定，不預先改）
逾時寫在 Dev-A 的 `weekly_service`。若 Q3 實測大型週超過 15 秒，再列選項（縮短 `draft` 規定、降 `max_tokens`、或請 Dev-A 為 AI-05 放寬逾時並改 spec 9.3）交 Mora。

## 4. 測試計畫（先紅後綠）

| # | 測試 | 先紅的原因 |
| --- | --- | --- |
| T1 | `NODES` 有 `"AI-05"`，且 `Output` 能驗證 spec 5.3a 的輸出範例 | 節點不存在 |
| T2 | `Item.section` 的值域等於 `weekly_report.SECTIONS` | 節點不存在 |
| T3 | `Output` 拒絕 `section="other"`、`task_id="abc"`、缺 `draft`（`"3"` 在 JSON 寬鬆模式會轉成 3，不算錯型別，與其他節點一致；11/17 Mora 定） | 節點不存在 |
| T4 | `real_ai` 標記：樣本 2 實際呼叫，`parse_output` 通過，且 R4 對 payload 允許的組合通過 | 節點不存在（CI 與 `AI_PROVIDER=off` 時跳過） |

既有測試只改一處：`test_unregistered_node_is_unavailable_without_calling` 原以 AI-05 當未登記節點，改用永不登記的 `AI-99`，意圖不變。跑全套一律加 `AI_PROVIDER=off`。

## 5. 評估與費用（Q3 選 A 時）

- 估算（Sonnet 5.5，每百萬 token 入 $2／出 $10）：單次約 2,500 輸入、1,500 輸出（含思考）→ 約 $0.02。一輪 5 個案例約 $0.1；預估調 3～5 輪，**合計約 $0.3～0.5**，在 $10 月上限內（11/16～17 已用約 $0.15）。
- 每輪結果記到 `../Dev-B工作紀錄/API設定追蹤.md`。
- 上線後每月約 4～5 次週報，約 $0.1。

## 6. 驗收標準

1. T1～T3 綠；後端全套（`AI_PROVIDER=off`）、ruff、gitleaks 通過。
2. 評估（或冒煙）：5 個案例格式通過率 100%、R4 通過率 100%；大型週延遲低於 15 秒。
3. 端對端（API）：週報前端 12.13 尚未完成（Dev-C），改以 API 驗證。本機 `AI_PROVIDER=anthropic`，`scripts/e2e_server.py` 載入 `weekly.sql`，呼叫週報產生端點一次，回應為 `ai_status=ok`、`validated=true`、`draft` 非空，且 `excluded_private=1`、`draft` 不含私人任務標題；走查完 `--drop`。
4. PR 由 Dev-A 審（配對 A→B），請他核對 prompt 對 R4 與各段定義的理解。
