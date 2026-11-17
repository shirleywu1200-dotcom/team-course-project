# PR #20 審查 B 段 SDD：私人專案不送 AI、清除 raw_output、去重含日期、候選沿用專案

依據：PR #20 Dev-A 審查 B 段 4～8 點；產品負責人裁定（2026-11-16 PR #20 留言，B1～B5）；Dev-A 補充（同日，B2 不需 DDL、AI-07 回饋讀到 NULL 不可 500、spec 6.7 合併文字）。
狀態：**Mora 已同意（2026-11-16）**；B1～B3 在 #20 實作，B5 在 #20 合併後另開 PR。

## 實作順序

1. 先 rebase 到 main（`4f15217`）：spec 6.7 衝突採 Dev-A 建議的合併文字，B2 範圍依本文 B2-2 修改。
2. B1 → B3 → B2。B5 牽涉 DDL，移到 #20 合併後另開 PR（見 B5-3）。
3. 每項先寫失敗測試，再實作；全部完成後跑後端、前端全套測試與 ruff、tsc。

## B1 私人專案的收件不呼叫 AI-01（資安規則 2）

- **B1-1 擋點放 `process_sources`**：同步與背景工作都經過這裡，只擋一處就涵蓋兩條路。`project_id` 指向 `scope='private'` 的專案時，不呼叫 `AIClient`，回 `Outcome("unavailable", attempts=0, skipped=len(source_ids))`。
  架構後果：(a) `sources` 照常寫入，使用者可在收件匣手動建任務（同 FR-INB-08 的失敗退路）(b) 不寫 `ai_runs`，因為沒有呼叫 (c) 背景工作照「AI 不可用」的路徑結束，`jobs.error` 用既有的 `FAILED_MESSAGE`，不另立狀態
- **B1-2 測試**：同步、背景各一個「`FakeAIClient.calls` 為空、`ai_status="unavailable"`」；另一個測試確認工作範圍專案照常呼叫。
- 契約：回應形狀不變，前端不用改。

## B3 有日期標頭時，日期併入去重雜湊（FR-INB-04）

- **B3-1** `parse_text` 遇到日期標頭時，記下標準化後的日期（`YYYY-MM-DD`），之後的訊息都帶這個日期；`Message` 新增 `date: str | None`。
- **B3-2** 雜湊：有日期時鍵為「日期＋時間＋發言者＋內容」；沒有日期時維持原本的「時間＋發言者＋內容」。
  架構後果：(a) 沒有日期標頭的既有資料，雜湊值不變，不用重算 (b) `sources.spoken_at` 仍只存 HH:MM，不改 DDL、不改回應 (c) 同一段對話第一次沒貼日期標頭、第二次有貼，會被當成不同訊息而重複收件，列為已知限制
- **B3-3 測試**：同時間、同人、同內容但日期不同 → 兩則都收；日期相同 → 第二則算重複；無日期 → 行為與現在相同。

## B2 清除原文時一併清除 `ai_runs.raw_output`（FR-GOV-01、03，資安規則 5）

- **B2-1 「刪除所有來源原文」**：`ai_runs.raw_output` 全部設為 NULL。
- **B2-2 到期清除的範圍：依 `ai_runs.created_at` 判斷，不分節點**。條件為 `raw_output IS NOT NULL AND created_at + 保存天數 <= now`，保存天數讀目前設定（和 `sources` 重算 `expires_at` 用同一個值）。
  理由：失敗的 AI-01 紀錄（不合格式的輸出）沒有候選可連回 `sources`，只靠 `candidates.ai_run_id` 會漏清；AI-06 量表訪談、AI-07 表頭對應的輸出也可能帶使用者原文。依建立時間判斷可以一次涵蓋，也不需要新欄位。
  架構後果：(a) 不改 DDL（Dev-A 已確認 `raw_output` 可為 NULL）(b) 每小時清除排程多一條 UPDATE，和既有清除在同一交易 (c) 和原文的保存天數一致，使用者只需要理解一個期限
- **B2-3 AI-07 回饋讀到 NULL**：`imports.service._ai_suggestion` 讀到 `raw_output` 為 NULL 時回 None，等同未帶 `ai_run_id`：不寫回饋，匯入照常成功（現在會在 `json.loads(None)` 丟例外而回 500）。
- **B2-4 文件**：spec 6.7 依 Dev-A 的合併文字補 B2；`CLAUDE.md` 資安規則 3 補「清除原文時一併設為 NULL（PR #20 B2）」。
- **B2-5 測試**：到期清除只清超過期限的列；全部清除清全部；清除後匯出的 `raw_output` 為 null；AI-07 preview 之後清除、再 commit → 201 且沒有回饋列。

## B5 候選建任務時沿用收件時的專案（FR-INB-14）

- **B5-1 資料**：`candidates` 新增 `project_id BIGINT REFERENCES projects(id)`（可為 NULL）。收件時把 `ingest` 的 `project_id` 寫進每筆候選；背景工作的 `jobs.payload` 已經帶 `project_id`，直接傳下去。
- **B5-2 建任務時由伺服器帶入**：`POST /candidates/{id}/create-task` 的 `project_id` 沒送時，用候選上的 `project_id`；有送則以送來的為準。
  架構後果：(a) 前端 `CandidateCard` 不用改，凍結的 `api/types.ts` 也不用動，Dev-C 11.8 不需要多吸收一項 (b) 和裁定文字「CandidateCard 建任務時送出」做法不同，結果相同；專案的真相留在伺服器，不靠前端回傳 (c) 使用者若要在建任務時改專案，之後由前端送 `project_id` 覆寫即可，不用再改後端
- **B5-3 DDL 與排程（2026-11-16 定案）**：遷移由 Dev-A 寫（path-owners），用欄位不用 JSONB，另開只含遷移的小 PR。遷移以 `down_revision` 串成一條鏈，所以編號採「先合進 main 的拿 0004」，避免出現指向不存在的上一版或兩個 head。**B5 移出 #20**：#20 同時卡著 Dev-C 的 12.1／12.3／12.6 與 Dev-A 週報段落 3，B5 不影響既有功能；遷移進 main 後從 main 開分支做 B5，單獨開 PR（已在 #20 留言說明，請產品負責人確認）。
  架構後果：(a) #20 只做 B1～B3，不等 DDL (b) B5 的 PR 依賴遷移小 PR 先合
- **B5-4 通知**：B5 是後端行為與 DDL 新增，開 issue 通知 Dev-C、QC-2（照 #25 的格式）。

## B4（不做）

照裁定，AI 失敗後不提供重新解析，保留摘錄並可手動建任務（FR-INB-08）。重新解析列為未來增強，另開票。

## 不在本 SDD

- 驗收測試（產品負責人裁定由 Dev-B 自補）：範圍另列 AC 清單給 Mora 確認。
- C 段：`ai_run_id` 前端交給 Dev-C 11.8；AI 紀錄與重試重構另開票。
