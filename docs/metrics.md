# 衡量值埋點檢查（todo 13.8，資料面）

檢查 spec 1.3 的五個衡量值能不能只靠資料庫算出來。查詢寫在 `backend/app/db/repo/metrics_repo.py`，測試在 `backend/tests/unit/test_metrics_queries.py`，已在 PostgreSQL 17 上通過。

這份是 Dev-A 的資料面檢查。用兩週真實試用資料驗算是 QC-2 的工作（todo 5.5、13.9）。

2026-11-17 依 main（含 PR #20 的 Phase 5–8）重新檢查一次，三項定義已裁定（#34）；Phase 10 週報（PR #23）尚未合併，相關內容標明「#23 合併後」。

| # | 衡量值（spec 1.3） | 可否計算 | 算法 |
| --- | --- | --- | --- |
| 1 | 週報中每個延期與完成 100% 對得上歷程事件 | **#23 合併後可以** | AI-05 回傳格式正確的嘗試中 R4 通過的比例：`ai_runs` 的 `node_id='AI-05'`，通過＝`status='ok'` 且 `error IS NULL`，失敗＝`error='R4_MISMATCH'`。人工版不納入（#34 裁定 1）。查詢待 #23 合併後補 |
| 2 | 每日確認時間不超過上限 | 近似（已裁定接受） | 每天第一筆到最後一筆候選處理的分鐘數（`daily_confirm_span_minutes`）。只會高估，對「不超過上限」是安全方向（#34 裁定 2(a)） |
| 3 | AI 建議採用率（含修改後確認）≥ 70% | 可以 | `ai_feedback` 中 AI-01 候選回饋：（`accepted`＋`edited`）÷ 全部；改建新任務（`changed`）不進分子、仍在分母；`open` 沒有回饋，不計（#34 裁定 3(b)） |
| 4 | 我的日期調整，註記完成率 ≥ 80% | 可以 | mine、`delta_days≠0` 的 `due` 事件中，有效註記非空的比例。母體與有效註記直接用時間管理統計的查詢（`events_repo.mine_due_events_with_effective_mark`），兩處口徑一致 |
| 5 | 完成事件中，完成回報填寫率 ≥ 70% | 可以（Phase 9 前恆為 0） | 已完成任務中有 `completion_feedback` 的比例 |

## 各項的資料依據（2026-11-17 檢查）

- **衡量值 3**：main 上改 `candidates.state` 的地方只有 `inbox/confirm.py` 的 `_close`，四種處理分別記成：
  | 動作 | `state` | `ai_feedback.outcome` |
  | --- | --- | --- |
  | 確認（confirm）、釐清（clarify） | `confirmed` | `accepted`；延期候選改了日期時為 `edited` |
  | 建立新任務（create-task） | `confirmed` | `changed` |
  | 忽略 | `ignored` | `ignored` |

  每次處理都寫一筆 `ai_feedback`（`node_id='AI-01'`、`target_type='candidate'`），衡量值 3 依 #34 裁定改由這張表計算；`changed` 仍單獨記錄，可另外查看。
- **衡量值 4**：候選確認與整批順延產生的 `due` 事件都經 `write_event`，`mine`、`delta_days` 由伺服器計算，和手動改期同一個母體。
- **衡量值 5**：任務完成後不能改回未完成（`set_status` 與 `complete_task` 都擋 `TASK_DONE`；DA-08、DA-16），匯入也不會建立已完成的任務，所以「已完成任務」就等於「完成事件」，每個任務最多一筆完成回報（`completion_feedback.task_id` UNIQUE）。Phase 9（完成回報）還沒做，main 上沒有任何程式寫 `completion_feedback`，所以目前比率恆為 0。
- **todo 13.8 提到的 `jobs`**：五個衡量值都不需要它。`jobs` 只記收件背景工作的排隊與重試，和確認率、確認時間無關。`ai_feedback` 可以用在衡量值 3 的細分。

## 裁定結果（2026-11-17，#34，產品負責人）

1. **衡量值 1 採 A**：量 AI 初稿的 R4 對帳通過率，量的是 AI 編造不存在項目的頻率。人工版（`manual_text`）不經對帳，不納入。查詢與測試待 #23 合併後補。
2. **衡量值 2 採 (a)**：接受近似值，spec 1.3 已註明。近似值是上界，只會高估，不會漏掉真的超時。試用若發現誤報太多，再改做實際計時。
3. **衡量值 3 採 (b)**：定義為「AI 建議採用率」，量 AI 配對品質，不是收件匣吞吐率。改建新任務（`changed`）不算採用。

以上已寫回 spec 1.3 與 9.3。
