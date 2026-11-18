# 個人大總管 APP 功能規格（spec.md）

| 項目 | 內容 |
| --- | --- |
| 版本 | v0.1（對應互動原型 v4、序列圖 1–7、AI 節點盤點 v0.1） |
| 日期 | 2026-11-12 |
| 技術棧 | Python 3.12 + FastAPI、React 18 + TypeScript、PostgreSQL（2026-11-13 由 SQLite 改定，見 `docs/decisions.md` DA-01） |
| 使用者 | 單一使用者（個人使用），不建帳號；負責人以名字表示 |
| 階段 | P1 專案閉環＋單點＋每日；P2 完成回報與精力；P3 目標與精力分析 |

文件中的標記：**〔假設〕** 是我暫定的數值或做法，要在實測（關卡 G2）或決策後校正；**〔待決〕** 是需要你裁定的事，列在第 9 章。

---

## 1. 功能概述／目標

### 1.1 要解決的問題

一位能獨立負責專案、或負責專案中一個 WBS 的專業工作者，每天的承諾散在三個地方：群組對話裡別人說「延到 11/18」、自己手上的單點事項、專案計畫表裡的日期。結果是：

1. 專案進度靠人工從對話裡撈，漏了就失真，週報要重新拼湊。
2. 預計完成日改了很多次，卻不知道原本承諾是哪天，也說不清自己的時間管理到底變好還是變差。
3. 事情做完沒有留下「做得好不好、花了多少精力」，無法回頭看精力與目標的關係。

### 1.2 產品定位

這是一本**由你確認的承諾帳**。AI 只提議，你決定，系統寫入。

三條不可破的原則，後面所有需求都從它們推出來：

| 原則 | 意思 |
| --- | --- |
| 確認前不入統計 | AI 產生的候選與草稿，在你確認前不改任何正式紀錄，也不進任何統計。 |
| 原訂日期不因改期覆寫 | 改期只改「最新預計」。唯一例外是「基準更正」，需二次確認，且舊值永久留在歷程。 |
| 歷程只增不改 | 所有變更寫成一筆事件；更正也是新增一筆，不改舊事件。 |

### 1.3 目標與衡量

| 目標 | 衡量（〔假設〕，G2 校正） |
| --- | --- |
| 專案進度可信 | 週報中每個延期與完成，100% 對得上歷程事件。量法：AI-05 回傳格式正確的嘗試中 R4 對帳通過的比例（失敗記 `error='R4_MISMATCH'`）；人工版不經對帳，不納入（2026-11-17 裁定，#34） |
| 確認成本可控 | 每日確認時間不超過設定上限（預設 5 分鐘）。以處理時間跨度近似：每天第一筆到最後一筆候選處理的分鐘數，只會高估（#34） |
| AI 候選有用 | AI 建議採用率（含修改後確認）≥ 70%：`ai_feedback` 中 AI-01 候選的 `accepted`＋`edited` ÷ 已處理候選；改建新任務（`changed`）不算採用，仍在分母（#34） |
| 時間管理可盤點 | 負責人是我的日期調整，註記完成率 ≥ 80% |
| 完成回報不成負擔 | 完成事件中，完成回報填寫率 ≥ 70% |

### 1.4 範圍

**包含（P1–P3）**：啟用設定與星數量表；專案建立、匯入；單點任務；候選抽取與確認；預計完成日調整與時間管理註記；整批順延；基準更正；專案修改歷程；甘特圖；完成回報（星數、精力）；目標與精力；週報與目標回報草稿。

**不包含**：多人協作與帳號權限；會議錄音與轉逐字稿（以逐字稿文字入口取代，逐字稿入口屬後續階段）；行事曆雙向同步；週報由系統代發；任務相依關係；基準版本化。

---

## 2. 使用情境／使用者故事

角色固定為「我」（使用者）。其他負責人只是名字。

### 2.1 啟用與設定

- US-01 作為新使用者，我想用三個問題讓系統產生我自己的星數量表，這樣之後評「達成度」有符合我標準的定義。
- US-02 作為新使用者，我想綁定專案群組或只用貼上入口，這樣不必依賴 bot 也能用。
- US-03 作為使用者，我想定義「精力高／中／低」對我的意思，這樣之後自評有一致標準。

### 2.2 專案與任務

- US-04 作為專案負責人，我想貼上試算表匯入 WBS，並在保存前看到診斷，這樣不會把壞資料帶進基準。
- US-05 作為專案負責人，我想在匯入後逐項改最新預計日，且原訂日期保持不變，這樣我看得到每項延了多少。
- US-06 作為專案負責人，客戶改需求導致整個專案順延 3 天，我想一次勾選多項任務順延，而不是逐項改。
- US-07 作為使用者，我想新增單點任務（含完成條件、預設星數、提醒），並同樣能改預計完成日。
- US-08 作為專案負責人，我發現匯入時原訂日期寫錯，想更正基準，但要有足夠的阻力，避免我事後把延期改小。

### 2.3 收件與確認

- US-09 作為使用者，我想貼上群組對話，由 AI 找出「延期、完成、卡住」的候選，並附原句，我逐項確認。
- US-10 作為使用者，疑問句或「可能」這類話不應被當成延期，我只想在「待釐清」區裁定。
- US-11 作為使用者，我想把每天要確認的候選合併成一次處理，上限在我設定的分鐘數內。

### 2.4 時間管理與精力

- US-12 作為使用者，每次提前或延後我自己負責的任務，我想被問「要不要計入時間管理變好／變差」，也可以先調整、晚點再註記。
- US-13 作為使用者，因客戶造成的延後，我想標「不計入」，這樣統計不會把我控制不了的事算成我的問題。
- US-14 作為使用者，完成事件時，我想回報實際達成星數與自評精力，這樣事後能對照事前預設。
- US-15 作為使用者，我想看時間管理統計，並看到被標「變差」的任務完成時的精力分布。

### 2.5 目標與週報

- US-16 作為使用者，我想把完成事件關聯到能力成長、時間配置、績效期待三類目標，並看到目標與精力的對照。
- US-17 作為使用者，樣本太少時，我想只看分布，不要被系統下結論。
- US-18 作為專案負責人，我想拿到週報初稿，每一項都能追到歷程，再自己改成人工版並決定是否送出。

### 2.6 歷程與資料控制

- US-19 作為使用者，我想依專案、類型、任務篩選修改歷程，看到前值、後值、原因與來源。
- US-20 作為使用者，我想設定原文保存期限、匯出資料、刪除原文，且刪除後任務與歷程仍保留。

---

## 3. 功能需求

編號規則：`FR-<模組>-<序號>`。每條都要有對應驗收標準（第 7 章）。階段標在模組標題。

### 3.1 FR-SET 啟用與設定（P1）

- FR-SET-01 首次啟動進入啟用精靈，共 6 步：歡迎、角色與範圍、收件來源、星數量表、目標與精力、確認節奏。可「略過」，略過時採預設值並使用量表 v0。
- FR-SET-02 設定項目：預設範圍（工作／私人）、角色、週報對象（主管／客戶／不需要）、每日確認時間（12:00／18:00／21:00）、確認時間上限（3／5／10 分鐘）、提醒時機、原文保存期限（30／90／180 天）、精力高中低的定義文字、啟用的目標類型。
- FR-SET-03 設定隨時可重新調整。調整量表會產生新版本，不修改舊版本。
- FR-SET-04 預設星數量表 v0 為五級：未達成、部分達成、符合預設、優於預設、遠超預設。

### 3.2 FR-RUB 星數量表（P1，AI-06）

- FR-RUB-01 量表由 5 句描述組成，依序對應 1–5 星，版本號遞增，**已確認的版本不可修改**。
- FR-RUB-02 量表訪談為三個選擇題：什麼程度算符合預設、什麼情況給 5 顆星、不同類型任務是否用不同標準。
- FR-RUB-03 AI 依三個回答產生量表草稿；草稿逐句可改；你確認後才成為新版本。不確認則沿用目前版本。
- FR-RUB-04 「依任務類型分開量表」本版只記錄回答，不實作（所有任務共用同一套）。
- FR-RUB-05 每筆完成回報記錄當時使用的 `rubric_id`；跨版本的星數不直接合併比較。

### 3.3 FR-PRJ 專案（P1）

- FR-PRJ-01 建立專案：名稱必填；範圍、週報對象；收件來源可為「貼上入口」或已告知成員的 LINE 群組。建立時寫一筆 `project` 事件（`field='created'`，DA-06）。
- FR-PRJ-02 編輯專案（名稱、範圍、週報對象）。**每個變更欄位各寫一筆 `project` 事件**，記前值與後值。沒有實際變更時不寫事件。
- FR-PRJ-03 專案不刪除，只封存（`archived_at`）。封存後預設不出現在列表，歷程保留。封存寫一筆 `project` 事件（`field='archived_at'`，DA-06）。
- FR-PRJ-04 專案現況頁顯示：完成數、已延期數（最新預計 > 原訂）、待確認候選數（註明不計入下方數字）、甘特圖、任務表。
- FR-PRJ-05 甘特圖每列有「進行區間」（開始到最新預計）、「原訂基準框」（開始到原訂，固定）、「延後區間」（原訂之後到最新預計）；已完成任務以完成日為終點；今天以直線標示。最新預計早於原訂時，仍顯示基準框，並在列標籤標「提前 n 天」。

### 3.4 FR-IMP 專案匯入（P1，AI-07）

- FR-IMP-01 匯入入口為貼上表格（逗號或 Tab 分隔，首列表頭）。檔案上傳列為後續。單次最多 500 列、50,000 字元；超過任一上限回 413 `PAYLOAD_TOO_LARGE`（2026-11-16 裁定，PR #20 Q5）。
- FR-IMP-02 表頭先由規則比對（任務／名稱、負責人、開始、結束／期限／完成）；規則辨認不出時才呼叫 AI-07 建議對應，並顯示對應預覽由你確認。匯入目標為私人範圍的既有專案時不呼叫 AI-07、不寫 `ai_runs`，回 `ai_status="unavailable"`、`mapped_by=null`，可帶 `column_map` 手動對應；`target="new"` 視為工作範圍（Phase 6 SDD Q4；PR #20 B1 比照；資安規則 2）。
- FR-IMP-03 日期格式接受 `YYYY-MM-DD`、`M/D`（無年份時依專案期間推年）。無法解析視為缺日期。
- FR-IMP-04 診斷規則：
  - 錯誤（該列不匯入，除非補正或略過）：缺任務名稱；缺結束日期；結束日期早於開始日期。
  - 注意（可匯入）：缺負責人，預設為「我」；缺開始日期，以結束前 3 天代入；名稱與前列重複，由你決定是否保留。
- FR-IMP-05 未處理的錯誤列**不匯入也不猜測**。保存時至少要有 1 列可匯入。
- FR-IMP-06 保存時為每列建立任務，`orig_due = latest_due = 結束日期`，`star_source = import_default`，並寫一筆 `baseline` 事件（匯入項數、略過列數）。保存是單一交易，全成功或全失敗。
- FR-IMP-07 可匯入到既有專案或新建專案。

### 3.5 FR-TSK 任務（P1）

- FR-TSK-01 建立任務欄位：標題（必填）、負責人（名字，預設「我」）、期限（必填）、範圍、專案（可空，空為單點任務）、完成條件（選填）、提醒、關聯目標（選填）、預設星數（1–5，預設 3）。
- FR-TSK-02 建立時 `orig_due = latest_due = 期限`，並寫 `task` 事件。
- FR-TSK-03 預設星數來源 `star_source` 由伺服器判定：沒有 AI 建議時為 `self`；有 AI 建議且未改為 `ai_accepted`；有 AI 建議但改了為 `ai_edited`；匯入為 `import_default`。前端不可直接指定來源。
- FR-TSK-04 狀態為 `todo`、`doing`、`done`；另有獨立旗標 `blocked`。狀態變化寫 `status` 事件。`todo`、`doing` 之間以 `POST /tasks/{id}/status` 切換；改為 `done` 一律走 `/complete`（DA-08）。狀態或卡住設成目前的值回 `NO_CHANGE`，不寫事件（DA-22）。已完成任務再按完成回 409 `TASK_DONE`（DA-16）。
- FR-TSK-05 任務詳情顯示：負責人、原訂（固定）、最新預計、與原訂差距、預設星數與來源、完成回報、此任務的歷程。
- FR-TSK-06 更改負責人（名字）寫一筆 `task` 事件。更改後，**過去事件的「是否為我的任務」判斷不變**。改為相同名字回 `NO_CHANGE`（DA-17）。
- FR-TSK-07 已完成任務：不可調整預計完成日、不可更正基準、不可再標卡住。
- FR-TSK-08 建立任務可指定開始日（選填）；明確填入晚於期限的開始日時拒絕（`VALIDATION_ERROR`，`details.fields` 含 `start`）。未填時沿用 DA-07：今天，期限早於今天時用期限當天。（2026-11-15 產品負責人裁定，PR #1 審查 A2、B1）
- FR-TSK-09 調整開始日：只改 `start_date`，不問原因與註記；寫一筆 `task` 事件（`field='start_date'`，`delta_days`、`mark` 為 NULL，不進時間管理統計），`version` 加 1。已完成回 `TASK_DONE`；等於目前值回 `NO_CHANGE`；超出「今天前 365 天到後 730 天」回 `DATE_OUT_OF_RANGE`；晚於最新預計日仍成功，回警告 `START_AFTER_DUE`。不新增錯誤碼；整批順延仍不動開始日。（同上）

### 3.6 FR-DUE 預計完成日調整（P1）

- FR-DUE-01 任何未完成任務都可調整「最新預計日」。入口：專案現況表格的調整欄、任務詳情、確認延期候選後。
- FR-DUE-02 調整**只改 `latest_due`**，不動 `orig_due`。
- FR-DUE-03 驗證：任務已完成拒絕（`TASK_DONE`）；新日期等於目前值拒絕（`NO_CHANGE`）；日期超出「今天前 365 天到後 730 天」拒絕（`DATE_OUT_OF_RANGE`）；新日期早於開始日只回警告，不阻擋。
- FR-DUE-04 每次調整寫一筆 `due` 事件：前值、後值、`delta_days`（提前為負、延後為正）、原因、備註、是否為我的任務、時間管理註記。
- FR-DUE-05 原因為固定選項。提前：提早完成條件達成、工作量比預期少、前置工作提早到位、其他。延後：估計不準（我低估）、被其他事插隊（我自己排程）、等對方或客戶回覆（外部）、需求變更（外部）、資源或環境未到位（外部）、其他。
- FR-DUE-05a 原因與註記**只由使用者選擇**。系統與 AI 都不預填、不推測。確認延期候選時，AI-01 只提供新日期與原句，原因欄位一律為空待選。因此 `adjust_due` 的原因可為空；有給時必須是該方向的選項，否則 `VALIDATION_ERROR`。手動調整畫面（12.2）把原因設為必選（DA-09）。
- FR-DUE-06 並行保護：請求帶 `expected_version`（任務版本號），不符回 `STALE_VERSION`。

### 3.7 FR-MRK 時間管理註記（P1）

