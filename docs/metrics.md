# 衡量值埋點檢查（todo 13.8，資料面）

檢查 spec 1.3 的五個衡量值能不能只靠資料庫算出來。查詢寫在 `backend/app/db/repo/metrics_repo.py`，測試在 `backend/tests/unit/test_metrics_queries.py`，已在 PostgreSQL 17 上通過。

這份是 Dev-A 的資料面檢查。用兩週真實試用資料驗算是 QC-2 的工作（todo 5.5、13.9）。

2026-11-17 依 main（含 PR #20 的 Phase 5–8）重新檢查一次；Phase 10 週報（PR #23）尚未合併，相關內容標明「#23 合併後」。

| # | 衡量值（spec 1.3） | 可否計算 | 算法 |
| --- | --- | --- | --- |
| 1 | 週報中每個延期與完成 100% 對得上歷程事件 | **#23 合併後可以，定義待裁定** | 見下方「待裁定 1」 |
| 2 | 每日確認時間不超過上限 | **只能近似** | 每天第一筆到最後一筆候選處理的分鐘數（`daily_confirm_span_minutes`），只能當上限參考；見「待裁定 2」 |
| 3 | 候選確認率（含修改後確認）≥ 70% | 可以 | `candidates.state`：confirmed ÷（confirmed＋ignored）；`open` 不計。`create-task` 是否算確認見「待裁定 3」 |
| 4 | 我的日期調整，註記完成率 ≥ 80% | 可以 | mine、`delta_days≠0` 的 `due` 事件中，有效註記非空的比例。母體與有效註記直接用時間管理統計的查詢（`events_repo.mine_due_events_with_effective_mark`），兩處口徑一致 |
| 5 | 完成事件中，完成回報填寫率 ≥ 70% | 可以（Phase 9 前恆為 0） | 已完成任務中有 `completion_feedback` 的比例 |

## 各項的資料依據（2026-11-17 檢查）

- **衡量值 3**：main 上改 `candidates.state` 的地方只有 `inbox/confirm.py` 的 `_close`，四種處理分別記成：
  | 動作 | `state` | `ai_feedback.outcome` |
  | --- | --- | --- |
  | 確認（confirm）、釐清（clarify） | `confirmed` | `accepted`；延期候選改了日期時為 `edited` |
  | 建立新任務（create-task） | `confirmed` | `changed` |
  | 忽略 | `ignored` | `ignored` |

  每次處理都寫一筆 `ai_feedback`（`node_id='AI-01'`、`target_type='candidate'`），所以「修改後確認」可以用 `outcome='edited'` 分開看。原本的缺口 3 已解決。
- **衡量值 4**：候選確認與整批順延產生的 `due` 事件都經 `write_event`，`mine`、`delta_days` 由伺服器計算，和手動改期同一個母體。
- **衡量值 5**：任務完成後不能改回未完成（`set_status` 與 `complete_task` 都擋 `TASK_DONE`；DA-08、DA-16），匯入也不會建立已完成的任務，所以「已完成任務」就等於「完成事件」，每個任務最多一筆完成回報（`completion_feedback.task_id` UNIQUE）。Phase 9（完成回報）還沒做，main 上沒有任何程式寫 `completion_feedback`，所以目前比率恆為 0。
- **todo 13.8 提到的 `jobs`**：五個衡量值都不需要它。`jobs` 只記收件背景工作的排隊與重試，和確認率、確認時間無關。`ai_feedback` 可以用在衡量值 3 的細分。

## 待裁定（交產品負責人）

1. **衡量值 1 量的是什麼** 【待複核：規格缺口】
   - #23 合併後的資料：每次 AI-05 嘗試寫一列 `ai_runs`，R4 對帳失敗記 `error='R4_MISMATCH'`；`reports.ai_items` 存下初稿每一項對應的 `task_id`、`event_id`。
   - 但 R4 對不上時初稿會被丟掉、改顯示依歷程列出的事件清單，所以「顯示出來的週報」本來就一定對得上，照字面算永遠是 100%。可能的定義：
     - **A：AI 初稿的對帳通過率**＝AI-05 回傳格式正確的嘗試中，R4 通過的比例（`ai_runs`：`node_id='AI-05'`，通過＝`status='ok'` 且 `error IS NULL`，失敗＝`error='R4_MISMATCH'`）。量的是 AI 錨定的風險。
     - **B：照字面量顯示的週報**，結果恆為 100%，只能當系統保證，不能當校正依據。
   - 另有兩點一起確認：人工版（`manual_text`）不經對帳，算不算在衡量範圍內；R4 失敗的狀態值在 #22 還沒定案，A 的算法只看 `error`，不受影響。
   - Dev-A 建議 A。裁定後在 `metrics_repo` 加查詢與測試。
2. **衡量值 2 接受近似值嗎** 【待複核：規格缺口】
   - FR-INB-16 要求「記錄實際使用時間供校正」，但資料表沒有欄位。Dev-B 的 Phase 7 SDD Q7 與 12.8 SDD D-3 決定不記實際使用時間，沿用近似值。
   - 近似值的限制：中間離開也會算進去，只能當上限。13.9 試用要量「每日確認時間」，需要裁定：(a) 接受近似值，spec 1.3 註明；或 (b) 另開票加遷移與前端計時。
3. **衡量值 3 的 create-task 算不算確認** 【待複核：規格解讀】
   - 候選對不到既有任務、使用者改建新任務時，`state='confirmed'`、`outcome='changed'`。目前算在確認裡。
   - 如果「AI 候選有用」只想算 AI 建議本身被採用，分子應排除 `changed`，改用 `ai_feedback` 計算。
