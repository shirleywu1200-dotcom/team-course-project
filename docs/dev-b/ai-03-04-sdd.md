# AI-03／AI-04 SDD：目標關聯建議與目標回報草稿的 prompt 與節點（Dev-B，Phase 9）

依據：spec 3.13 FR-GOL-03、05、06、07、FR-AI-06；5.3a「AI-03」「AI-04」（PR #73，#72 定案）；5.13 目標統計；13.4 SDD D-1（節點登記表）、D-3（重試只在呼叫端）；`ai-05-sdd.md`（同類做法與基準）；CLAUDE.md 資安規則 2。
狀態：**已定案、實作中**（2026-11-18 Mora：Q1～Q5 都採 A）。分支 `dev-b/ai-03-04-sdd`。

## 0. 現況盤點

- 格式已定案：#72 Dev-A 提案、Dev-B 回覆兩題，Dev-A 寫回 5.3a 開 PR #73（Dev-C 審、11/18 Dev-B 已留言確認一致）。
- **呼叫端還沒有**：Phase 9 第三片（9.7、9.10）由 Dev-A 做，資料模型等 #47 G1、G2，端點 `POST /goal-links/suggest` 等 G3。R3 對帳（FR-GOL-07）也在呼叫端。
- **分工以 #72 為準**：#50（已關閉）原寫「AI-03、AI-04 由 Dev-A 隨 Phase 9 登記節點」；#72 改成「呼叫端是 Dev-A，prompt 與節點是 Dev-B」（比照 #22 的 AI-05）。兩處說法不同，開工前在 #72 留言請 Dev-A 確認節點由 Dev-B 登記，避免兩人各寫一份。
- 節點不依賴呼叫端：真實 client 只看 `NODES` 表與 `Output`，可以先做、先用真實供應商評估。
- spec 5.13 仍寫 `GET /goal-links/pending`「含 AI-03 建議」，和 5.3a 的新做法不一致；屬 G3 裁定後 Dev-A 一併改，本票不動。

## 1. 範圍與檔案

| 檔案 | 動作 | 內容 |
| --- | --- | --- |
| `backend/app/ai/nodes/ai03.py` | 新增 | `Item`、`Output`、`SYSTEM`、`NODE` |
| `backend/app/ai/nodes/ai04.py` | 新增 | `Figure`、`Output`、`SYSTEM`、`NODE`、`FIGURE_KEYS` |
| `backend/app/ai/nodes/__init__.py` | 改兩行 | `"AI-03"`、`"AI-04"` |
| `backend/tests/unit/test_13_4_real_ai.py` | 加測試 | 見第 4 節 |
| `scripts/eval_ai03.py`、`scripts/eval_ai04.py` | 新增 | 照 `eval_ai05.py` 的模式，見第 5 節 |
| `scripts/eval_data/ai03_cases.json`、`ai04_cases.json` | 新增 | 全虛構資料 |
| `docs/dev-b/13-4-sdd.md` | 改文件 | 第 1a 題：AI-03、04 改由 Dev-B 依 #72 補節點 |

不做：呼叫端、payload 組裝、R3 對帳的正式實作、端點（Dev-A）；改 5.3a 格式（要先回 #72）。

## 2. 設計

### 2.1 AI-03 `Output`

```python
class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: int
    goal_id: int | None
    reason: str

class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Item]
```

- 只約束外形（同 AI-05 Q1-A）。`reason` 200 字、NUL、`task_id`／`goal_id` 不在 payload 整項丟棄、同一任務重複，都留給呼叫端（重複的處理已在 #73 請 Dev-A 定）。

### 2.2 AI-03 `SYSTEM` 要點

1. 輸入：`goals`（goal_id、type 三類的意義、title、period）、`tasks`（task_id、title、done_date）。
2. 每個任務回**剛好一項**；沒有合適目標時 `goal_id` 填 null，不要硬配。
3. 判斷依據只有任務標題與目標標題、類型、期間（完成日不在期間內的，不建議該目標）。
4. `reason`：一句話、50 字內（留給 200 字上限緩衝），只說「內容和目標哪裡相關」；不評價任務重要性、品質或人（FR-AI-06）。
5. 只能用輸入裡的 id，原樣抄回。