- FR-MRK-01 **負責人為「我」**的任務，調整日期時必須回答註記：`better`（變好）、`worse`（變差）、`none`（不計入）；或明確選「稍後註記」（`defer_mark=true`，註記留空）。兩者皆無時拒絕（`MARK_REQUIRED`）；兩者同時給回 `VALIDATION_ERROR`，訊息說明擇一（DA-10）。
- FR-MRK-02 **負責人不是我**的任務，不詢問註記；事件記 `mine=0`，不進時間管理統計。請求中帶了註記時忽略，並在 `warnings` 回 `MARK_IGNORED`（DA-11）。
- FR-MRK-03 原因屬外部（以「外部」標記的原因）時，介面提示建議「不計入」。**這只是提示，系統不預選、不代判。**
- FR-MRK-04 補註記與改註記：對 `mine=1` 且 `delta_days≠0` 的日期事件，新增一筆 `annotation` 事件，`ref_event_id` 指向原事件。原事件不改。補註記可帶 `reason`，有給時依原日期事件的方向（提前或延後）檢查選項；`annotation` 事件的 `mine` 沿用原事件，不依現在的負責人（DA-13）。
- FR-MRK-05 有效註記 = 指向該日期事件的最新一筆 `annotation`；沒有則取原事件的註記；皆空為「未註記」。
- FR-MRK-06 時間管理統計口徑：只算 `mine=1`、`delta_days≠0`、有效註記非空的日期事件。輸出變好次數與提前總天數、變差次數與延後總天數、不計入次數、未註記次數；**未註記與不計入不進變好／變差**。
- FR-MRK-07 統計另輸出「被標變差的任務完成時的精力分布」（高、中、低、尚未完成），供時間與精力盤點。分布以任務計數，同一任務多次被標變差只算一次；沒有完成回報的任務算在「尚未完成」（DA-12）。判讀由程式規則計算，不用 AI（FR-AI-06）。規則如下（2026-11-16 產品負責人裁定，#15）：
  - 樣本＝變好次數＋變差次數（FR-MRK-06 口徑）。樣本少於 `min_sample`（5）時 `judgement=null`，`judgement_note`＝「樣本 {n} 筆，不到 {min_sample} 筆，只顯示不下結論」。
  - 樣本足夠時，`judgement` 三選一：變好多於變差為「時間管理偏向變好」，變差多於變好為「偏向變差，建議檢視」，相等為「持平」。`judgement_note`＝「變好 {b} 次、變差 {w} 次。」
  - 精力洞察：分母為精力分布四格合計（被標變差的任務數，含「尚未完成」）；高、中、低某一級的任務數**嚴格大於**分母的一半時，`judgement_note` 再接「變差多集中在{高／中／低}精力任務。」剛好一半不算；「尚未完成」不算一個等級。
- FR-MRK-08 整批順延產生的事件依本節規則處理註記。基準更正的 `baseline` 事件沒有 `delta_days`，不屬於 FR-MRK-06 的統計口徑，所以不詢問、不寫註記（DA-14）。

### 3.8 FR-BLK 整批順延（P1）

- FR-BLK-01 入口在專案現況。流程：預覽 → 確認。預覽列出被勾選任務與新日期，不寫入。
- FR-BLK-02 輸入：專案、任務清單（每項帶 `expected_version`）、天數（非 0 整數，絕對值 ≤ 365，負為提前）、原因、備註、註記（套用到清單中「負責人是我」的任務）或 `defer_mark`。
- FR-BLK-03 預設全選未完成任務；**不自動推論相依**，由你勾選（本版沒有相依資料）。
- FR-BLK-04 清單含已完成任務拒絕（`INCLUDES_DONE_TASK`，列出任務）；含不屬於該專案的任務拒絕；清單為空拒絕。
- FR-BLK-05 預覽標示新日期早於今天、早於開始日的任務（警告，不阻擋）。
- FR-BLK-06 確認為**單一交易**：建立批次記錄，逐項寫 `due` 事件（共用 `batch_id`），更新 `latest_due`；任一項失敗全部回滾。
- FR-BLK-07 同一批次的「我的任務」套用同一個註記；要逐項不同，之後在歷程對單項補註記（FR-MRK-04）。
- FR-BLK-08 歷程中同批次事件可辨識，並可依批次篩選。

### 3.9 FR-BAS 基準更正（P1）

- FR-BAS-01 入口為任務詳情內的小連結，不放在主要操作區。
- FR-BAS-02 只允許兩種類型：`correction`（更正錯誤）、`rebaseline`（客戶或主管正式改變承諾日）。原因必選：匯入或輸入錯誤、原計畫日期寫錯、客戶或主管正式改變承諾日、其他。
- FR-BAS-03 **兩段式確認**：第一步（preview）回傳影響說明與一個確認憑證；第二步（commit）必須帶憑證與 `ack=true`（聲明「這不是為了讓延期看起來比較小」）。preview 不改 `tasks`、`events`，但會在 `confirmations` 新增一列憑證，commit 時才能比對（DA-21）。
- FR-BAS-04 影響說明包含：此任務與基準的差距變化（舊 → 新）；專案「已延期」數量變化（單點任務沒有專案，改算全部單點任務的已延期數，DA-15）；此任務過去的日期調整事件數（保留，不重算）；舊原訂日將永久留在歷程。
- FR-BAS-05 確認憑證綁定「任務、新日期、類型、原因、當時的原訂日與任務版本」，10 分鐘過期（〔假設〕）；任務在期間內有變動則憑證失效（`CONFIRMATION_INVALID`）。
- FR-BAS-06 commit 時覆蓋 `orig_due`，寫一筆 `baseline` 事件（欄位 `orig_due`，前值、後值、類型、原因、「二次確認」）。**舊的原訂日只留在歷程，不做基準版本。**
- FR-BAS-07 更正後：甘特基準框、已延期數、週報延期事項依新基準重算；**既有日期事件與註記不重算**。
- FR-BAS-08 已完成任務拒絕（`TASK_DONE`）；新日期等於目前原訂日拒絕（`NO_CHANGE`）。

### 3.10 FR-HIS 專案修改歷程（P1）

- FR-HIS-01 所有變更都是 `events` 的一筆。**資料庫層禁止 UPDATE 與 DELETE**（觸發器擋下）。
- FR-HIS-02 事件類型：`due`（日期）、`annotation`（註記）、`status`（狀態）、`task`（任務）、`feedback`（完成回報）、`goal`（目標關聯）、`baseline`（基準）、`project`（專案）。
- FR-HIS-03 歷程頁可依專案（含「單點任務」）、類型、任務篩選；回傳筆數。
- FR-HIS-04 每筆顯示：時間、操作者、專案、任務、類型、前值 → 後值、時間管理註記（日期事件）、依據（原句或操作來源）。
- FR-HIS-05 原句不存在事件本身，而是引用 `sources`；來源原文被刪除後，事件仍在，原句顯示「（原文已依設定刪除）」。
- FR-HIS-06 任務詳情顯示該任務的歷程；手機的專案標題旁可開專案歷程。
- FR-HIS-07 事件快照任務標題（`task_title`），改名或改負責人不影響舊事件。非任務事件（例如 `project`）的 `task_title` 寫空字串，畫面顯示為「—」（DA-05）。

### 3.11 FR-INB 收件、候選與確認（P1，AI-01）

- FR-INB-01 入口：貼上文字（預設）；LINE webhook（P1b，需已綁定且已告知成員的群組）。
- FR-INB-02 R1 規則：LINE 群組未綁定或未確認告知成員者一律丟棄，不存原文。
- FR-INB-03 只存必要摘錄（`sources.excerpt`），不存整段對話；依保存期限到期清除。
- FR-INB-04 重複訊息以「時間＋發言者＋內容」雜湊判斷，**只回報重複數，不自動合併**。貼上內容有日期標頭（例如 `2026/11/11（三）`）時，標頭之後的訊息以「日期＋時間＋發言者＋內容」判斷；沒有日期標頭時維持原規則（2026-11-16 裁定，PR #20 B3）。原文清除後再貼同一段文字仍算重複，原文維持清除、不回存（2026-11-16 裁定，PR #20 Q3）。
- FR-INB-05 解析規模：不超過 30 行同步處理；超過則建立背景工作，回傳工作編號，前端輪詢（每 3 秒，最多 60 秒）。〔假設〕
- FR-INB-06 AI-01 輸出候選：種類（`delay`、`done`、`stuck`）、對應任務、新值、原句、確定度。AI 原始輸出先保存為中間產物。
- FR-INB-07 R2 規則（程式，不由 AI 決定）：驗證輸出格式；日期轉值；問句、含「可能、大概、應該、也許」者降級為 `unclear`（待釐清）；認不出任務的承接語句為 `unmatched`（待配對），**不猜**；無關訊息略過並計數。
- FR-INB-08 AI 逾時或輸出不合格式：從 AI-01 續跑最多重試 2 次；仍失敗則工作標為 `failed`，保留摘錄，提示可手動建立任務。
- FR-INB-08a 收件指定的專案為私人範圍（`scope='private'`）時，不呼叫 AI-01、不寫 `ai_runs`，回 `ai_status="unavailable"`（背景工作標為 `failed`），摘錄照存、可手動建立任務（2026-11-16 裁定，PR #20 B1；資安規則 2）。背景工作以**執行當下**的專案範圍判斷：排隊期間專案改為私人，執行時同樣不呼叫 AI-01（2026-11-16 裁定，PR #20 Q2）。
- FR-INB-09 候選狀態：`open`、`confirmed`、`ignored`。`open` 候選**不進任何正式統計、甘特圖或週報**。
- FR-INB-10 確認 `delay` 候選：可先改日期；寫 `due` 事件（依據為該候選與原句）；更新 `latest_due`；若任務負責人是我，回傳 `needs_mark=true` 與事件 id，前端接著開註記面板（FR-MRK）。新日期等於目前 `latest_due` 時回 422 `NO_CHANGE`，候選維持 `open`、不寫事件（同 AC-07）（2026-11-16 裁定，PR #20 Q4）。
- FR-INB-11 確認 `done` 候選：任務標為完成、記完成日，並開啟完成回報（FR-FBK）。
- FR-INB-12 確認 `stuck` 候選：任務 `blocked=1`，寫 `status` 事件。
- FR-INB-13 `unclear` 候選：提供「我確認」（依建議值，事件依據註記為「待釐清，你確認」）與「忽略」。
- FR-INB-14 `unmatched` 候選：可「建立新任務」（標題、負責人為發言者、期限由你確認）或「忽略」。建任務時沒送 `project_id`，沿用候選收件時的專案（PR #20 B5）；該專案已封存時，任務建成無專案，回應 `warnings` 含 `PROJECT_ARCHIVED`（畫面顯示「原專案已封存，任務已建為無專案」）。明確送了 `project_id`（含已封存的專案、含 null）照舊，不檢查（#44 裁定 A）。
- FR-INB-15 忽略保留紀錄，作為評估資料。
- FR-INB-16 每日合併確認：在設定時間推播待確認數；確認時間以使用者設定上限為準，超過不強迫，但記錄實際使用時間供校正。

### 3.12 FR-FBK 完成回報（P2）

- FR-FBK-01 任務完成（今日頁按完成，或確認完成候選）後開啟完成回報。
- FR-FBK-02 必填：實際達成星數（1–5）、自評精力（高／中／低）。選填：投入時間相對預期（少於／如期／多於）。關聯目標另以 `POST /goal-links` 確認（FR-GOL-03；#47 A6）。
- FR-FBK-03 逾期天數 `overdue_days = max(0, 完成日 − 原訂日)` **由伺服器計算**，前端送來的值忽略。以原訂日為基準。
- FR-FBK-04 儲存時記錄當時 `rubric_id`；顯示事前預設與其來源。
- FR-FBK-05 可「稍後補」：任務保持完成狀態，列入今日頁「待補完成回報」，直到填寫。
- FR-FBK-06 一個任務最多一筆完成回報。修改回報（以新增一筆 `feedback` 更正事件、統計取最新一筆）本期不做（D-05、todo 9.3）：已有回報再送回 `FEEDBACK_EXISTS`（2026-11-18 產品負責人裁定，#47 A1）。
- FR-FBK-07 精力永遠由你自評，**AI 不估、不代填**。

### 3.13 FR-GOL 目標與精力（P2–P3，AI-03、AI-04）

- FR-GOL-01 目標三類：能力成長（衡量：完成事件數）、時間配置（衡量：每週確認分鐘數；未知時段不算 0）、績效期待（衡量：對應專案的完成比）。
- FR-GOL-02 每個目標有預期精力投入（高／中／低），用來和實際完成事件的精力對照，**不是考核**。
- FR-GOL-03 關聯：完成事件關聯到目標，**由你確認**。AI-03 只提議；改選、不關聯記為修正事件。
- FR-GOL-04 目標統計：關聯事件數、實際平均星數、事前預設平均、逾期件數、精力分布。
- FR-GOL-05 判讀：關聯事件少於 5 筆只顯示分布，`judgement=null`（〔假設〕門檻，G2 驗證）；5 筆以上：實際主要精力等級與預期相同為「一致」，否則「建議檢視」。判讀由程式規則計算，非 AI。
- FR-GOL-06 工作目標回報：AI-04 以已確認關聯的完成事件與統計產生對內草稿；人工版與草稿分開保存。
- FR-GOL-07 R3 規則：草稿中的數字必須等於程式統計，不符時不顯示草稿，改顯示統計表。

### 3.14 FR-RPT 週報（P1，AI-05）

- FR-RPT-01 週報只讀「工作」範圍、已確認的事件；**私人範圍在送進 AI 前就排除**，並顯示排除項數。範圍只看**任務**的 `scope`（私人專案底下的工作任務照常列入）；`excluded_private` 為本來會進任一段的私人任務數，同一任務只算一次（2026-11-16 產品負責人裁定，#18 A、B）。
- FR-RPT-02 內容段落：本週完成、延期事項（原訂 → 最新，附依據）、下週重點與風險（卡住，或期限在下週的任務）。本週＝`week_start`（星期一）起 7 天，下週＝其後 7 天；事件日期以台北時區判斷。各段的選取規則（#18 C～F、G1～G3、G5、G6）：
  - 本週完成（`done`）：`done_date` 在本週，且有 `status` 事件（`to_value='done'`）的任務；附該事件 id。找不到完成事件的不列入。
  - 延期事項（`delay`）：本週內有 `delta_days > 0` 的 `due` 事件，**而且目前仍延期**（`latest_due > orig_due`）的任務；原訂與最新都取任務目前的值，所以基準更正後依新基準（AC-25）；附該週的延後事件 id。
  - 下週重點與風險（`next`）：未完成，且符合下列任一：卡住；`latest_due` 在下週；已逾期（`latest_due` 早於下週一）。封存專案的任務不列入；本週的完成與延期照列。（#18 H1，「逾期」以下週一為基準；2026-11-17 定案）
  - 「附依據」為事件 id，由前端依 id 到歷程查原句或操作來源，不經 AI。
- FR-RPT-03 R4 規則：初稿中每個完成與延期都要對應一筆歷程事件；對不上者不顯示初稿，改顯示事件清單。R4 檢查 AI 回傳的**每一項**（含 `next`）都必須是本週資料裡存在的（段落、任務、事件）組合，避免 AI 帶入私人或不存在的任務（#18 G4）。R4 不要求完整，AI 漏報不算失敗，由畫面並列事件清單比對（G8）。R4 只能檢查結構化的 `items`，不檢查 `draft` 自由文字（已知限制）。
  - 產生當下嚴格比對全部項目；`GET` 重新對帳時，`done`、`delay` 仍嚴格比對，`next` 只要求任務仍存在且為工作範圍，不要求仍在下週重點（避免事後完成或改期就讓初稿失效）。（#18 J1；2026-11-17 定案）
  - AI 有回應但格式不對或對帳失敗，記為 `invalid_output`，當作失敗；AI 逾時或其他錯誤記為 `unavailable`。（#18 J2、J3；2026-11-17 定案）
  - 已知限制（J9）：基準更正後 `draft` 文字仍是舊的原訂日；`draft` 文字提到、但不在 `items` 裡的任務，事後改私人偵測不到；`items` 為空但 `draft` 有文字依 G8 算通過；重複項目合併。
