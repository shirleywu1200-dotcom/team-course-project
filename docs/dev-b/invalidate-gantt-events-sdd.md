# Dev-B 元件補齊 gantt／events 失效 SDD

狀態：Mora 已同意（2026-11-18，Q1 含 tasks）
分支：`dev-b/invalidate-gantt-events`（從 origin/main 27f90b4 切）
緣由：審 PR #55 時承諾「失效表中 Dev-B 端點新增的 gantt、events，Dev-B 元件目前沒失效，會另外處理」。

## 1. 依據

- 對照基準：`frontend/src/api/queryCache.ts` 的 `mutationInvalidations`（Dev-C 共用層，本案**不改**）。
- 寫法範本：`TaskDetailPage.tsx:45-46` 改期成功後 `void qc.invalidateQueries({ queryKey: queryRoots.events })`、`queryRoots.gantt`。
- 驗收場景：12.1 專案現況（#66，讀 `keys.gantt(projectId)`）、12.6 專案歷程（#65，讀 `keys.events(filters)`）。兩者的 key 都以 `queryRoots.gantt`／`queryRoots.events` 開頭，以根失效就能涵蓋。

## 2. 現況差異

| 端點 | 呼叫處 | 登記表 | 現在失效 | 缺 |
|---|---|---|---|---|
| `POST /candidates/{id}/confirm\|clarify\|create-task\|ignore` | `inbox/CandidateCard.tsx:34-40` onSuccess | candidates, tasks, timeManagement, projects, gantt, events | candidates, tasks, timeManagement, projects | **gantt, events** |
| `POST /ingest`（同步） | `inbox/PasteBox.tsx:47-55` onSuccess | candidates, gantt | candidates | **gantt** |
| `POST /ingest`（非同步，job 完成） | `inbox/PasteBox.tsx:72-74` effect | 同上 | candidates | **gantt** |
| `POST /projects/import/commit` | `import/ImportPage.tsx:61-68` onSuccess | projects, tasks, gantt, events | projects, tasks | **gantt, events** |
| `POST /sources/purge` | `data-control/DataControlPage.tsx` `clearSourceCaches` | candidates, tasks, events | candidates、events 用 cancel→remove→refetch（比失效更強） | **tasks** |

`purge` 要失效 tasks 的原因：`TaskDetailOut` 帶 `events`（含來源原文），存在 `keys.task(id)`＝`["tasks", id]` 底下；只清 `["events"]` 的話，任務詳情頁仍會留著舊原文。

## 3. 設計

只改 Dev-B 自己的四個檔，每處只**加**失效呼叫，不改既有行為：

1. **CandidateCard**：onSuccess 的迴圈陣列補上 `queryRoots.gantt`、`queryRoots.events`。
2. **PasteBox**：同步成功、非同步 job 完成這兩處，都在失效 candidates 之後再失效 `queryRoots.gantt`（job 完成才代表候選寫入，跟 candidates 同一時機）。
3. **ImportPage**：commit onSuccess 補 `queryRoots.gantt`、`queryRoots.events`。onError 那一行（非預期錯誤時重讀 projects）**不動**：登記表只規範成功後的失效。
4. **DataControlPage**：只在 `PurgeSection` 的 onSuccess，`clearSourceCaches` 之後補失效 `queryRoots.tasks`。`clearSourceCaches` 本身不動，因為保存期限縮短（`PUT /settings`）也會呼叫它，那條不在本案範圍。

不採用 `runMutationWithInvalidation`：它會把失效綁在 mutationFn 內，PasteBox 非同步路徑、purge 的 remove 語意都跟它不合；改寫屬於重構，超出本案範圍。

## 4. 測試（先紅後綠）

照 `InboxPage.test.tsx:312` 的寫法：`vi.spyOn(client, "invalidateQueries")` 收集 queryKey，斷言含指定的根。

| 測試檔 | 新增測試 | 斷言 |
|---|---|---|
| `InboxPage.test.tsx` | 確認候選後一併失效甘特與歷程 | 含 `["gantt"]`、`["events"]` |
| `InboxPage.test.tsx` | 同步貼上解析後失效甘特 | 含 `["gantt"]` |
| `InboxPage.test.tsx` | 非同步解析完成後失效甘特 | job 完成後含 `["gantt"]` |
| `ImportPage.test.tsx` | 匯入成功後失效甘特與歷程 | 含 `["gantt"]`、`["events"]` |
| `DataControlPage.test.tsx` | 刪除來源原文後失效任務 | 含 `["tasks"]` |

既有測試不改。如果有既有測試因此變紅，就停下來回報，不去遷就它。

## 5. 驗收

- 上表新測試先紅，改完後轉綠。
- 前端全套 vitest 綠、`tsc -b` 綠（Node 26 要設 `NODE_OPTIONS=--localstorage-file=$TEMP/vitest-ls.json`）。
- 本機 commit。推送、開 PR（由 Dev-A 審）要等 Mora 明確同意。

## 6. 待 Mora 決定

- **Q1** purge 補失效 tasks：建議做（理由見第 2 節）。不做的話，本案就只補 gantt／events。