### 2.3 AI-04 `Output`

```python
FIGURE_KEYS = ("linked", "avg_actual", "avg_expected", "overdue_count",
               "energy.high", "energy.mid", "energy.low", "progress_pct")

class Figure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: Literal[FIGURE_KEYS]   # 值域：stats 的數字鍵（judgement 不是數字，不列）
    value: float

class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: str
    figures: list[Figure]
```

- `key` 用值域約束（同 AI-05 `section`）：供應商依 schema 產生，不會寫出 `stats` 沒有的鍵名，R3 第 1 點只剩「值相等」會失敗。
- `FIGURE_KEYS` 與 Dev-A 呼叫端的 `stats` 鍵是同一份事實：呼叫端合併後加一則測試綁住兩者（同 AI-05 T2），現在先以 5.3a 範例的鍵為準。

### 2.4 AI-04 `SYSTEM` 要點

1. 輸入：`goal`（type、title、period、energy_plan）、`stats`（各鍵意義）、`tasks`（只有工作範圍的任務標題與完成日）。
2. `draft` 格式見 Q3。
3. **數字規則**（R3）：數字一律用阿拉伯數字；只能寫 `stats` 的值，或照抄目標標題、期間、任務標題、完成日裡本來就有的數字；**不自己算**（不寫差值、百分比換算、筆數加總）；用到的 `stats` 數字逐一列進 `figures`。
4. `judgement` 照抄；null 時寫「樣本不足，不下判讀」，**不寫門檻數字**（見 Q4）。
5. 不評價、不推測原因（FR-AI-06）：例如不寫「精力分配不當」「表現優秀」；`energy_plan` 和實際分布不同時只陳述兩者。
6. 私人範圍的任務不在 `tasks` 裡，但已算進 `stats`：不要寫「共 N 項工作」這種把 `tasks` 筆數當總數的句子（`linked` 才是總數）。

### 2.5 `max_tokens`

兩個節點先設 8,000（同 AI-01、AI-05），評估後依實測 `output_tokens` 調整。

## 3. 待 Mora 確認（依「答錯的返工量」排序）

### Q1 評估 R3 誤判率時，對帳用誰的實作？
#72 承諾「誤判率由 Dev-B 實測」，但 R3 對帳寫在 Dev-A 的呼叫端，目前還沒寫。
- **A（建議）**：`eval_ai04.py` 內依 5.3a 寫一個暫用的對帳函式，先量；Dev-A 的函式合併後，腳本改 import 正式函式、刪掉暫用的，再重跑一輪當基準線。後果：不必等 Dev-A，6 天內來得及；暫用函式只活在評估腳本、不進產品，量到的規則和正式版差異靠「合併後重跑一輪」抓。
- B：由 Dev-B 寫正式的 R3 純函式（`domain/goal_report.py`），Dev-A 呼叫端直接用。後果：規則只有一份，量到的就是上線的；但改了 5.3a 寫的分工，要先在 #72 取得 Dev-A 同意，且 Dev-B 多一張要審的 PR。
- C：等 Dev-A 寫完再量。後果：零重複，但 Phase 9 卡在 #47 G1、G2，可能到 11/22 後才開始調 prompt，誤判率太高時來不及改允許名單。

### Q2 `Output` 要多嚴？
- **A（建議）**：外形＋值域（2.1、2.3），同 AI-05 的 Q1-A。後果：跨欄位規則只在呼叫端一處；AI-04 的 `key` 由 schema 擋住拼錯。
- B：AI-04 的 `key` 也不設值域（任意字串）。後果：和呼叫端零重疊，但拼錯鍵名會讓 R3 第 1 點失敗、浪費一次重試。