- FR-RPT-04 AI 初稿與人工版分開保存。人工版由你修改。每週一列；重新產生只更新 AI 初稿，人工版不動（AC-51）。重新產生時 AI 失敗，保留上一次成功的初稿，整列不動（`excluded_private`、`updated_at` 也不更新）；第一次產生就失敗時建一列，AI 欄位為 null。（#18 H2、J4；2026-11-17 定案）
- FR-RPT-05 **P1 系統不代發週報**，只提供文字供你複製；送出功能為預留〔待決〕。

### 3.15 FR-GOV 資料控制（P1）

- FR-GOV-01 來源原文依保存期限自動清除（每小時排程，見 6.7）。
- FR-GOV-02 匯出：產生包含所有表的 JSON 檔供下載。
- FR-GOV-03 刪除所有來源原文：二次確認；刪除後任務、事件仍保留，原句顯示為已刪除。`idempotency_keys` 存的回應本文可能含原句，一併刪除（屬於暫存，不是歷程，DA-23）。
- FR-GOV-04 LINE 群組解除綁定即停止處理該群組，不追溯刪除已確認的紀錄。
- FR-GOV-05 送進 AI 的內容只含必要摘錄；是否遮蔽姓名〔待決〕。

### 3.16 FR-AI AI 節點通則

- FR-AI-01 所有 AI 節點為 L1：輸出只成為候選或草稿，**不直接寫入正式紀錄**。
- FR-AI-02 每個 AI 呼叫記錄於 `ai_runs`：節點、狀態、嘗試次數、延遲、錯誤。
- FR-AI-03 每個 AI 節點必須有不依賴 AI 的退路（第 6.6 節）。AI 不可用時，主流程仍可完成。
- FR-AI-04 AI 的結果被接受、修改、忽略、改選，都記入 `ai_feedback`，供評估。匯入表頭對應（AI-07）：一次匯入寫一筆，錨定該次匯入的 `baseline` 事件，`detail` 只放欄位索引（第 5.6 節）。
- FR-AI-06 **AI 不得參與對使用者自己的評價**：延期原因、時間管理註記、自評精力、實際達成星數皆由使用者判斷，不設預填或建議。AI-02（預設星數）因屬事前預設而非事後評價，是否採用另見 D-01。
- FR-AI-05 AI 供應商以介面隔離（`AIClient`），可替換；單次呼叫逾時預設 20 秒〔假設〕。各節點的 payload 與輸出格式見 5.3a。

---

## 4. 資料模型

PostgreSQL 15+。通則：日期用 `DATE`，時間戳用 `TIMESTAMPTZ`（連線時區 Asia/Taipei，API 輸出 ISO 8601 含 `+08:00`）；布林用 `BOOLEAN`（SQL 種子寫 `true`／`false`，本文件 AC 中的 `mine=0`、`blocked=1` 等寫法分別讀作 `false`、`true`）；JSON 用 `JSONB`；主鍵為 `BIGINT GENERATED BY DEFAULT AS IDENTITY`（種子可指定 id，之後須重設序列）。時區固定為 Asia/Taipei。

### 4.1 實體關係

```
settings(1) ─ rubrics(n)
projects(1) ─ tasks(n) ─ completion_feedback(0..1)
tasks(n) ─ goals(0..1)
sources(1) ─ candidates(n)
events(n) ─ projects / tasks / sources / batches
events.ref_event_id ─ events (註記指向日期事件)
batches(1) ─ events(n)
ai_runs(n) ─ jobs(1)
```

### 4.2 DDL

以 `backend/app/db/migrations/versions/0001_initial.sql` 為準，下列內容與該檔相同。

```sql
-- 個人大總管 APP 初始結構（PostgreSQL 15+）
-- 本檔即 spec 4.2 的 DDL 契約；之後只能新增遷移，不改既有欄位語意。

-- 設定（單列）
CREATE TABLE settings (
  id                 SMALLINT PRIMARY KEY CHECK (id = 1),
  default_scope      TEXT NOT NULL DEFAULT 'work' CHECK (default_scope IN ('work','private')),
  role               TEXT NOT NULL DEFAULT 'project_owner'
                     CHECK (role IN ('project_owner','wbs_owner','both')),
  report_audience    TEXT NOT NULL DEFAULT 'manager'
                     CHECK (report_audience IN ('manager','client','none')),
  confirm_time       TEXT NOT NULL DEFAULT '18:00',
  confirm_cap_min    INTEGER NOT NULL DEFAULT 5 CHECK (confirm_cap_min IN (3,5,10)),
  remind_default     TEXT NOT NULL DEFAULT 'morning'
                     CHECK (remind_default IN ('morning','eve_before','none')),
  retention_days     INTEGER NOT NULL DEFAULT 30 CHECK (retention_days IN (30,90,180)),
  energy_def_high    TEXT NOT NULL,
  energy_def_mid     TEXT NOT NULL,
  energy_def_low     TEXT NOT NULL,
  goal_types_enabled JSONB NOT NULL DEFAULT '["growth","time","expectation"]'
                     CHECK (jsonb_typeof(goal_types_enabled) = 'array'),
  onboarded_at       TIMESTAMPTZ
);

-- 星數量表（版本不可變）
CREATE TABLE rubrics (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  version     INTEGER NOT NULL UNIQUE,
  levels      JSONB NOT NULL CHECK (
                CASE WHEN jsonb_typeof(levels) = 'array'
                     THEN jsonb_array_length(levels) = 5 ELSE false END),
  source      TEXT NOT NULL CHECK (source IN ('default','interview')),
  interview   JSONB,
  created_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE line_groups (
  id           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name         TEXT NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('self','client')),
  line_ref     TEXT UNIQUE,
  notified     BOOLEAN NOT NULL DEFAULT false,
  bound        BOOLEAN NOT NULL DEFAULT false,
  CHECK (NOT bound OR notified)                 -- 未告知成員不可綁定
);

CREATE TABLE projects (
  id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name          TEXT NOT NULL CHECK (length(trim(name)) > 0),
  scope         TEXT NOT NULL CHECK (scope IN ('work','private')),
  audience      TEXT NOT NULL CHECK (audience IN ('manager','client','none')),
  line_group_id BIGINT REFERENCES line_groups(id),
  created_at    TIMESTAMPTZ NOT NULL,
  updated_at    TIMESTAMPTZ NOT NULL,
  archived_at   TIMESTAMPTZ
);

CREATE TABLE goals (
  id           BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  type         TEXT NOT NULL CHECK (type IN ('growth','time','expectation')),
  title        TEXT NOT NULL,
  period       TEXT NOT NULL,
  definition   TEXT NOT NULL DEFAULT '',
  target       INTEGER NOT NULL DEFAULT 0,          -- growth：件數；time：分鐘／週；expectation：未用
  energy_plan  TEXT NOT NULL CHECK (energy_plan IN ('high','mid','low')),
  project_id   BIGINT REFERENCES projects(id),     -- expectation 類型使用
  created_at   TIMESTAMPTZ NOT NULL,
  archived_at  TIMESTAMPTZ
);

CREATE TABLE tasks (
  id             BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  project_id     BIGINT REFERENCES projects(id),   -- NULL = 單點任務
  title          TEXT NOT NULL CHECK (length(trim(title)) > 0),
  owner_name     TEXT NOT NULL DEFAULT '我',        -- 名字；'我' 代表使用者本人
  scope          TEXT NOT NULL CHECK (scope IN ('work','private')),
  start_date     DATE NOT NULL,
  orig_due       DATE NOT NULL,                     -- 基準，僅基準更正可改
  latest_due     DATE NOT NULL,
  status         TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','doing','done')),
  blocked        BOOLEAN NOT NULL DEFAULT false,
  done_date      DATE,
  done_when      TEXT NOT NULL DEFAULT '',
  remind         TEXT NOT NULL DEFAULT 'morning' CHECK (remind IN ('morning','eve_before','none')),
  expected_stars INTEGER NOT NULL DEFAULT 3 CHECK (expected_stars BETWEEN 1 AND 5),
  star_source    TEXT NOT NULL DEFAULT 'self'
                 CHECK (star_source IN ('self','ai_accepted','ai_edited','import_default')),
  rubric_id      BIGINT REFERENCES rubrics(id),
  goal_id        BIGINT REFERENCES goals(id),
  version        INTEGER NOT NULL DEFAULT 1,        -- 樂觀鎖
  created_at     TIMESTAMPTZ NOT NULL,
  updated_at     TIMESTAMPTZ NOT NULL,
  CHECK (status <> 'done' OR done_date IS NOT NULL)
);
CREATE INDEX ix_tasks_project ON tasks(project_id, status);
CREATE INDEX ix_tasks_owner_due ON tasks(owner_name, latest_due);

CREATE TABLE completion_feedback (
  id                 BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  task_id            BIGINT NOT NULL UNIQUE REFERENCES tasks(id),
  actual_stars       INTEGER NOT NULL CHECK (actual_stars BETWEEN 1 AND 5),
  energy             TEXT NOT NULL CHECK (energy IN ('high','mid','low')),
  invest_vs_expected TEXT CHECK (invest_vs_expected IN ('less','as_expected','more')),
  overdue_days       INTEGER NOT NULL CHECK (overdue_days >= 0),   -- 伺服器計算
  rubric_id          BIGINT NOT NULL REFERENCES rubrics(id),
  created_at         TIMESTAMPTZ NOT NULL
);

-- 來源（原文摘錄；可被保存期限清除）
CREATE TABLE sources (
  id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  channel       TEXT NOT NULL CHECK (channel IN ('paste','line')),
  line_group_id BIGINT REFERENCES line_groups(id),
  speaker       TEXT NOT NULL,
  spoken_at     TEXT,                               -- 對話中的時間字樣，例如 10:12
  excerpt       TEXT,                               -- 清除後為 NULL
  excerpt_hash  TEXT NOT NULL UNIQUE,               -- 時間＋發言者＋內容
  received_at   TIMESTAMPTZ NOT NULL,
  expires_at    TIMESTAMPTZ NOT NULL,
  purged_at     TIMESTAMPTZ
);

CREATE TABLE jobs (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('ingest')),
  status      TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed')),
  attempts    INTEGER NOT NULL DEFAULT 0,
  payload     JSONB NOT NULL,
  result      JSONB,                                -- 新增候選數、略過數、重複數
  error       TEXT,
  created_at  TIMESTAMPTZ NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE ai_runs (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  node_id     TEXT NOT NULL CHECK (node_id IN ('AI-01','AI-02','AI-03','AI-04','AI-05','AI-06','AI-07','AI-08')),
  job_id      BIGINT REFERENCES jobs(id),
  status      TEXT NOT NULL CHECK (status IN ('ok','timeout','invalid_output','error')),
  attempt     INTEGER NOT NULL DEFAULT 1,
  latency_ms  INTEGER,
  raw_output  TEXT,                                 -- 中間產物，供續跑與除錯
  error       TEXT,
  created_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE candidates (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  source_id   BIGINT NOT NULL REFERENCES sources(id),
  kind        TEXT NOT NULL CHECK (kind IN ('delay','done','stuck','unclear','unmatched')),
  certainty   TEXT NOT NULL CHECK (certainty IN ('sure','to_clarify','to_match')),
  task_id     BIGINT REFERENCES tasks(id),
  proposed    JSONB,                                -- 例：{"new_due":"2026-11-18"}
  suggest     JSONB,                                -- 待釐清時的建議動作
  note        TEXT,
  state       TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open','confirmed','ignored')),
  decision    TEXT,
  decided_at  TIMESTAMPTZ,
  ai_run_id   BIGINT REFERENCES ai_runs(id),
  created_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_candidates_state ON candidates(state);

CREATE TABLE batches (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  project_id  BIGINT NOT NULL REFERENCES projects(id),
  days        INTEGER NOT NULL CHECK (days <> 0),
  reason      TEXT,
  note        TEXT,
  task_count  INTEGER NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL
);

-- 歷程（只增不改）
CREATE TABLE events (
  id            BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  ts            TIMESTAMPTZ NOT NULL,
  project_id    BIGINT REFERENCES projects(id),
  task_id       BIGINT REFERENCES tasks(id),
  task_title    TEXT NOT NULL,                      -- 快照；非任務事件為空字串
  kind          TEXT NOT NULL CHECK (kind IN
                ('due','annotation','status','task','feedback','goal','baseline','project')),
  field         TEXT NOT NULL,
  from_value    TEXT,
  to_value      TEXT,
  origin        TEXT NOT NULL CHECK (origin IN
                ('candidate','manual','bulk','import','baseline_correction','system')),
  origin_ref    BIGINT,                             -- candidate id 或 batch id
  source_id     BIGINT REFERENCES sources(id),      -- 原句來源
  reason        TEXT,
  note          TEXT,
  delta_days    INTEGER,                            -- due 事件：提前為負、延後為正
  mark          TEXT CHECK (mark IS NULL OR mark IN ('better','worse','none')),
  mine          BOOLEAN NOT NULL DEFAULT false,     -- 事件發生時，負責人是否為我
  ref_event_id  BIGINT REFERENCES events(id),       -- annotation 指向 due 事件
  batch_id      BIGINT REFERENCES batches(id),
  actor         TEXT NOT NULL DEFAULT 'me',
  extra         JSONB
);
CREATE INDEX ix_events_project ON events(project_id, ts DESC);
CREATE INDEX ix_events_task    ON events(task_id, ts DESC);
CREATE INDEX ix_events_ref     ON events(ref_event_id);
CREATE INDEX ix_events_batch   ON events(batch_id);

CREATE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'events are append-only' USING ERRCODE = 'restrict_violation';
END;
$$;
CREATE TRIGGER events_no_update BEFORE UPDATE ON events
  FOR EACH ROW EXECUTE FUNCTION events_append_only();
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
  FOR EACH ROW EXECUTE FUNCTION events_append_only();
CREATE TRIGGER events_no_truncate BEFORE TRUNCATE ON events
  FOR EACH STATEMENT EXECUTE FUNCTION events_append_only();

CREATE TABLE ai_feedback (
  id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  node_id     TEXT NOT NULL,
  target_type TEXT NOT NULL,                        -- candidate／task／goal_link／rubric／import_map
  target_id   BIGINT NOT NULL,
  outcome     TEXT NOT NULL CHECK (outcome IN ('accepted','edited','ignored','changed')),
  detail      JSONB,
  created_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE reports (
  id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  kind             TEXT NOT NULL CHECK (kind IN ('weekly','goal')),
  period_start     DATE,
  goal_id          BIGINT REFERENCES goals(id),
  ai_draft         TEXT,
  manual_text      TEXT,                            -- 與 AI 草稿分開保存
  excluded_private INTEGER NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL,
  updated_at       TIMESTAMPTZ NOT NULL
);

CREATE TABLE confirmations (                        -- 基準更正的確認憑證
  token        TEXT PRIMARY KEY,
  task_id      BIGINT NOT NULL REFERENCES tasks(id),
  payload      JSONB NOT NULL,
  task_version INTEGER NOT NULL,
  expires_at   TIMESTAMPTZ NOT NULL,
  used_at      TIMESTAMPTZ
);

CREATE TABLE idempotency_keys (
  key         TEXT PRIMARY KEY,
  endpoint    TEXT NOT NULL,
  response    JSONB NOT NULL,                       -- {"status": HTTP 狀態碼, "body": 回應內容}
  created_at  TIMESTAMPTZ NOT NULL                  -- 保存 24 小時
);
```

### 4.2.1 後續遷移

0001 之後的變更一律新增遷移，不改 0001（todo 5.7）。內容以 `backend/app/db/migrations/versions/` 下的檔案為準。

