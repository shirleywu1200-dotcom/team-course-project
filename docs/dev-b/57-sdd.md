# #57 SDD：自動帶入的候選專案已封存時，不帶專案並回警告

依據：#44 產品負責人裁定 A（2026-11-18 00:01）；#57 Dev-A 開票（改法、三個測試情境、審查由 Dev-A）。
狀態：**Mora 已同意（2026-11-18），Q1、Q2 皆照建議**。分支 `dev-b/57-archived-project`。

## 現況

`POST /candidates/{id}/create-task`：沒送 `project_id` 時，`confirm.create_task_from` 沿用 `candidates.project_id`（B5，PR #41）。這個專案在收件後才被封存的話，任務會建在封存專案底下，不會進週報「下週重點」（G5），專案列表預設也看不到。

## 改法

### 57-1 判斷只放在自動帶入的路徑

`confirm.py` 的 `project_id is _FROM_CANDIDATE` 分支：`cand["project_id"]` 不為 NULL 時，讀 `projects_repo.get`；`archived_at IS NOT NULL` → `project_id = None`，並加一則警告。

- 明確送了 `project_id`（含已封存的 id、含 null）：照舊，不檢查、不警告。
- 架構後果：(a) 只多一次依主鍵的讀取，而且只在候選帶有專案時才讀 (b) `tasks.create_task` 不用改：它本來就不擋封存專案，裁定也要求明確指定時照舊 (c) 不新增錯誤碼，也不動 DDL

### 57-2 警告用代碼 `PROJECT_ARCHIVED`，文案由前端負責（Q1，已同意）

既有的 `warnings` 都是 `list[str]` 代碼（`BEFORE_START`、`MARK_IGNORED`、`START_AFTER_DUE`），前端再把代碼對應成中文。#57 寫的是「沿用既有 `warnings` 形狀」，但 #44 也要求「文案明確寫出原專案已封存，任務已建為無專案」，兩者要靠「代碼＋前端文案」才能同時做到。

- 後端回 `warnings: ["PROJECT_ARCHIVED"]`；前端顯示「原專案已封存，任務已建為無專案」。
- 架構後果：(a) 回應形狀不變（`DecideOut.warnings` 本來就是 `list[str] | None`），型別不用重新產生 (b) 文案只放在前端一處，日後改字不必動後端 (c) 中文句子不會放進 API 回應，和其他警告一致

### 57-3 建任務的回應一律帶 `warnings`

`create_task_from` 一律回傳 `warnings`（沒有警告時為 `[]`），和確認延期一致。`DecideOut.warnings` 的說明從「確認延期時才出現」改為「確認延期、建任務時出現」，並列出 `PROJECT_ARCHIVED`。

- 架構後果：OpenAPI 只改了說明文字，型別沒變；Dev-C 的 MSW 測試不受影響（欄位本來就是選填）。

### 57-4 前端：收件匣「已處理」區顯示警告（Q2，已同意）

`CandidateCard`／`InboxPage` 屬於 12.8，是 Dev-B 自己的頁面。#57 只列了後端，但沒有畫面的話，使用者看不到警告，PO 要求「讓使用者知道」就沒有做到。

- 做法：「已處理」區的該筆結果下方加一行警告文字（沿用既有的警告樣式，不新增 token），代碼不認得時不顯示。
- 測試：MSW 回 `warnings: ["PROJECT_ARCHIVED"]` → 看得到文案；回 `[]` → 看不到。

### 57-5 spec 寫回（第一個 commit，只改文件）

- FR-INB-14 補一句：「自動帶入的專案已封存時，任務建成無專案，回應 `warnings` 含 `PROJECT_ARCHIVED`；明確指定專案時照舊（#44）。」
- 5.11 第 987 行 `create-task` 的輸入說明後，補輸出 `warnings` 與 `PROJECT_ARCHIVED`。

## 測試（先寫、先紅）

後端 `tests/unit/test_phase7_inbox.py`，依 #57 的三個情境，加上一個邊界：

1. 自動帶入，專案已封存 → 任務 `project_id` 為 NULL，`warnings == ["PROJECT_ARCHIVED"]`。
2. 明確送了已封存的專案 id → 任務建在該專案，`warnings == []`。
3. 自動帶入，專案未封存 → 照舊帶入，`warnings == []`（既有 `test_b5_create_task_without_project_uses_candidate_project` 補斷言，不改原本的斷言）。
4. 候選本來就沒有專案 → 任務無專案，`warnings == []`（不能誤報）。

種子：在既有的 `BASE + CANDIDATES` 加上 `UPDATE projects SET archived_at = ... WHERE id = 2;`，不改夾具庫。

## 不做

- 不擋明確指定的封存專案（裁定照舊）。
- 不新增錯誤碼、不改 DDL。
- 不碰 `clarify`、`confirm`：它們處理的是既有任務，不建任務，也就沒有帶入專案這件事。

## 完成條件

spec 寫回、四個測試綠、後端與前端全套測試、ruff、tsc 通過 → code-review → 開 PR（Dev-A 審）→ 合併後關閉 #57，並在 #44 留言請 PO 關閉。