### Q3 AI-04 的 `draft` 寫給誰看、長什麼樣？
FR-GOL-06 只說「對內草稿」，人工版另存。
- **A（建議）**：給主管的目標回報，200～400 字，固定四段：
  ```
  【目標】學會 SQL 視窗函式（能力成長，2026Q4，預期精力：高）
  【進度】已關聯 3 件完成工作，進度 100%；實際平均 4 星，事前預設 3.3 星；逾期 1 件。
  【精力分布】高 2 件、中 1 件、低 0 件。
  【相關工作】・報表查詢改寫（11/12）…
  【判讀】樣本不足，不下判讀。
  ```
  後果：數字位置固定，R3 誤判少、使用者好核對；讀起來像表格轉文字，人工版要潤飾。
- B：一段敘述文。後果：讀起來順，但模型容易自己加總或換算（「超出預期 0.7 星」），R3 誤判率高。

### Q4 `judgement=null` 時，「不到 5 筆」的 5 怎麼處理？
`min_sample`（5）不在 AI-04 payload 的 `stats` 裡，也不在允許名單。草稿寫「樣本不到 5 筆」就會被 R3 擋下，但其實沒寫錯。
- **A（建議）**：prompt 規定 null 時寫「樣本不足，不下判讀」、不寫門檻數字。後果：不改 5.3a；評估案例專門放一題看模型守不守。
- B：請 Dev-A 把 `min_sample` 加進 payload 與允許名單。後果：句子較完整，但要回 #72 改 5.3a 格式，還要再過一次審查。

### Q5 AI-03 要不要量「建議準確率」？
- **A（建議）**：要。每個案例在 JSON 裡標「預期目標」（含「沒有合適目標」），算建議與預期一致的比例。後果：多花約 20 分鐘標註；可以事先估建議好不好用。門檻借用 1.3 節 AI-01 的採用率 70%（1.3 只對 AI-01 訂了門檻，AI-03 沒有，這裡只當參考）。
- B：只量格式與 id 合法。後果：省時間，但上線前不知道建議好不好用。

## 4. 測試計畫（先紅後綠）

| # | 測試 | 先紅的原因 |
| --- | --- | --- |
| T1 | `NODES` 有 `"AI-03"`、`"AI-04"`，且兩個 `Output` 能驗證 5.3a 的輸出範例 | 節點不存在 |
| T2 | AI-03 `Output` 拒絕 `goal_id="abc"`、缺 `reason`、多出欄位 | 節點不存在 |
| T3 | AI-04 `Output` 拒絕 `key="total"`、缺 `figures`；`FIGURE_KEYS` 涵蓋 5.3a 範例 `stats` 的全部數字鍵（巢狀攤平） | 節點不存在 |
| T4 | `real_ai`：AI-03、AI-04 各跑一個樣本，`Output` 驗證通過；AI-03 每個任務都有一項、id 都在 payload；AI-04 `figures` 都等於 `stats`（R3 第 1 點；第 2 點由評估腳本量，不在測試裡另寫一份） | 節點不存在（CI 與 `AI_PROVIDER=off` 時跳過） |

既有測試不改。跑全套一律加 `AI_PROVIDER=off`。

## 5. 評估與費用

案例（全虛構，payload 照 5.3a 範例手寫）：

- **AI-03（5 題）**：明確對應；沒有合適目標；兩個目標都像（相似標題）；完成日在目標期間外；20 筆上限（20 個任務、4 個目標，看延遲）。
- **AI-04（6 題）**：`judgement=null`（Q4）；判讀「一致」；「建議檢視」（預期高、實際多為低）；目標標題含數字（「讀完 3 本書」）；小數（`avg_expected` 3.3）與 0 值；`tasks` 為空（全部是私人任務，只有統計）。

指標：