| 遷移 | 內容 | 依據 |
| --- | --- | --- |
| 0002 結構變更 | `ai_runs.node_id` 的 CHECK 移除 `AI-08`（AI-08 已取消）；`rubrics` 加不可修改觸發器，UPDATE、DELETE、TRUNCATE 皆擋，INSERT 不受影響。`settings` 不加，啟用精靈需要 UPDATE | PR #1 審查 A1、B5（2026-11-15 產品負責人裁定）；FR-RUB-01 |
| 0003 系統種子 | 寫入 `settings`（id=1，三句精力定義，其餘欄位用 DDL 預設值）與 `rubrics`（version=0、`source='default'`、五句量表），冪等（`ON CONFLICT DO NOTHING`）；降級不刪除種子 | PR #1 審查 B2（種子文字經產品負責人確認，修改文字屬規格變更）；AC-59 |
| 0004 候選記住收件專案 | `candidates` 加 `project_id BIGINT REFERENCES projects(id)`（可為 NULL，NULL 表示收件時沒有指定專案）與索引 `ix_candidates_project`。只新增欄位與索引 | PR #20 審查 B5（2026-11-16 產品負責人裁定）；FR-INB-14 |
| 0005 週報存檔 | `reports` 加 `ai_items JSONB`（AI 回傳的結構化項目）與 `ai_status TEXT`（`ok`、`unavailable`、`invalid_output`，可為 NULL）；加部分唯一索引「每週一列」（`period_start`，`WHERE kind = 'weekly'`）；加 CHECK「週報列一定要有 `period_start`」（NULL 不受唯一索引約束）（#18 J8；2026-11-17 定案）。只新增欄位、索引與 CHECK | 2026-11-16 產品負責人裁定（#18 第 1 點 (b)）；FR-RPT-03、04 |

系統種子相關規則（2026-11-15 產品負責人裁定）：

- 「目前量表」為 `version` 最大者；建立任務與匯入時，`tasks.rubric_id` 填入目前量表 id。
- `settings.onboarded_at` 為 NULL 表示尚未啟用；完成或略過啟用精靈都寫入時間；略過時沿用種子值；精靈修改精力定義是 UPDATE 那一列，不新增。
- 測試範本資料庫等於遷移結果（含種子）。測試種子不得再插入 `settings(id=1)` 或 `rubrics(version=0)`；要測多版本量表用 `version >= 1`，且 id 不得指定為 1。

### 4.3 列舉值

| 列舉 | 值 |
| --- | --- |
| 註記 `mark` | `better` 變好、`worse` 變差、`none` 不計入 |
| 候選種類 | `delay`、`done`、`stuck`、`unclear`、`unmatched` |
| 確定度 | `sure`、`to_clarify`、`to_match` |
| 星數來源 | `self`、`ai_accepted`、`ai_edited`、`import_default` |
| 日期調整原因（提前） | `finished_early`、`less_work`、`prereq_early`、`other` |
| 日期調整原因（延後） | `underestimated`、`self_interrupt`、`wait_external`*、`scope_change_external`*、`resource_external`*、`other` |
| 基準更正類型 | `correction`、`rebaseline` |
| 基準更正原因 | `input_error`、`plan_date_wrong`、`formal_commitment_change`、`other` |

\* 標星號者為外部原因（`external=true`），介面據此提示建議「不計入」。

### 4.4 衍生計算（不存欄位，查詢時算）

| 項目 | 規則 |
| --- | --- |
| 已延期 | `latest_due > orig_due` 且未完成 |
| 與基準差距 | `latest_due − orig_due`（天） |
| 逾期天數 | `max(0, done_date − orig_due)`，完成時寫入 `completion_feedback` |
| 有效註記 | 指向該日期事件的最新 `annotation.mark`，否則取該事件的 `mark` |
| 時間管理統計 | 見 FR-MRK-06 |

---

## 5. 介面／API 定義

### 5.1 通則

- Base URL：`/api/v1`。格式 JSON，UTF-8。日期 `YYYY-MM-DD`，時間戳 ISO 8601。
- 認證：單使用者；以環境變數設定的 Bearer token 保護（`Authorization: Bearer …`），僅用於避免意外對外暴露；預設只綁定 `127.0.0.1`。
- 冪等：所有「確認／提交」類 POST 接受 `Idempotency-Key` 標頭，相同鍵 24 小時內回傳首次結果（DA-18）：
  - 只對 POST、PUT、PATCH 生效；回應狀態碼小於 500 才保存（存狀態碼與本文，重送時回相同狀態碼）。
  - 同一個鍵用在不同端點回 422 `VALIDATION_ERROR`。
  - 兩個相同鍵的請求同時到達時，不保證只執行一次；整批順延另有 `expected_version` 擋第二次寫入。
  - 每次寫入時清除超過 24 小時的列（DA-23）。回應本文可能含原句，所以「刪除所有來源原文」（FR-GOV）的清除範圍也包含這張表。
- 樂觀鎖：修改任務的請求帶 `expected_version`；不符回 409 `STALE_VERSION`。
- 成功回應：直接回資源或 `{ "data": … }`；列表回 `{ "items": […], "total": n }`。建立類端點（`POST /projects`、`POST /tasks`、`POST /events/{id}/annotations`、`POST /projects/import/commit`、`POST /candidates/{id}/create-task`、`POST /rubrics`）回 201，其餘 POST 回 200（DA-20；後三個為 2026-11-16 擴充）。
- OpenAPI 文件放在 `/api/v1/openapi.json`，與其他 API 一樣需要 token；`/docs`、`/redoc` 關閉。不啟動伺服器也能匯出：在 `backend/` 下執行 `uv run python -m app.export_openapi`（DA-24）。
- 未預期的例外：回 500 `INTERNAL_ERROR`，訊息固定；log 只記例外類型名稱，不寫錯誤訊息與 traceback；資料庫引擎設 `hide_parameters=True`，例外訊息不帶 SQL 參數值（DA-25）。
- 錯誤回應格式：

```json
{ "error": { "code": "TASK_DONE", "message": "已完成的任務不可調整預計完成日", "details": { "task_id": 12 } } }
```

### 5.2 錯誤碼

| HTTP | code | 情況 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | token 缺失或錯誤 |
| 404 | `NOT_FOUND` | 資源不存在 |
| 409 | `TASK_DONE` | 對已完成任務做日期調整、基準更正、標卡住 |
| 409 | `STALE_VERSION` | `expected_version` 與目前不符 |
| 409 | `CONFIRMATION_INVALID` | 基準更正憑證過期、已使用或任務已變動 |
| 409 | `CANDIDATE_NOT_OPEN` | 候選已處理 |
| 409 | `FEEDBACK_EXISTS` | 任務已有完成回報（修改回報 9.3 未開放；2026-11-18 產品負責人裁定，#47 A1） |
| 413 | `PAYLOAD_TOO_LARGE` | 貼上文字超過 20,000 字，或匯入超過 500 列或 50,000 字元 |
| 422 | `VALIDATION_ERROR` | 欄位缺漏或格式錯誤（`details` 列出欄位） |
| 422 | `NO_CHANGE` | 新值等於目前值 |
| 422 | `DATE_OUT_OF_RANGE` | 日期超出允許範圍 |
| 422 | `MARK_REQUIRED` | 負責人是我，卻沒給註記也沒選稍後註記 |
| 422 | `INCLUDES_DONE_TASK` | 整批順延清單含已完成任務 |
| 422 | `EMPTY_SELECTION` | 清單或可匯入列為空 |
| 422 | `ACK_REQUIRED` | 基準更正缺少聲明 |
| 422 | `ANNOTATION_NOT_ALLOWED` | 對非「我的任務」或無日期差的事件補註記 |
| 503 | `AI_UNAVAILABLE` | 僅限沒有退路的 AI 端點（量表訪談）；其餘端點降級，見 5.3 |
| 500 | `INTERNAL_ERROR` | 未預期的伺服器錯誤；訊息固定，不帶例外內容（2026-11-13 新增，`docs/decisions.md` DA-19；2026-11-16 產品負責人複核同意） |

### 5.3 AI 降級約定

凡會呼叫 AI 的端點，回應都帶 `ai_status`：`ok`、`unavailable`、`invalid_output`。`unavailable` 與 `invalid_output` 時，端點仍回 200 並提供退路內容（例如不含建議的表單、統計表），不回錯誤。

`ai_status` 的判定：AI 回傳且通過結構驗證為 `ok`；最後一次嘗試的輸出不合格式為 `invalid_output`；逾時、供應商不可用、其他錯誤，以及依規則刻意不呼叫（私人範圍）為 `unavailable`。`ai_runs.status` 另記細分值（`timeout`、`invalid_output`、`error`）。

### 5.3a AI 節點輸入輸出契約（`AIClient`）

`AIClient.call(node_id, payload) -> dict` 是唯一對外呼叫 AI 的介面（資安規則 2），契約擁有者為 Dev-B。以下為各節點送出的 payload 與接受的輸出；輸出不合結構時丟 `AIInvalidOutput`。測試以 `FakeAIClient.script(node_id, 輸出或例外…)` 排定回傳值。

**AI-01 收件解析（FR-INB-06、07）**

- payload 只含以下三個鍵：
  ```json
  {
    "today": "2026-11-11",
    "messages": [{ "ref": 101, "speaker": "阿德", "spoken_at": "10:12", "text": "畫面規格 v1 確定延到 11/18" }],
    "tasks": [{ "id": 2, "title": "畫面規格 v1", "owner": "阿德", "latest_due": "2026-11-13" }]
  }
  ```
  - `messages`：本次新收（非重複）且原文未清除的訊息；`ref` 為 `sources.id`。重複訊息與已清除的原文不送（FR-INB-04、6.7）。
  - `tasks`：未完成、`scope='work'` 的任務；收件有指定專案時只含該專案的任務。私人範圍任務（不論是否在工作專案內）一律不送。只含上列四個欄位。
- 輸出：`{ "items": [{ "ref": 101, "kind": "delay", "task_id": 2, "new_due": "11/18", "certainty": "sure" }] }`
  - `items` 必須是陣列，否則整體算不合格式（重試）。個別項目 `ref` 不在本次 `messages`、`kind` 不在 `delay`／`done`／`stuck`／`none` 的，該項丟棄。
  - `kind="none"` 表示該則不產生候選。`task_id` 不在本次 `tasks` 裡時轉為 `unmatched`，不猜（AC-37）。`new_due` 接受 `YYYY-MM-DD` 或 `M/D`。`certainty` 選填，預設 `sure`；不是 `sure` 時降級為 `unclear`。
  - 其他欄位（例如原因推測）一律不讀（FR-DUE-05a、AC-12a）。
- 重試：同一批訊息總共最多嘗試 3 次（1 次加續跑 2 次，FR-INB-08）；供應商不可用時不續跑。每次嘗試寫一列 `ai_runs`。

**AI-07 匯入表頭對應（FR-IMP-02）**

- payload：`{ "headers": ["任務", "負責人", "開始", "結束"], "samples": [["API 定義", "我", "11/3", "11/12"]] }`。`samples` 最多前 2 列資料，只供判斷欄位意義。
- 輸出：`{ "title": 0, "owner": 1, "start": 2, "end": 3 }`。`title`、`end` 必須是欄位範圍內的整數索引；`owner`、`start` 可為 null；非 null 的索引不可重複。不合規則算 `invalid_output`。
- 只呼叫 1 次，不重試：失敗時直接走手動指定對應的退路（6.6）。寫一列 `ai_runs`。

**AI-05 週報初稿（FR-RPT，Phase 10；2026-11-16 #22 定案）**

- 呼叫端（Dev-A，Phase 10）組 payload、驗證輸出、R4 對帳；prompt 與真實供應商的節點設定由契約擁有者（Dev-B，13.4）負責。雙方只依本節格式開發，Phase 10 用 `FakeAIClient` 排回傳值。
- payload 只含以下鍵；每一項只放列出的欄位，其餘一律不送：
  ```json
  {
    "week":  { "start": "2026-11-09", "end": "2026-11-15" },
    "done":  [{ "task_id": 3, "title": "API 介面定義", "owner": "我", "done_date": "2026-11-12", "event_id": 41 }],
    "delay": [{ "task_id": 2, "title": "畫面規格", "owner": "小薇", "orig_due": "2026-11-12", "latest_due": "2026-11-18", "event_ids": [52] }],
    "next":  [{ "task_id": 5, "title": "驗收會議", "owner": "我", "latest_due": "2026-11-19", "blocked": false }]
  }
  ```
  - 只送工作範圍（`scope='work'`）的任務；私人任務在組 payload 前排除，只計數。
  - 明確不送：事件的 `note`、`reason`、`extra`、註記（`mark`）、完成回報的星數與精力（FR-AI-06）、`done_when`、原句、專案名稱。
  - `title` 用任務現值；`owner` 照 AI-01 送名字，D-03（姓名遮蔽）裁定後兩節點一起改。
- 輸出：`{ "draft": "本週（11/09–11/15）工作進度…", "items": [{ "section": "done", "task_id": 3, "event_id": 41 }, { "section": "next", "task_id": 5, "event_id": null }] }`
  - `draft` 為字串、`items` 為陣列；`section` 為 `done`、`delay`、`next`。`done`、`delay` 的 `event_id` 必填，`next` 必須為 null。
  - 缺欄位、型別不對、`section` 不在值域內，算 `invalid_output`。`draft` 空白、超過 20,000 字或含 NUL 字元也算 `invalid_output`（#18 K8）。
  - 每一項只讀 `section`、`task_id`、`event_id`，其他鍵丟棄，不算錯誤（#22）。
- 重試與紀錄（同 AI-01）：任何例外都算一次失敗、繼續重試，總共最多 3 次；`AIUnavailable` 與 R4 對帳失敗立刻停。最終 `ai_status` 以最後一次嘗試為準：最後一次是格式錯誤（`AIInvalidOutput`）或 R4 失敗回 `invalid_output`，其餘回 `unavailable`（#18 J3、K3）。`error` 欄的 `R4_MISMATCH` 與供應商格式錯誤的 `AIInvalidOutput` 分得開，可據以算週報對帳結果（spec 1.3）。每次嘗試寫一列 `ai_runs`（`latency_ms` 失敗也記；`error` 只放例外類別名稱，R4 失敗記 `R4_MISMATCH`）。**AI-05 不存 `raw_output`**。
  - R4 對帳（項目引用的 `task_id`、`event_id` 是否在 payload 裡）不重試、立刻停：`ai_runs` 記 `status='invalid_output'`、`error='R4_MISMATCH'`；回應 `ai_status='invalid_output'`、`validated=false`、`draft=null`、`items` 為退路清單（AC-66；2026-11-17 Dev-B 確認，#22）。

**AI-03 目標關聯建議（FR-GOL-03，Phase 9；2026-11-18 #72 Dev-A、Dev-B 定案）**

- 呼叫端（Dev-A）組 payload、驗證輸出、寫 `ai_feedback`；prompt 與節點（#50）由 Dev-B 負責。
- 觸發：使用者在待關聯清單按「請 AI 建議」才呼叫，打開清單時不自動呼叫；`GET /goal-links/pending` 不呼叫 AI（視窗聚焦時會自動重抓，會重複付費）。端點暫定 `POST /goal-links/suggest`〔待決：#47 G3，產品負責人裁定〕。
- 建議只放在該次回應，不另存；使用者確認關聯時帶 `ai_run_id`，伺服器讀該筆 `raw_output` 比對，寫 `ai_feedback`（與建議相同 `accepted`，不同或不關聯 `changed`），比照 AI-07 的 D-3。
- payload 只含以下鍵，其餘一律不送：
  ```json
  { "goals": [{ "goal_id": 2, "type": "growth", "title": "學會 SQL 視窗函式", "period": "2026Q4" }],
    "tasks": [{ "task_id": 7, "title": "報表查詢改寫", "done_date": "2026-11-12" }] }
  ```
  - `goals` 只送未封存的目標。`tasks` 只送工作範圍（`scope='work'`）的待關聯任務，私人任務不送、也不建議（資安規則 2、FR-GOV-05）。
  - 待關聯超過 20 筆時，送完成日最新的 20 筆；其餘再按一次。
  - 明確不送：完成回報的星數與精力（FR-AI-06）、目標的 `definition`、`energy_plan`、任務負責人、原句。
- 輸出：`{ "items": [{ "task_id": 7, "goal_id": 2, "reason": "任務內容與 SQL 學習相關" }] }`
  - `goal_id` 可為 null，表示沒有合適的目標。每個任務最多一項：同一個 `task_id` 出現多次時保留第一項、其餘丟棄；`task_id` 或 `goal_id` 不在 payload 的項目整項丟棄（兩者都不算錯誤，#73 Dev-B 提問、Dev-A 定）。
  - `reason` 不超過 200 字、不含 NUL，否則算 `invalid_output`。`reason` 只說明內容相關，不評價任務或人（FR-AI-06）。
- 記錄：比照 AI-01 存 `raw_output`（清除與匯出依 6.7：清除時設 NULL，匯出不帶）。重試比照 AI-01。

**AI-04 目標回報草稿（FR-GOL-06、07，Phase 9；2026-11-18 #72 Dev-A、Dev-B 定案）**

- 呼叫端（Dev-A）組 payload、驗證輸出、R3 對帳；prompt 與節點（#50）由 Dev-B 負責。
- payload 只含以下鍵，其餘一律不送：
  ```json
  { "goal":  { "type": "growth", "title": "學會 SQL 視窗函式", "period": "2026Q4", "energy_plan": "high" },
    "stats": { "linked": 3, "avg_actual": 4.0, "avg_expected": 3.3, "overdue_count": 1,
               "energy": { "high": 2, "mid": 1, "low": 0 }, "progress_pct": 100, "judgement": null },
    "tasks": [{ "task_id": 7, "title": "報表查詢改寫", "done_date": "2026-11-12" }] }
  ```
  - `stats` 為程式算好的統計（5.13），只送彙總數字，不送逐筆的星數與精力（FR-AI-06）。
  - `tasks` 只列工作範圍的任務；私人範圍只進統計數字、不列標題。
- 輸出：`{ "draft": "…", "figures": [{ "key": "linked", "value": 3 }, { "key": "avg_actual", "value": 4.0 }] }`
  - `draft` 不空白、不超過 20,000 字、不含 NUL，否則算 `invalid_output`（同 AI-05）。
  - prompt 要求數字一律用阿拉伯數字，並把草稿用到的每個數字列進 `figures`。
- R3 對帳（FR-GOL-07，兩點都做，任一不符即 `validated=false`、`draft=null`，前端改顯示統計表）：
  1. `figures` 的每一項都等於 `stats` 的同名值（巢狀鍵用 `energy.high` 這類寫法）。
  2. `draft` 裡出現的每個數字都在允許名單內：`stats` 的值，以及 payload 文字本來就有的數字（`goal.title`、`goal.period`、各任務 `title`，以及 `done_date` 拆出的年、月、日）。
  - 比對前正規化：`4.0`＝`4`、`100%`＝`100`、全形數字轉半形。
  - 誤判率由 Dev-B 在 #50 的評估實測；太高時調整允許名單，不放寬規則本身。
- 重試與紀錄同 AI-05：總共最多 3 次，`AIUnavailable` 與 R3 失敗立刻停；R3 失敗記 `status='invalid_output'`、`error='R3_MISMATCH'`；不存 `raw_output`。存在 `reports` 表 `kind='goal'`，比照週報（5.14）。

### 5.4 設定與量表

| Method | Path | 說明 |
| --- | --- | --- |
| GET | `/settings` | 取得設定 |
| PUT | `/settings` | 更新設定（部分欄位） |
| POST | `/settings/onboarding/complete` | 完成啟用（略過時帶 `skipped=true`） |
| GET | `/rubrics` | 列出所有量表版本；`?active=true` 取目前版本 |
| POST | `/rubrics/interview` | AI-06：輸入三題回答，回草稿 |
| POST | `/rubrics` | 確認草稿為新版本 |

`POST /rubrics/interview` 輸入：

```json
{ "q1": "交付完成且品質達標", "q2": "超出範圍或品質明顯突出", "q3": "否，同一套標準" }
```

輸出：`{ "ai_status": "ok", "draft": ["未達成：…", "部分達成：…", "符合預設：…", "優於預設：…", "遠超預設：…"] }`。AI 不可用時回 503 `AI_UNAVAILABLE`，前端保留目前版本。

`POST /rubrics` 輸入：`{ "levels": [5 句], "interview": {…} }`；輸出新版本 `{ "id", "version" }`。`levels` 必須剛好 5 句且皆非空，否則 `VALIDATION_ERROR`。

### 5.5 專案

| Method | Path | 說明 |
| --- | --- | --- |
| GET | `/projects` | 列表；`?include_archived=false` |
| POST | `/projects` | 建立 |
| GET | `/projects/{id}` | 取得，含任務數、基準保存日 |
| PATCH | `/projects/{id}` | 編輯名稱、範圍、週報對象；逐欄寫 `project` 事件 |
| POST | `/projects/{id}/archive` | 封存 |
| GET | `/projects/{id}/gantt` | 甘特資料 |
| GET | `/projects/{id}/history` | 該專案歷程（同 `/events`，預設帶 `project_id`） |

`PATCH /projects/{id}` 輸入：`{ "name": "…", "scope": "private", "audience": "client" }`；輸出：專案與 `changes`（寫入的事件列表）。無變更回 `changes=[]`，不寫事件。

`GET /projects/{id}/gantt` 輸出：

```json
{
  "range": { "from": "2026-11-09", "to": "2026-12-11" },
  "today": "2026-11-11",
  "summary": { "done": 1, "total": 6, "delayed": 2, "open_candidates": 3 },
  "rows": [{
    "task_id": 3, "title": "API 介面定義", "owner": "小薇", "status": "doing",
    "start": "2026-11-09", "orig_due": "2026-11-12", "latest_due": "2026-11-15",
    "delta_days": 3, "done_date": null, "blocked": false, "version": 4
  }]
}
```

### 5.6 匯入

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/projects/import/preview` | 解析、診斷，不寫入 |
| POST | `/projects/import/commit` | 保存基準 |

`preview` 輸入：`{ "text": "任務,負責人,開始,結束\n…", "target": "new" | <project_id>, "new_name": "…" }`。

`preview` 輸出：

```json
{
  "ai_status": "ok",
  "column_map": { "title": 0, "owner": 1, "start": 2, "end": 3, "mapped_by": "rule" },
  "rows": [{
    "index": 0, "title": "需求確認", "owner": "我", "start": "2026-11-16", "end": "2026-11-18",
    "issues": [{ "level": "warn", "code": "OWNER_MISSING", "message": "缺負責人，匯入時預設為「我」" }],
    "blocking": false
  }],
  "summary": { "importable": 5, "blocking": 1 }
}
```

`mapped_by` 為 `rule` 或 `ai`；`ai` 時前端須顯示對應預覽由你確認。

`commit` 輸入：`{ "target": …, "new_name": "…", "rows": [{ "index": 0, "title": "…", "owner": "…", "start": "…", "end": "…", "skip": false }] }`。伺服器**重新驗證**每列，有 `blocking` 且未略過者拒絕（`VALIDATION_ERROR`，列出列號）。輸出：`{ "project_id", "created": n, "skipped": m, "event_id" }`。

**AI-07 對應回饋（FR-AI-04；2026-11-16 產品負責人核可，#8）**：

- `preview` 輸出的 `column_map` 在 `mapped_by="ai"` 時多一個 `ai_run_id`（該次 AI-07 的 `ai_runs.id`），其他情況不出現。
- `commit` 輸入可選帶 `ai_run_id` 與使用者最終的 `column_map`（`{title, owner, start, end}` 欄位索引），兩者須一起出現，否則 `VALIDATION_ERROR`。`ai_run_id` 須指向 `status='ok'` 的 AI-07 紀錄，否則 `VALIDATION_ERROR`。不帶時行為不變，也不寫回饋。
- 伺服器從 `ai_runs` 取 AI 建議（不信前端自報），與最終對應比較：相同寫 `accepted`、不同寫 `changed`；`target_type='import_map'`、`target_id` 為本次 `baseline` 事件 id；`detail = { "ai_run_id", "ai": {四欄索引}, "final": {四欄索引} }`，只含整數或 null，不含任何貼上內容。該筆 `ai_runs.raw_output` 已因清除原文設為 NULL 時，照未帶 `ai_run_id` 處理：匯入照常成功，不寫回饋（PR #20 B2）。
- 同一 `ai_run_id` 已寫過回饋時，匯入照常完成，不再寫第二筆。回饋與匯入在同一交易，失敗一起回滾。

### 5.7 任務

| Method | Path | 說明 |
| --- | --- | --- |
| GET | `/tasks` | 篩選：`project_id`、`owner`、`status`、`scope`、`due_before`；`project_id=none` 為單點任務 |
| POST | `/tasks` | 建立 |
| GET | `/tasks/{id}` | 詳情，含最近歷程 |
| PATCH | `/tasks/{id}/owner` | 改負責人 |
| POST | `/tasks/{id}/adjust-due` | 調整最新預計日 |
| POST | `/tasks/{id}/adjust-start` | 調整開始日（FR-TSK-09） |
| POST | `/tasks/{id}/status` | 切換 `todo`／`doing`（DA-08） |
| POST | `/tasks/{id}/block` | 標為卡住／取消 |
| POST | `/tasks/{id}/complete` | 標為完成並回傳是否需要完成回報 |
| POST | `/tasks/suggest-stars` | AI-02 提議預設星數 |

`POST /tasks` 輸入：

```json
{
  "title": "確認驗收條件", "owner": "我", "due": "2026-11-18", "scope": "work",
  "project_id": null, "done_when": "客戶回覆確認", "remind": "morning", "goal_id": null,
  "expected_stars": 3, "suggested_stars": 3
}
```

`suggested_stars` 為先前 `suggest-stars` 回傳的建議值（沒用 AI 則省略）。伺服器依 FR-TSK-03 判定 `star_source`。輸出：任務；寫 `task` 事件。

`POST /tasks/suggest-stars` 輸入：`{ "title", "done_when", "project_id" }`；輸出：`{ "ai_status": "ok", "stars": 3, "rubric_version": 2 }`；AI 不可用時 `{ "ai_status": "unavailable", "stars": null }`。

`POST /tasks/{id}/adjust-due` 輸入：

```json
{
  "new_due": "2026-11-20",
  "expected_version": 4,
  "reason": "scope_change_external",
  "note": "客戶改需求，等新版畫面",
  "mark": "none",
  "defer_mark": false
}
```

輸出：

```json
{
  "task": { "id": 3, "latest_due": "2026-11-20", "orig_due": "2026-11-12", "version": 5 },
  "event": { "id": 88, "kind": "due", "from_value": "2026-11-15", "to_value": "2026-11-20",
             "delta_days": 5, "mark": "none", "mine": true },
  "warnings": [],
  "needs_mark": false
}
```

錯誤：`TASK_DONE`、`NO_CHANGE`、`DATE_OUT_OF_RANGE`、`MARK_REQUIRED`、`STALE_VERSION`、`VALIDATION_ERROR`（原因不在該方向的選項內，例如提前時選了延後原因；或 `mark` 與 `defer_mark` 同時給，DA-10）。`warnings` 可含 `BEFORE_START`，以及非我的任務帶了註記時的 `MARK_IGNORED`（DA-11）。`needs_mark` 的單一定義為「我的任務，且這次沒有給註記」（`mine and mark is None`，DA-04）：手動調整即選了稍後註記；確認延期候選時以 `defer_mark=true` 呼叫，兩處一致。

`POST /tasks/{id}/adjust-start` 輸入：`{ "new_start": "2026-11-14", "expected_version": 4, "note": "…" }`（`note` 選填）。輸出：`{ "task", "event", "warnings": [] }`，`warnings` 可含 `START_AFTER_DUE`。錯誤：`TASK_DONE`、`NO_CHANGE`、`DATE_OUT_OF_RANGE`、`STALE_VERSION`、`VALIDATION_ERROR`。

`POST /tasks/{id}/complete` 輸入：`{ "expected_version": 4, "done_date": "2026-11-12" }`（`done_date` 預設為今天，不可晚於今天）。輸出：`{ "task", "event", "feedback_required": true }`。已完成任務回 409 `TASK_DONE`（DA-16）。

`POST /tasks/{id}/status` 輸入：`{ "status": "todo" | "doing", "expected_version": 4 }`。輸出：`{ "task", "event" }`，寫一筆 `status` 事件。錯誤：`TASK_DONE`、`NO_CHANGE`（設成目前的值，DA-22）、`STALE_VERSION`、`VALIDATION_ERROR`（`status` 不是 `todo` 或 `doing`；改為 `done` 請用 `/complete`）。`POST /tasks/{id}/block` 設成目前的值同樣回 `NO_CHANGE`。

`PATCH /tasks/{id}/owner` 改為相同名字回 `NO_CHANGE`（DA-17）。

### 5.8 註記與歷程

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/events/{id}/annotations` | 對日期事件補註記或改註記 |
| GET | `/events` | 歷程查詢 |
| GET | `/stats/time-management` | 時間管理統計 |
| GET | `/meta/reasons` | 原因選項（含 `external` 標記、所屬方向） |

`POST /events/{id}/annotations` 輸入：`{ "mark": "worse", "reason": "underestimated", "note": "…" }`。`mark` 必填且為三值之一。`reason` 選填，有給時依原日期事件的方向檢查選項（DA-13）。輸出：新增的 `annotation` 事件，與更新後的有效註記。錯誤：`NOT_FOUND`、`ANNOTATION_NOT_ALLOWED`、`VALIDATION_ERROR`。

`GET /events` 參數：`project_id`（或 `none`）、`kind`、`task_id`、`batch_id`、`from`、`to`、`limit`（預設 100，最大 500；超過回 422 `VALIDATION_ERROR`（2026-11-16 裁定，PR #20 Q6））、`offset`。`from`、`to` 為日期，兩端皆包含（以事件時間戳的台北日期判斷）。輸出：

```json
{
  "total": 4,
  "items": [{
    "id": 88, "ts": "2026-11-11T10:48:00+08:00", "project_id": 1, "project_name": "會員系統 2.0 改版",
    "task_id": 3, "task_title": "API 介面定義", "kind": "due", "field": "latest_due",
    "from_value": "2026-11-15", "to_value": "2026-11-20", "delta_days": 5,
    "effective_mark": "none", "mine": true, "reason": "scope_change_external", "note": "…",
    "origin": "candidate", "batch_id": null,
    "source": { "label": "候選 #12", "quote": "畫面規格 v1 確定延到 11/18", "purged": false }
  }]
}
```

`source.purged=true` 時 `quote` 為 `null`，前端顯示「原文已依設定刪除」。

`GET /stats/time-management` 參數：`from`、`to`（選填）。輸出：

```json
{
  "better": { "count": 1, "days": 1 },
  "worse":  { "count": 2, "days": 3 },
  "none": 1,
  "unmarked": 0,
  "worse_by_energy": { "high": 0, "mid": 1, "low": 0, "not_done": 1 },
  "min_sample": 5,
  "judgement": null,
  "judgement_note": "樣本 3 筆，不到 5 筆，只顯示不下結論"
}
```

`judgement`、`judgement_note` 的規則見 FR-MRK-07。