| 節點 | 指標 |
| --- | --- |
| AI-03 | 格式通過率、id 合法率、覆蓋率（每個任務剛好一項）、準確率（Q5）、`reason` 最長字數、延遲 |
| AI-04 | 格式通過率、R3 第 1 點與第 2 點各自通過率；**R3 失敗逐筆人工判定「真錯」或「誤判」**，誤判率＝誤判 ÷ 失敗；延遲 |

- **R3 第 2 點的已知限制（實作時以假 client 驗出）**：允許名單含 `done_date` 拆出的日，1～31 的數字很容易「剛好在名單裡」。例：案例 `null_judgement` 有一筆 11/05，草稿寫「樣本不到 5 筆」仍會通過。也就是第 2 點**會漏抓**與日期或統計值撞號的錯數字，不會因此誤判。評估照實記錄，不在本票改規則；若要收緊（例如日期只在「月/日」寫法出現時才放行），回 #72 與 Dev-A 討論。
- 照 `eval_ai05.py`：先印估算、輸入 y 才送、`--max-cost` 上限、終端機只印統計，逐案 CSV 存到 `EVAL_OUT_DIR`。
- 估算（Sonnet 5.5，入 $2／出 $10 每百萬 token）：單次約 1,500 輸入、1,200 輸出 → 約 $0.015。一輪 11 題約 $0.17；預估調 3～4 輪，**合計約 $0.5～0.7**，在 $10 月上限內（11 月已用約 $0.25）。**跑第一輪前會再問 Mora。**
- 每輪結果記到 `../Dev-B工作紀錄/API設定追蹤.md`。

## 6. 驗收標準

1. T1～T3 綠；後端全套（`AI_PROVIDER=off`）、ruff、gitleaks 通過。
2. 評估：兩節點格式通過率 100%；AI-03 id 合法率、覆蓋率 100%，準確率 ≥ 70%（參考值，見 Q5）；AI-04 R3 誤判率 0（11 題內），真錯的不算 prompt 失敗但要記錄；最慢延遲低於 15 秒（逾時 20 秒）。
3. 端對端：等 Dev-A 呼叫端合併後，以 API 各打一次（`ai_status=ok`、AI-04 `validated=true`），並用正式 R3 函式重跑 AI-04 評估一輪（Q1-A）。這一點不擋本票 PR，另記在 Dev-B 待辦。
4. PR 由 Dev-A 審（配對 A→B），請他核對 prompt 對 R3 與 payload 欄位的理解。

## 7. 驗收結果（2026-11-18，claude-sonnet-5-5、effort low）

之後改 prompt、換模型或換成呼叫端的正式 R3 函式時，以這裡的數字當基準線重跑。

| 項目 | 結果 |
| --- | --- |
| 1. 測試 | T1～T3 綠；後端全套（`AI_PROVIDER=off`）938 passed、ruff、gitleaks 通過 |
| 2. AI-03 第 1 輪 | 格式、id 合法、覆蓋皆 5/5；準確 29/29；reason 最長 56 字；最慢 6.2 秒（20 筆） |
| 2. AI-04 第 1 輪 | 格式、R3 第 1 點、第 2 點皆 6/6；`figures` 每案都列滿 8 個鍵；最慢 9.8 秒 |
| 人工看稿 | AI-04：`judgement=null` 三案都寫「樣本不足，不下判讀。」、沒寫門檻；無評價用詞；日期不補零；`tasks` 為空寫「・無可列出的工作」。AI-03：period 案正確以「完成日不在 2026Q3」不配對 |
| 費用 | 約 $0.07 |

- 第 1 輪就全過，**不再調 prompt**。限制：案例是 Dev-B 自擬、標題語意清楚，準確率 100% 不代表真實任務標題也一樣；上線後以 `ai_feedback` 的 `accepted` 比例觀察。
- 未做：驗收第 3 點（端對端）與用正式 R3 函式重跑，等 Dev-A 呼叫端。

## 8. 時程

11/24 12:00 前完成。節點與評估不依賴呼叫端：SDD 同意後約 1 天（測試＋節點半天、評估 2～3 輪半天）；端對端視 Dev-A 進度。