### 5.9 整批順延

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/projects/{id}/bulk-shift/preview` | 預覽，不寫入 |
| POST | `/projects/{id}/bulk-shift/commit` | 單一交易寫入 |

輸入（兩端點相同，`commit` 另需註記）：

```json
{
  "items": [{ "task_id": 3, "expected_version": 4 }, { "task_id": 4, "expected_version": 2 }],
  "days": 3,
  "reason": "scope_change_external",
  "note": "客戶延後驗收會議",
  "mark": "none",
  "defer_mark": false
}
```

`preview` 輸出：每項 `{ task_id, title, owner, from, to, mine, warnings[] }`，加上 `mine_count`、`mark_required`（`mine_count>0` 為真）。

`commit` 輸出：`{ "batch_id": 7, "updated": 2, "mine_marked": 1, "events": [event ids] }`。錯誤：`INCLUDES_DONE_TASK`、`EMPTY_SELECTION`、`STALE_VERSION`（`details` 列出過期任務，整批不寫入）、`MARK_REQUIRED`、`VALIDATION_ERROR`（`days=0` 或任務不屬於該專案）。

### 5.10 基準更正

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/tasks/{id}/baseline-correction/preview` | 第一步：驗證並回影響說明與憑證 |
| POST | `/tasks/{id}/baseline-correction/commit` | 第二步：憑證加聲明，才寫入 |

`preview` 輸入：`{ "new_orig_due": "2026-11-14", "type": "correction", "reason": "plan_date_wrong", "expected_version": 4 }`。

`preview` 輸出：

```json
{
  "confirmation_token": "c0f3…", "expires_at": "2026-11-11T11:00:00+08:00",
  "impact": {
    "orig_due": { "from": "2026-11-12", "to": "2026-11-14" },
    "gap_days": { "from": 3, "to": 1 },
    "project_delayed_count": { "from": 2, "to": 1 },
    "past_due_events_kept": 2,
    "old_value_kept_in_history": true
  }
}
```

`commit` 輸入：`{ "confirmation_token": "c0f3…", "ack": true }`。輸出：任務與 `baseline` 事件。錯誤：`ACK_REQUIRED`、`CONFIRMATION_INVALID`、`TASK_DONE`、`NO_CHANGE`。

### 5.11 收件與候選

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/ingest` | 貼上文字；小量同步，大量建背景工作 |
| POST | `/webhooks/line` | LINE webhook（P1b） |
| GET | `/ingest/jobs/{id}` | 查工作狀態 |
| GET | `/candidates` | `?state=open` |
| POST | `/candidates/{id}/confirm` | 確認（`delay` 可帶 `new_due`） |
| POST | `/candidates/{id}/clarify` | 待釐清：採用建議 |
| POST | `/candidates/{id}/ignore` | 忽略 |
| POST | `/candidates/{id}/create-task` | 待配對：建立新任務 |

`POST /ingest` 輸入：`{ "text": "[10:12] 阿德：畫面規格 v1 確定延到 11/18", "project_id": 1 }`。`text` 為空字串時回 200、`created=0`，不建立來源（2026-11-16 裁定，PR #20 Q6）。

輸出（同步完成）：

```json
{ "mode": "sync", "ai_status": "ok",
  "result": { "created": 3, "skipped": 1, "duplicates": 0 }, "candidates": [ … ] }
```

輸出（背景）：`{ "mode": "async", "job_id": 15, "status": "queued" }`。

`GET /ingest/jobs/{id}` 輸出：`{ "status": "running|succeeded|failed", "attempts": 1, "result": {…}, "error": null }`。`failed` 時 `error` 為可顯示訊息，並說明可手動建立任務。

候選物件：

```json
{
  "id": 12, "kind": "delay", "certainty": "sure", "state": "open",
  "task": { "id": 2, "title": "畫面規格 v1", "latest_due": "2026-11-13", "orig_due": "2026-11-13" },
  "proposed": { "new_due": "2026-11-18" },
  "quote": "畫面規格 v1 確定延到 11/18", "speaker": "阿德", "spoken_at": "10:12",
  "note": null, "suggest": null
}
```

`POST /candidates/{id}/confirm` 輸入（`delay`）：`{ "new_due": "2026-11-18", "expected_version": 3 }`；輸出：`{ "candidate", "task", "event", "needs_mark": true }`。`needs_mark=true` 表示負責人是我，前端接著呼叫 `POST /events/{event_id}/annotations` 或選擇稍後。錯誤：`CANDIDATE_NOT_OPEN`、`TASK_DONE`、`STALE_VERSION`、`DATE_OUT_OF_RANGE`。

`confirm` 對 `done` 候選：輸出含 `feedback_required=true`。對 `unclear`、`unmatched` 使用專用端點；用錯端點回 `VALIDATION_ERROR`。

`POST /candidates/{id}/create-task` 輸入：`{ "title": "報表處理", "owner": "阿德", "due": "2026-12-20", "project_id": 1 }`。輸出含 `warnings`（沒有時為 `[]`），可含 `PROJECT_ARCHIVED`：沒送 `project_id`、沿用的候選專案已封存，任務已建為無專案（FR-INB-14，#44）。

### 5.12 完成回報

| Method | Path | 說明 |
| --- | --- | --- |
| PUT | `/tasks/{id}/feedback` | 儲存完成回報 |
| GET | `/tasks/{id}/feedback` | 讀取完成回報；還沒填回 `NOT_FOUND`（任務存在時代表尚未填寫，是正常狀態） |
| GET | `/feedback/pending` | 待補完成回報的任務 |
| GET | `/meta/today` | 伺服器的今天（台北時區），供前端判斷日期 |

（2026-11-18 產品負責人裁定，#47：A1～A6 依 Dev-A 提案。）

`PUT /tasks/{id}/feedback` 輸入：`{ "actual_stars": 4, "energy": "mid", "invest_vs_expected": "as_expected", "rubric_id": 5 }`。
- `actual_stars`（1–5）、`energy`（`high`／`mid`／`low`）、`rubric_id` 必填；`invest_vs_expected`（`less`／`as_expected`／`more`）選填，可為 null。
- `rubric_id` 是前端開啟面板時讀到的量表版本（`GET /rubrics`），伺服器只檢查它存在，不存在回 `VALIDATION_ERROR`（6.5「量表在填寫期間換版本」）。
- 不收 `goal_id`：關聯目標一律走 `POST /goal-links`（5.13），送了也忽略。`overdue_days` 由伺服器計算，前端送了也忽略（FR-FBK-03）。
- 任務須為 `done`，否則 `VALIDATION_ERROR`（`details.fields` 為 `["task_id"]`）；已有完成回報回 `FEEDBACK_EXISTS`（修改回報 9.3 依 D-05 不做）；任務不存在回 `NOT_FOUND`。`actual_stars`、`rubric_id` 只收 JSON 整數（`true`、`"4"` 回 `VALIDATION_ERROR`）。
- 成功回 201：`{ "feedback": FeedbackOut, "event": EventOut }`。同一交易寫入回報與一筆 `feedback` 事件：`field='completion_feedback'`、`from_value` 為 null、`to_value` 為回報 id、`origin='manual'`，`extra`＝`{ actual_stars, energy, invest_vs_expected, overdue_days, rubric_id }`（`invest_vs_expected` 為 null 時鍵仍保留）。`task_title`、`mine`、`project_id` 依 `write_event` 由任務當下快照。

`FeedbackOut`＝`{ id, task_id, actual_stars, energy, invest_vs_expected, overdue_days, rubric_id, created_at }`。

`GET /feedback/pending` 輸出：`{ "items": [PendingItem], "total": n }`，列出已完成但還沒有完成回報的任務，工作與私人範圍都列；依 `done_date`、`task_id` 由舊到新，不分頁、不篩選。`PendingItem`＝`{ task_id, title, owner, project_id, done_date, orig_due, overdue_days, expected_stars, star_source }`，`overdue_days` 與儲存回報時的計算相同（FR-FBK-03：`max(0, done_date − orig_due)`）。

`GET /meta/today` 輸出：`{ "today": "2026-11-18" }`。

### 5.13 目標

| Method | Path | 說明 |
| --- | --- | --- |
| GET / POST | `/goals` | 列表、建立 |
| GET / PATCH | `/goals/{id}` | 取得、編輯 |
| GET | `/goals/{id}/stats` | 統計與判讀 |
| GET | `/goals/matrix` | 目標 × 精力矩陣 |
| GET | `/goal-links/pending` | 已完成回報但未關聯目標的事件，含 AI-03 建議 |
| POST | `/goal-links` | 你確認關聯（`{ task_id, goal_id }`，`goal_id=null` 表示不關聯；2026-11-18 裁定統一端點，#47 B1） |
| POST | `/goals/{id}/report/draft` | AI-04 草稿 |
| PUT | `/goals/{id}/report/manual` | 儲存人工版 |

`GET /goals/{id}/stats` 輸出：

```json
{
  "progress": { "text": "3 ／ 3 件完成事件", "pct": 100 },
  "linked": 3, "avg_actual": 4.0, "avg_expected": 3.3, "overdue_count": 1,
  "energy": { "high": 2, "mid": 1, "low": 0 },
  "energy_plan": "high",
  "min_sample": 5,
  "judgement": null,
  "judgement_note": "樣本 3 筆，不到 5 筆，只顯示不下結論"
}
```

`POST /goal-links` 的 AI-03 建議由 `GET /goal-links/pending` 回傳 `suggestion: { goal_id, reason }`；使用者確認或改選時，伺服器寫 `ai_feedback`（`accepted` 或 `changed`）。

### 5.14 週報

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/reports/weekly/draft` | 產生 AI 初稿 |
| GET | `/reports/weekly?week_start=2026-11-09` | 依週次取得既有週報（不產生） |
| GET | `/reports/weekly/{id}` | 取得 |
| PUT | `/reports/weekly/{id}/manual` | 儲存人工版 |

`POST /reports/weekly/draft` 輸入：`{ "week_start": "2026-11-09" }`。`week_start` 必須是星期一，且不能晚於本週（只能產生本週或過去的週報），否則 `VALIDATION_ERROR`（#18 第 5 點、G7）；早於今天前 365 天回 `DATE_OUT_OF_RANGE`（#18 J6；2026-11-17 定案）。過去週的「下週重點」依現在的狀態計算，畫面上要註明。回 200（AI 失敗也是 200，附退路內容，spec 5.3）。所有端點（產生、依 id 或週次讀取、存人工版）的輸出相同：

```json
{
  "id": 4, "week_start": "2026-11-09", "ai_status": "ok", "excluded_private": 1,
  "draft": "本週（11/09–11/15）工作進度\n【本週完成】…",
  "items": [
    { "section": "delay", "task_id": 2, "event_id": 41, "title": "畫面規格", "owner": "小薇",
      "done_date": null, "orig_due": "2026-11-12", "latest_due": "2026-11-18", "blocked": null,
      "event": { "id": 41, "ts": "2026-11-10T10:00:00+08:00", "from_value": "2026-11-12",
                 "to_value": "2026-11-18", "delta_days": 6 } },
    { "section": "next", "task_id": 5, "event_id": null, "title": "驗收會議", "owner": "我",
      "done_date": null, "orig_due": null, "latest_due": "2026-11-19", "blocked": false, "event": null }
  ],
  "validated": true,
  "manual_text": null,
  "updated_at": "2026-11-16T10:00:00+08:00"
}
```

- `items.section` 為 `done`、`delay`、`next`；`next` 的 `event_id` 為 null（#18 第 6 點）。
- 每一項附可讀內容（2026-11-17 產品負責人裁定，#23）：讀取時由目前的任務與事件算出，不存進 `ai_items`，也不影響 AI-05 的輸出格式。各段的欄位如下，不屬於該段的欄位為 null：
  | section | 欄位 |
  | --- | --- |
  | 全部 | `title`（任務現值）、`owner` |
  | `done` | `done_date`；`event`＝完成事件 |
  | `delay` | `orig_due`、`latest_due`（任務現值）；`event`＝這一項對應的延後事件 |
  | `next` | `latest_due`、`blocked` |
  - `event` 只放結構化的事件證據：`{ id, ts, from_value, to_value, delta_days }`。不放來源原句（可被清除的原文，CLAUDE.md 資安 3、5），也不放評價欄位：延期原因、備註、時間管理註記、完成回報的星數與精力（FR-AI-06）。
  - 只列工作範圍的任務；任務改成私人範圍時，照第 1 點 (b) 整份改回事件清單，不會露出標題。
- `validated=true` 時，`draft` 為 AI 初稿，`items` 為 AI 回傳的項目；`validated=false`（AI 失敗或 R4 對不上）時 `draft=null`，`items` 為依歷程列出的事件清單，供手動撰寫（第 4 點）。
- 儲存（第 1 點 (b)）：`POST` 存 `ai_draft`、`ai_items`、`ai_status`，`manual_text` 不動。`GET` 回存下的 `ai_status`，並用存下的 `ai_items` 對**目前**的歷程重新對帳得出 `validated`，所以產生後任務改成私人範圍或做了基準更正，都會反映。
- `excluded_private` 為產生初稿當下送 AI 前排除的私人任務數（AC-48）。
- `GET /reports/weekly?week_start=` 依週次取得既有週報，不呼叫 AI、不寫入，輸出同上。`week_start` 不是星期一回 422 `VALIDATION_ERROR`（`details.fields` 為 `week_start`）；缺少或不是日期時也回 422，`details.fields` 沿用查詢參數的錯誤格式為 `query.week_start`。讀取不套用產生時的「不晚於本週、不早於 365 天」，該週沒有列一律 404。該週還沒產生時回 404 `NOT_FOUND`，`details` 只放 `week_start`：**這個 404 代表「尚未產生」，是正常狀態，不是錯誤**，前端顯示空狀態，不顯示錯誤橫幅（2026-11-17 產品負責人裁定，#23）。
- `PUT /reports/weekly/{id}/manual` 輸入：`{ "manual_text": "…" }`。不帶 `expected_version`，後寫的蓋掉先寫的（第 7 點）。可為 null 或空字串（清除人工版）；超過 20,000 字回 413 `PAYLOAD_TOO_LARGE`；內容相同照常儲存，不回 `NO_CHANGE`。（#18 J5；2026-11-17 定案）
- AI-05 的 payload、輸出、重試與紀錄見 5.3a（#22）。
- `GET`、`PUT` 的 id 不存在，或該 id 是目標回報（`kind='goal'`），回 404 `NOT_FOUND`。（#18 J10；2026-11-17 定案）
- `POST draft`、`PUT manual` 不存冪等快取：重播會略過重新對帳，快取也會多存一份人工版與初稿。以路徑前綴 `/api/v1/reports/weekly/` 排除（`NO_CACHE_PREFIXES`）。（#18 J7；2026-11-17 定案）

### 5.15 資料控制與維運

| Method | Path | 說明 |
| --- | --- | --- |
| POST | `/export` | 產生匯出檔 |
| POST | `/sources/purge` | 刪除所有來源原文；需 `{ "confirm": true }` |
| GET | `/meta/health` | 健康檢查（DB、AI 供應商可用性） |

---

## 6. 流程與邊界條件

### 6.1 收件到確認（對應序列 A1）

正常流程：

1. 提交文字 → 規則檢查（R1 綁定；大小限制）。
2. 摘錄寫入 `sources`（只存必要摘錄），去重。
3. ≤ 30 行：同步呼叫 AI-01；> 30 行：寫 `jobs(queued)`，回 `job_id`。
4. AI-01 輸出先存 `ai_runs.raw_output`。
5. R2 規則檢查與降級，寫入 `candidates(state=open)`。
6. 使用者在收件匣逐項確認，伺服器寫事件並更新任務。

例外處理：

| 情況 | 處理 |
| --- | --- |
| AI 逾時／輸出不合格式 | 從 AI-01 續跑，最多重試 2 次；仍失敗 → `jobs.failed`，保留摘錄，前端提示可手動建立任務 |
| 部分行無法解析 | 該行略過並計入 `skipped`，不影響其他行 |
| 全部行都被略過 | 回 `created=0`，提示「沒有找到可處理的訊息」 |
| 重複訊息 | 計入 `duplicates`，不重複建候選 |
| 候選對應任務在確認前已完成 | 確認時回 `TASK_DONE`，候選維持 `open`，前端提示改為忽略 |
| 候選對應任務在確認前被改期 | `expected_version` 不符回 `STALE_VERSION`，前端重新載入候選與任務 |
| 同一則訊息同時含延期與完成 | 本版只取一種：完成優先於延期；另一個留給使用者手動處理〔假設〕 |
| 輪詢超過 60 秒 | 前端停止輪詢，顯示「仍在處理，稍後回收件匣查看」，工作持續 |
| 服務重啟時有 `running` 工作 | 啟動時將 `running` 重設為 `queued` 續跑，嘗試次數保留 |

### 6.2 預計完成日調整與註記（對應圖 5）

正常流程：驗證 → 回傳確認面板內容（前值、後值、天數、相對原訂）→ 使用者選原因與註記 → 單一交易：寫 `due` 事件、更新 `latest_due`、`version+1`。

| 情況 | 處理 |
| --- | --- |
| 任務已完成 | `TASK_DONE` |
| 新日期等於目前 | `NO_CHANGE` |
| 新日期早於開始日 | 允許，回警告 `BEFORE_START` |
| 新日期早於今天 | 允許（可能補登），不警告 |
| 負責人是我，沒給註記 | `MARK_REQUIRED`；除非 `defer_mark=true` |
| 先調整、稍後註記 | 事件 `mark=NULL`；統計列為「未註記」；歷程顯示「補註記」 |
| 事後補註記 | 新增 `annotation` 事件；原事件不變；統計取有效註記 |
| 兩處同時調整同一任務 | 後到者 `STALE_VERSION`，前端重新載入 |
| 在調整與補註記之間，負責人被改為別人 | 補註記仍可進行（依事件的 `mine`，不依現在的負責人） |
| 提前時選了延後原因 | `VALIDATION_ERROR` |

### 6.3 整批順延（對應圖 6）

| 情況 | 處理 |
| --- | --- |
| 清單含已完成任務 | `INCLUDES_DONE_TASK`，不寫入 |
| 其中一項 `STALE_VERSION` | 整批回滾，回報過期的任務；前端重新預覽 |
| 其中一項寫入失敗 | 整批回滾；不留下部分批次 |
| 天數使新日期早於今天 | 預覽警告；允許 |
| 同批次要逐項不同註記 | 先套用統一註記或稍後註記，之後逐項補註記 |
| 清單中沒有我的任務 | 不要求註記；`mine_marked=0` |
| 重複提交（重新整理、連點） | 以 `Idempotency-Key` 回傳首次結果，不重複順延 |

### 6.4 基準更正（對應圖 7）

| 情況 | 處理 |
| --- | --- |
| 任務已完成 | `TASK_DONE` |
| 新日期等於目前原訂日 | `NO_CHANGE` |
| 缺原因 | `VALIDATION_ERROR` |
| commit 未帶聲明 | `ACK_REQUIRED` |
| 憑證過期、已使用、或任務在 preview 後變動 | `CONFIRMATION_INVALID`，需重新 preview |
| 更正後 `orig_due` 晚於 `latest_due` | 允許，差距為負（顯示「早於基準」）；甘特圖仍顯示基準框 |
| 更正後對過去註記的影響 | 無；過去事件與註記不重算 |
| 想再改回舊值 | 視為另一次基準更正，須再走兩段式，並再寫一筆事件 |

### 6.5 完成與完成回報

| 情況 | 處理 |
| --- | --- |
| 完成日晚於今天 | `VALIDATION_ERROR` |
| 完成日早於開始日 | 允許，逾期天數為 0 |
| 沒選星數或精力 | 不可儲存；可「稍後補」 |
| 稍後補 | 任務維持 `done`，進入待補清單；統計不計入該任務的完成回報 |
| 量表在填寫期間換版本 | 使用開啟面板時的版本；寫入該版本 id |
| 對非完成任務送回報 | `VALIDATION_ERROR` |
| 已有完成回報再送 | `FEEDBACK_EXISTS`（修改回報 9.3 未開放，#47 A1） |

### 6.6 AI 失敗時的退路

| 節點 | AI 失敗時 | 不可用也不影響 |
| --- | --- | --- |
| AI-01 候選抽取 | 工作標失敗，提示手動建立任務 | 手動建立與調整所有任務 |
| AI-02 星數提議 | 不提議，使用者自選 | 建立任務 |
| AI-03 目標關聯 | 不提議，使用者手選或不關聯 | 完成回報 |
| AI-04 目標回報草稿 | 顯示統計表 | 目標統計與矩陣 |
| AI-05 週報初稿 | 顯示事件清單，使用者自己寫 | 歷程與所有統計 |
| AI-06 量表訪談 | 沿用目前量表（回 503，前端保留） | 完成回報（以舊版量表） |
| AI-07 欄位對應 | 使用者手動指定欄位對應 | 匯入 |

### 6.7 資料保存與清除

- 清除排程（服務啟動時一次，之後每小時一次；冪等）：將 `expires_at` 已過的 `sources.excerpt` 設為 NULL，寫 `purged_at`。有原文被清除時，一併刪除 `idempotency_keys`（DA-23）。`created_at` 加保存天數已過的 `ai_runs.raw_output` 設為 NULL，不分節點（失敗的 AI-01 輸出連不回來源；AI-06、AI-07 的輸出也可能含原文；PR #20 B2）；另外，經背景工作的 `source_ids` 或候選的 `ai_run_id` 連得回已清除來源的輸出，也一併設為 NULL（背景工作可能晚於收件才呼叫 AI）。`events`、`candidates` 不動。（2026-11-15 裁定：原為每日 03:00，本機服務該時段常未開機會漏跑，改為每小時。）
- 修改保存期限時，尚未清除的來源一併重算 `expires_at = received_at + 新天數`（2026-11-15 裁定）。
- 「刪除所有來源原文」清除 `sources.excerpt`，刪除 `idempotency_keys` 全部列（回應本文可能含原句；這張表是 24 小時的重送暫存，不是歷程，DA-23），並將 `ai_runs.raw_output` 全部設為 NULL（PR #20 B2）。`events`、`candidates`、`tasks` 不動，事件的原句顯示改為已刪除。
- 匯出檔包含全部表；`sources.excerpt` 已清除者匯出為 `null`。`ai_runs` 匯出時不帶 `raw_output` 欄位（不論是否已清除），其餘欄位與筆數照常：`raw_output` 可能含收件原句，清除與匯出要同一立場，否則清了還能從匯出撈回；匯出是可外傳的快照，不帶 AI 原始輸出暫存（2026-11-17 產品負責人裁定，#40；取代 2026-11-16 PR #20 Q1 的「尚未清除的照帶」）。
- 匯出另外不帶下列欄位（2026-11-17 產品負責人裁定，#54，併 #46）。原則：可能含收件原句或 AI 原始輸出的欄位不進可外傳的快照；權杖一律不匯出；使用者刻意寫的業務內容保留。本條只改匯出，清除範圍不變（`reports.ai_draft`、`sources.speaker` 要不要一併清除，已在 #54 請產品負責人裁定）。
  | 表.欄位 | 理由 |
  | --- | --- |
  | `confirmations.token` | 基準更正的確認權杖，外流沒有正當用途 |
  | `idempotency_keys.response` | 重送暫存的回應本文，可能含 AI 草稿、匯入對應或候選原句 |
  | `reports.ai_draft` | 週報 AI 初稿，屬 AI 原始產出 |
  | `sources.speaker` | 收件原句的說話者 |
  | `sources.excerpt_hash` | 由時間、說話者與內容算出的去重雜湊；原文清除後仍可拿猜測的句子比對，只供內部去重（開發決定，#54） |
- 匯出照帶：`reports.manual_text`（使用者自己寫給主管的人工版，屬業務資料）；`ai_feedback.detail`、`jobs.payload`（核對後只有 id、欄位索引、計數與行號，不含原文；#54 回報產品負責人）。

### 6.8 並行與一致性

- 所有寫入在單一交易內完成「事件＋任務狀態」兩件事，不可只寫其中一邊。
- 交易隔離層級為 READ COMMITTED；修改任務時以 `SELECT … FOR UPDATE` 鎖定任務列，並比對 `version`；遇死結或序列化失敗（SQLSTATE `40P01`、`40001`）重試最多 3 次（間隔 50 ms）。
- 前端以 `version` 偵測過期；收到 `STALE_VERSION` 一律重新載入再讓使用者重做，不自動重送。

---

## 7. 驗收標準

格式為 Given／When／Then。「事件」皆指 `events` 資料列。

### 7.1 預計完成日與註記

- AC-01 Given 匯入專案的任務 A（負責人阿德，未完成）；When 呼叫 `adjust-due` 新日期晚 3 天且不帶註記；Then 回 200，`latest_due` 更新、`orig_due` 不變，事件 `mine=0`、`mark=NULL`，不回 `MARK_REQUIRED`。
- AC-02 Given 任務 B（負責人我）；When 調整日期且沒有 `mark` 也沒有 `defer_mark`；Then 回 422 `MARK_REQUIRED`，任務與事件都沒變。
- AC-03 Given 同上；When 帶 `mark=none`；Then 事件 `mark='none'`，`delta_days` 等於新舊日期差，`orig_due` 不變。
- AC-04 Given 同上；When 帶 `defer_mark=true`；Then 事件 `mark=NULL`，回 `needs_mark=true`，時間管理統計的「未註記」加 1。
- AC-05 Given 單點任務（無專案）；When 調整日期；Then 與專案任務一樣成功，事件的 `project_id` 為 NULL，歷程以「單點任務」篩選找得到。
- AC-06 Given 已完成任務；When 調整日期；Then 回 409 `TASK_DONE`。
- AC-07 Given 新日期等於目前值；Then 422 `NO_CHANGE`。
- AC-08 Given 一個 `mark=NULL` 的日期事件；When `POST /events/{id}/annotations` `mark=worse`；Then 新增 `annotation` 事件，原事件的列內容完全未變，統計「變差」加 1、「未註記」減 1。
- AC-09 Given 已有註記 `worse`；When 再補註記 `none`；Then 有效註記為 `none`，歷程仍保留兩筆註記事件。
- AC-10 Given `mine=0` 的日期事件；When 補註記；Then 422 `ANNOTATION_NOT_ALLOWED`。
- AC-11 Given 事件資料列；When 直接對 `events` 執行 UPDATE 或 DELETE；Then 資料庫拒絕（觸發器 ABORT）。
- AC-12a Given 確認一筆 `delay` 候選；Then 回應與介面的 `reason`、`mark` 皆為空，AI 輸出中即使含原因推測也不被採用或顯示。
- AC-12 Given 負責人是我、原因為 `wait_external`；When 取得原因選項與調整面板資料；Then `external=true`，介面顯示「建議不計入」；伺服器**不**因此自動設定註記。
- AC-13 Given 時間管理統計；When 事件有效註記分別為 `better`、`worse`、`none`、NULL 各 1 筆且皆 `mine=1`；Then 統計為變好 1、變差 1、不計入 1、未註記 1；`mine=0` 的事件不計入任何一項。

### 7.2 整批順延

- AC-14 Given 專案內 5 項未完成任務，勾選其中 4 項；When commit 延後 3 天；Then 4 項 `latest_due` 各 +3、`orig_due` 不變，產生 4 筆 `due` 事件且 `batch_id` 相同，另 1 項不變。
- AC-15 Given 勾選的任務中有 2 項是我的；When commit 帶 `mark=none`；Then 這 2 項的事件 `mark='none'`，其餘事件 `mine=0`、無註記。
- AC-16 Given 勾選的任務含 1 項已完成；Then 422 `INCLUDES_DONE_TASK`，沒有任何任務被改。
- AC-17 Given 勾選中有 1 項的 `expected_version` 過期；Then 409 `STALE_VERSION`，**4 項全部**未變、無批次記錄。
- AC-18 Given 同一 `Idempotency-Key` 連送兩次；Then 第二次回傳首次結果，批次與事件只有一份。
- AC-19 Given 預覽；Then 不寫入任何資料；新日期早於今天的項目有 warnings。

### 7.3 基準更正

- AC-20 Given 任務 `orig_due=11/12`；When preview 新原訂日 11/14；Then 回確認憑證與影響說明（差距與已延期數的前後值、過去日期事件數）；`tasks`、`events` 未變，只在 `confirmations` 新增一列憑證（DA-21）。
- AC-21 Given 有效憑證；When commit 不帶 `ack=true`；Then 422 `ACK_REQUIRED`，`orig_due` 不變。
- AC-22 Given 有效憑證與 `ack=true`；When commit；Then `orig_due=11/14`，新增 `baseline` 事件含前值 11/12、後值 11/14、類型與原因；該任務過去的 `due` 事件與註記完全未變。
- AC-23 Given 憑證已使用或超過 10 分鐘，或任務在 preview 後被改；Then 409 `CONFIRMATION_INVALID`。
- AC-24 Given 已完成任務；Then preview 與 commit 都回 409 `TASK_DONE`。
- AC-25 Given 基準更正後；Then 甘特圖基準框、專案「已延期」數、週報的延期段落都以新原訂日計算。

### 7.4 專案與歷程

- AC-26 Given 專案；When 同時改名稱與範圍；Then 產生 2 筆 `project` 事件，各記前值與後值；When 未改任何欄位；Then 不產生事件。
- AC-27 Given 多個專案與多種事件；When `GET /events` 帶 `project_id`、`kind`、`task_id` 組合；Then 結果只含符合者，`total` 正確；`project_id=none` 只回單點任務事件。
- AC-28 Given 事件來自某則訊息；When 來源原文已過保存期限被清除；Then 事件仍在，`source.purged=true`、`quote=null`。
- AC-29 Given 任務被改名或改負責人；Then 舊事件的 `task_title`、`mine` 不變。

### 7.5 匯入

- AC-30 Given 含 7 列的表格，其中 1 列缺結束日期、1 列結束早於開始、1 列重複名稱、1 列缺負責人；When preview；Then 兩個錯誤列標 `blocking`，重複與缺負責人為警告，`importable` 數正確。
- AC-31 Given 有未略過的錯誤列；When commit；Then 422，不匯入任何列。
- AC-32 Given 全部合法；When commit；Then 建立對應任務，`orig_due=latest_due=結束日期`、`star_source='import_default'`，並有 1 筆 `baseline` 事件；交易失敗時一列都不留。
- AC-33 Given 表頭非標準名稱；Then 規則無法對應時才呼叫 AI-07，回 `mapped_by='ai'`；AI 不可用時回 `mapped_by=null`，使用者可手動指定。

### 7.6 收件與候選

- AC-34 Given 候選為 `open`；When 查詢甘特圖、統計、週報；Then 這些結果都不含該候選的影響。
- AC-35 Given 訊息為「下週測試如果環境沒好，會不會卡住？」；Then 不產生 `stuck`，而產生 `unclear`（待釐清）；確認前任務 `blocked` 不變。
- AC-36 Given 訊息含「可能」的延期；Then 候選為 `unclear`，不是 `delay`。
- AC-37 Given 訊息認不出對應任務；Then 候選為 `unmatched`，系統不自行猜測任務。
- AC-38 Given 貼上同一段文字兩次；Then 第二次 `duplicates` 計數，不新增候選。
- AC-39 Given 確認 `delay` 候選，任務負責人是我；Then 回 `needs_mark=true`；負責人不是我則 `false`。
- AC-40 Given AI-01 回傳不合格式；Then 重試至多 2 次，仍失敗工作為 `failed`，摘錄保留，沒有任何候選或事件被寫入。
- AC-41 Given 超過 30 行；Then 回 `mode=async` 與 `job_id`，工作狀態可查詢。
- AC-42 Given 未綁定的 LINE 群組訊息；Then 丟棄，不寫 `sources`。

### 7.7 完成回報與目標

- AC-43 Given 完成任務；When 儲存回報缺星數或缺精力；Then 422。
- AC-44 Given 完成日晚於原訂日 2 天；When 儲存回報；Then `overdue_days=2`；前端送來的 `overdue_days` 被忽略。
- AC-45 Given 回報儲存；Then 記錄 `rubric_id` 為當時版本；量表之後換版不改既有回報。
- AC-46 Given 目標關聯事件 3 筆；Then 統計回傳分布，`judgement=null` 與樣本不足說明；Given 5 筆以上；Then 回判讀，且判讀為程式規則結果。
- AC-47 Given AI-03 建議目標 A，使用者改選 B；Then 關聯為 B，`ai_feedback.outcome='changed'`。

### 7.8 週報與 AI

- AC-48 Given 含私人範圍任務；When 產生週報；Then 私人範圍任務不出現在送給 AI 的輸入與初稿中，`excluded_private` 為其數量。
- AC-49 Given 初稿中有一項延期在歷程中找不到事件；Then `validated=false`，不顯示初稿，改回事件清單。
- AC-50 Given AI 供應商不可用；Then 週報、目標回報、星數提議、關聯建議端點皆回 200 並附退路內容；量表訪談回 503；所有非 AI 功能照常。
- AC-51 Given 週報人工版已修改；When 重新產生 AI 初稿；Then 人工版內容不被覆蓋。

### 7.9 資料控制與非功能

- AC-52 Given 保存期限 30 天；When 清除排程執行；Then 超過期限的 `excerpt` 為 NULL，事件與候選仍在。
- AC-53 Given 「刪除所有來源原文」；When 未帶 `confirm=true`；Then 拒絕；帶了則所有 `excerpt` 為 NULL。
- AC-54 Given 匯出；Then 檔案為合法 JSON，含所有表，且表的筆數與資料庫一致。Given `ai_runs` 有 `raw_output`（不論是否已清除）；Then 匯出的 `ai_runs` 每列都沒有 `raw_output` 欄位，其餘欄位與筆數照常（#40）。Given 6.7 列出的其他排除欄位（`confirmations.token`、`idempotency_keys.response`、`reports.ai_draft`、`sources.speaker`、`sources.excerpt_hash`）有值；Then 匯出的對應表每列都沒有這些欄位，其餘欄位與筆數照常，`reports.manual_text` 照帶（#54）。
- AC-55 Given 500 列匯入；Then preview 在 2 秒內完成（不含 AI-07）〔假設〕。
- AC-56 Given 1,000 個任務、10,000 筆事件；Then `GET /events`（含篩選）在 300 ms 內回應〔假設〕。
- AC-57 Given 任一寫入端點中途丟出例外；Then 事件與任務狀態都未變（沒有只寫一半）。

### 7.10 完成定義

P1 完成 = AC-01 至 AC-42、AC-48 至 AC-53、AC-55 至 AC-57 全數通過，並以真實專案資料試用 2 週，量測第 1.3 節的衡量值，作為 G2 校正依據。P2 另需 AC-43 至 AC-45；P3 另需 AC-46、AC-47。

---


### 7.11 追加驗收標準（2026-11-15）

編號由產品負責人指定。

- AC-59 Given 全新資料庫；When 跑完遷移；Then `settings` 恰 1 列、`rubrics` 恰 1 列（version=0、`levels` 剛好 5 句）；When 遷移降級再升級，或重跑種子；Then 兩表仍各 1 列。
- AC-61 Given 建立任務時指定開始日；Then 任務的 `start_date` 為該日；Given 指定的開始日晚於期限；Then 422 `VALIDATION_ERROR`，`details.fields` 含 `start`，不建立任務也不寫事件。
- AC-62 Given 未完成任務；When `POST /tasks/{id}/adjust-start` 帶新開始日；Then 只有 `start_date` 改變（`orig_due`、`latest_due` 不變）、`version` 加 1，並新增一筆 `task` 事件（`field='start_date'`，前值、後值，`delta_days` 與 `mark` 為 NULL），該事件不進時間管理統計；Given 新開始日晚於最新預計日；Then 200 且 `warnings` 含 `START_AFTER_DUE`；Given 已完成任務、等於目前值、或超出日期範圍；Then 分別回 `TASK_DONE`、`NO_CHANGE`、`DATE_OUT_OF_RANGE`。
- AC-64 時間管理判讀（FR-MRK-07）。以下「變差」各在不同任務上：
  - Given 變好 1 次、變差 3 次（樣本 4）；Then `judgement=null`，`judgement_note`＝「樣本 4 筆，不到 5 筆，只顯示不下結論」。
  - Given 變好 4 次、變差 2 次；Then `judgement`＝「時間管理偏向變好」，`judgement_note`＝「變好 4 次、變差 2 次。」
  - Given 變好 2 次、變差 3 次，3 個任務中 2 個是低精力；Then `judgement`＝「偏向變差，建議檢視」，`judgement_note`＝「變好 2 次、變差 3 次。變差多集中在低精力任務。」
  - Given 變好 1 次、變差 4 次，4 個任務為低 2、中 2；Then `judgement`＝「偏向變差，建議檢視」，`judgement_note`＝「變好 1 次、變差 4 次。」（剛好一半，不加集中提示）
  - Given 變好 3 次、變差 3 次；Then `judgement`＝「持平」。
- AC-63〔編號暫定，待產品負責人指定〕 Given 匯入的表頭由 AI-07 對應（`mapped_by="ai"`）；When commit 帶回 `ai_run_id` 與最終 `column_map`；Then 新增恰 1 筆 `ai_feedback`（`node_id='AI-07'`、`target_type='import_map'`、`target_id` 為回應的 `event_id`），最終對應與 AI 建議相同為 `accepted`、不同為 `changed`，`detail` 只含欄位索引；Given 同一 `ai_run_id` 再 commit 一次；Then 匯入成功、回饋仍為 1 筆；Given 只帶其中一項，或 `ai_run_id` 不是 `ok` 的 AI-07 紀錄；Then 422 `VALIDATION_ERROR`，不建立任務也不寫回饋。
- AC-65 週報彙整（FR-RPT-01、02；#18 裁定）：
  - Given 本週有延後事件、之後基準更正使 `latest_due ≤ orig_due`；Then 該任務不列入延期。
  - Given 已完成任務 `done_date` 在本週但沒有 `to_value='done'` 的 `status` 事件；Then 不列入本週完成。
  - Given 未完成、未卡住、`latest_due` 早於下週一；Then 列入 `next`。Given 封存專案裡卡住的任務；Then 不列入 `next`。
  - Given `week_start` 不是星期一，或晚於本週；Then 422 `VALIDATION_ERROR`，`details.fields` 含 `week_start`。
- AC-66 週報存檔與對帳（FR-RPT-03、04）：
  - Given 同一週產生兩次初稿；Then `reports` 只有一列，第二次只更新 AI 初稿。
  - Given AI 回傳的 `next` 項目引用私人任務或不存在的任務；Then `validated=false`，`draft=null`，`items` 為事件清單。
  - Given 已產生並通過對帳的初稿，之後項目裡的任務改為私人範圍；When `GET`；Then `validated=false`。
  - Given 已有成功的初稿；When 重新產生時 AI 不可用；Then 該次回應為退路內容，`GET` 仍回上次成功的初稿。（#18 H2；2026-11-17 定案）
  - Given 某週已產生週報；When `GET /reports/weekly?week_start=` 該週；Then 回同一列，內容與 `GET /{id}` 相同，不呼叫 AI；Given 該週尚未產生；Then 404 `NOT_FOUND`，`details` 只有 `week_start`；Given `week_start` 不是星期一；Then 422 `VALIDATION_ERROR`（#23）。
  - Given 任一週報回應；Then 每個 item 帶該段的可讀欄位（`title`、`owner`、日期、`event` 事件證據），不屬於該段的欄位為 null，且不含延期原因、備註、註記、星數、精力與來源原句（#23）。
- AC-67 人工版（FR-RPT-04）：Given 週報存在；When `PUT /manual`；Then `manual_text` 更新，其他欄位不變；Given id 不存在；Then 404 `NOT_FOUND`。

## 8. 技術棧／限制

### 8.1 技術棧

| 層 | 選擇 | 理由 |
| --- | --- | --- |
| 後端語言與框架 | Python 3.12、FastAPI、Pydantic v2 | 型別驗證與 OpenAPI 文件自動產生，錯誤格式容易統一 |
| 資料存取 | SQLAlchemy 2.x（Core 為主）、Alembic、psycopg 3 | 交易與遷移明確；`events` 只增觸發器以遷移腳本管理 |
| 資料庫 | PostgreSQL 15+ | 行級鎖與觸發器完整；`pg_dump` 備份；可隨資料匯出 |
| 背景工作 | 行程內 worker（asyncio）＋ `jobs` 資料表 | 不引入 Redis；重啟後可由資料表恢復 |
| 排程 | APScheduler | 每日合併確認推播、原文清除 |
| AI 介面 | `AIClient` 抽象類別；供應商以設定檔指定 | 可替換、可在測試中以假實作取代 |
| 前端 | React 18、TypeScript、Vite | 元件化；以同一份程式碼提供手機與網站兩種版面 |
| 前端狀態與資料 | TanStack Query | 快取與重新載入，配合 `STALE_VERSION` 流程 |
| 前端路由與樣式 | React Router、CSS 變數（亮暗色） | 沿用互動原型的設計語彙 |
| 甘特圖 | 自繪 SVG | 需求簡單（基準框、延後區間、今天線），不引入大型套件 |
| 測試 | pytest（後端）、Vitest（前端）、Playwright（端對端） | 驗收標準直接對應端對端與 API 測試 |

### 8.2 架構與限制

- 單機部署：一個後端行程＋靜態前端＋一個 PostgreSQL 執行個體（只綁 `127.0.0.1`）。
- 平台分工（沿用原型決策）：手機重在收件匣、今日、確認、完成回報；網站重在基準、甘特圖、匯入、整批順延、週報、目標管理、歷程。兩者用同一套 API。
- 不建帳號：負責人是名字字串；「我」是固定的保留字。多人協作不在這一版。
- 時區固定 Asia/Taipei；不處理跨時區。
- 日期只到「日」，不含時間；工作日與假日曆不納入（延後 3 天就是日曆上 3 天）。
- 資料量假設：單一使用者，任務 ≤ 數千筆、事件 ≤ 數萬筆。
- AI：不得要求 AI 輸出自由文字後直接寫入資料；所有 AI 輸出皆須通過結構驗證與規則檢查。
- 隱私：送進 AI 的內容為必要摘錄與任務清單；私人範圍不進週報；供應商資料處理條件須在上線前確認〔待決〕。
- 安全：API 預設只綁 `127.0.0.1`；對外開放前須加 TLS 與 token 輪替。
- 備份：每日以 `pg_dump`（custom 格式）備份，保留 14 份〔假設〕。
- 可觀測性：記錄每次 AI 呼叫、重試與失敗（`ai_runs`）；以 `ai_feedback` 與事件推導評估指標，不另建分析資料庫。

### 8.3 建議目錄結構

```
backend/
  app/
    main.py
    api/            # routers：settings, projects, tasks, events, candidates, ...
    domain/         # 規則：due.py, marks.py, bulk.py, baseline.py, ingest_rules.py, stats.py
    ai/             # AIClient, nodes/ai01..ai07.py, validators.py
    db/             # models.py, migrations/（含 events 觸發器）
    jobs/           # worker.py, scheduler.py
  tests/            # 對應第 7 章 AC 編號
frontend/
  src/
    features/       # inbox, today, tasks, projects, gantt, history, goals, reports, settings
    components/
    api/            # 型別由 OpenAPI 產生
```

---

## 9. 待決事項與假設

### 9.1 待決（需要你裁定）

| 編號 | 事項 | 我的建議 |
| --- | --- | --- |
| D-01 | AI-02 星數提議是否進 P1 | P1 先不上，或預設關閉；前 10 件由你自設星數，避免錨定 |
| D-03 | 送進 AI 前是否遮蔽姓名 | 看你更重視隱私還是 AI-01 判斷負責人的準確度 |
| D-04 | 週報是否由系統代發 | P1 不代發，只產生文字 |
| D-05 | 完成回報儲存後是否允許修改 | 允許，以新增更正事件實作，統計取最新 |
| D-06 | LINE 群組綁定是否放 P1（P1b） | 貼上入口為 P1 必要；LINE 視開發量決定 |
| D-07 | 同一則訊息含延期與完成時的處理 | 完成優先，延期留待手動 |

### 9.2 已裁定（本規格依此撰寫）

1. 精力以事件完成回報為主；事前預設星數，完成時回報實際星數；自評精力高／中／低為必填。
2. P1 同時含專案閉環與單點、每日兩條軌道。
3. 會議錄音線先排除，以逐字稿入口啟動；負責人用名字，不建帳號；多人協作不在這一版。
4. 星數量表由啟用時的 AI 訪談個人化，版本化，AI 只提議預設值。
5. 預計完成日調整需詢問時間管理註記；專案須記錄修改歷程。
6. 整批順延：我的任務套用統一註記，逐項不同在歷程改註記。
7. 基準更正：**直接覆蓋原訂日，舊值只留在歷程**，不做基準版本；單人版不限制權限，僅靠兩段式確認。
8. 延期原因與時間管理註記**一律由使用者判斷，不設 AI 節點**（原 AI-08 取消，不列入後續階段）。原因連動「建議不計入」提示再連到註記，任何 AI 預填都會間接影響對自己的評價。（原 D-02，已結案）
9. Dev-A 開發期間的決定紀錄 DA-01～DA-26（`docs/decisions.md`）已由產品負責人複核（2026-11-16，issue #15）。DA-12 以外全部照原決定，結論已寫入本規格各條，條文後以「（DA-xx）」標示出處。DA-12 新增「二元判讀＋精力洞察」規則，已寫入 FR-MRK-07、5.8 與 AC-64。

### 9.3 本文件中的〔假設〕清單

AI 建議採用率 ≥ 70%、註記完成率 ≥ 80%、完成回報填寫率 ≥ 70%；同步與背景工作的門檻（30 行）；輪詢間隔與上限（3 秒、60 秒）；AI 逾時 20 秒；基準更正憑證 10 分鐘；少於 5 筆不下判讀；日期範圍（今天前 365 天至後 730 天）；效能目標（AC-55、AC-56）；備份保留 14 份。以上全部待 G2 以實測校正。

### 9.4 可追溯對照

| 本文件 | 對應 |
| --- | --- |
| FR-INB、FR-DUE、FR-MRK | 序列圖 3、5；AI 增強 A1 |
| FR-BLK | 序列圖 6 |
| FR-BAS | 序列圖 7 |
| FR-IMP | 序列圖 2；AI 增強 A3 |
| FR-SET、FR-RUB | 序列圖 1；AI 增強 A3 |
| FR-FBK、FR-GOL、FR-RPT | 序列圖 4；AI 增強 A2 |
| FR-AI、第 6.6 節 | AI 節點盤點 v0.1（AI-01 至 AI-07） |
