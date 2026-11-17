# 前端開發與 API 型別

在此目錄執行 `npm ci` 安裝鎖定的依賴。開發伺服器使用 `npm run dev`。

| 指令 | 用途 |
| --- | --- |
| `npm test` | 既有畫面行為測試與 OpenAPI 工具測試 |
| `npm run typecheck` | TypeScript 檢查，含請求型別的編譯期契約測試 |
| `npm run build` | 型別檢查與正式建置 |
| `npm run format:check` | 檢查前端尚未提交與已暫存變更的 Git 空白格式錯誤 |
| `npm run openapi:export` | 從後端匯出 UTF-8 OpenAPI 快照 |
| `npm run types:generate` | 從快照產生 TypeScript 型別 |
| `npm run types:check` | 不啟動後端，檢查生成型別是否符合快照，以及暫存回應清單 |
| `npm run openapi:check` | 再匯出後端至記憶體，比對快照並執行上述檢查；不覆寫檔案 |

`openapi:export` 與 `openapi:check` 使用 `backend/.venv` 的 Python。
先依 `backend/.python-version` 準備 Python，並在 `backend/` 執行 `uv sync --frozen`。
匯出不需要啟動 API 伺服器、不連線資料庫、不讀取正式 token。
匯出或 JSON 驗證失敗時，既有快照不會被覆寫。

API 變動後，依序執行：

```sh
npm run openapi:export
npm run types:generate
npm run openapi:check
npm test
npm run typecheck
```

提交 `openapi.json`、`src/api/types.generated.ts` 與必要的別名變更。
這兩個產物由指令產生，不手動編輯。型別工具只在 devDependencies。

請求型別從 `src/api/types.ts` 匯出，內容引用生成型別。
原本沒有獨立命名的功能頁請求物件保留原樣；本次不改 Dev-A 功能程式。

A4 已補齊全部成功回應模型。`src/api/types.ts` 的既有名稱改為生成型別別名；
`types.pending.ts` 只保留 `pending-response-count: 0`，沒有手寫回應型別。
零清單檢查會掃描全部成功回應；若出現空 schema，不能宣告零 pending。
`FromTo<T>`、`Paged<T>` 僅保留由生成模型欄位推導的相容泛型，不另定義資源欄位。

## 路由與共用版面（11.1）

`src/app/routeDefinitions.ts` 集中管理預留路由與導覽名稱；
`AppRoutes.tsx` 組合頁面，`AppLayout.tsx` 管理共用導覽與內容區。
寬度不超過 767px 時，底部導覽只顯示五個入口，依序為收件匣、今日、任務、目標、設定。
其餘入口只在首頁（工作總覽）提供連結，可點選頁首「個人大總管」返回首頁。
網站版頂部導覽維持完整，包含專案現況、歷程、匯入、統計、週報及資料控制等入口。
兩種版面使用相同 Outlet 與頁面元件，改變寬度不重建內容、不清除未送出的輸入。
版面樣式引用既有 CSS token，沒有新增主題或查詢快取規則。

| 路由 | 對應 todo／目前狀態 |
| --- | --- |
| `/` | 工作總覽與導覽入口 |
| `/projects`、`/projects/:projectId` | 12.1 預留 |
| `/tasks/:taskId` | 保留 Dev-A 12.2、12.5；12.3 後續在此整合正式任務詳情 |
| `/tasks` | 任務入口，預留 |
| `/projects/:projectId/bulk-shift` | 保留 Dev-A 12.4 |
| `/history`、`/projects/:projectId/history` | 12.6 預留 |
| `/import` | 12.7 匯入精靈 |
| `/inbox` | 12.8 收件匣與每日確認；首頁每日確認連結指向此處 |
| `/today`、`/tasks/:taskId/feedback` | 12.9 預留；此處未實作完成回報 |
| `/time-management` | 12.10 預留 |
| `/setup` | 12.11 首次啟用精靈；已啟用者由守門導回首頁 |
| `/settings` | 12.11 設定與量表 |
| `/goals` | 12.12 預留 |
| `/reports` | 12.13 週報：按週讀取、明確產稿、人工版保存與事件退路 |
| `/data-control` | 12.14 預留 |
| `/tasks/new` | 12.15 預留；靜態路由優先於任務編號 |
| 其他網址 | 找不到頁面，可返回工作總覽 |

預留頁面本身只顯示「此功能尚未開放」，不讀寫 API，也不代表該 todo 已實作。
App 根節點的 OnboardingGate 在 Router／QueryClient 內讀取共用 settings：未啟用導向 `/setup`，完成或略過後回首頁。
舊 `/confirmations` 預留頁已移除；每日確認就在 `/inbox`。
TokenGate 與 token 儲存、傳送邏輯沿用原有程式。

11.8 的 AI-07 回饋沿用生成的 commit 請求型別：首次 AI 預覽的 `ai_run_id` 保留至本輪保存，
使用者手動改對應、重新預覽後，commit 成對送原 id 與最終四欄索引 `column_map`。
改原文或目標、保存成功時清除 id；晚回的舊預覽不污染新一輪。沒有 AI id 時兩個回饋鍵均省略。
預覽的 `column_map` 只送四個索引，不含 `ai_run_id`／`mapped_by`；accepted／changed 由後端判斷。

## API client（11.2）

`src/api/client.ts` 提供通用 `api<T>`，成功時原樣回傳 JSON；HTTP 200、201 都是成功。
`MARK_IGNORED` 保留在成功回應的 warnings，屬警告，不拋錯。
沒有新增端點專用函式或手寫回應型別，也不驗證或推測業務回應欄位。

失敗時解析 `{error:{code,message,details}}` 並拋出既有 `ApiError`。
格式不符時沿用前端既有 `HTTP_ERROR` 備援，不新增伺服器錯誤碼；
code／message 必須是非空字串，details 必須是非陣列物件。
缺少有效訊息時使用 HTTP 狀態文字，再以 `HTTP <狀態碼>` 備援，不把 HTML 原文當作訊息。

`STALE_VERSION` 不自動重送。沿用既有功能頁的 onError 流程使相關查詢失效並重新讀取，
使用者確認最新資料後才能自行再次提交。整合測試驗證 GET 確實重新執行，
第二次 POST 必須由使用者操作觸發，且帶重新讀取的 expected_version。
本次未修改 QueryClient 設定、既有功能頁或其測試。

認證維持原樣：token 存在 `localStorage` 的 `g4.token`，以 `VITE_API_TOKEN` 作備援，
每次請求透過既有 `Authorization: Bearer …` header 傳送；沒有新增儲存或傳送管道。

`client.test.tsx` 對 spec 5.2 的 17 個錯誤碼逐一檢查錯誤解析、顯示與不自動重送。
其中 `INTERNAL_ERROR`（DA-19）**待產品負責人複核**；這些測試不代表已取得正式核可。

## TanStack Query 與快取失效（11.3）

查詢鍵只定義在 `src/api/queryKeys.ts`，舊 `queries.ts` 匯出與鍵值保留；
`makeQueryClient` 移至獨立檔案，保留禁重試、禁焦點重讀設定。
11.3 時 OpenAPI 有 22 個操作：7 個 GET（專案列表／詳情、任務列表／詳情、時間管理、原因、健康），15 個動作如下；其後 Dev-B（#20）新增的 13 個動作、Dev-A（#23）新增的 2 個週報動作接在表尾。

| 動作 | 失效查詢資源 | 依據 |
| --- | --- | --- |
| `POST /projects` | projects | FR-PRJ-01 |
| `PATCH /projects/{project_id}` | projects | FR-PRJ-02 |
| `POST /projects/{project_id}/archive` | projects | FR-PRJ-03 |
| `POST /projects/{project_id}/bulk-shift/preview` | 無 | FR-BLK-01，預覽不寫入 |
| `POST /projects/{project_id}/bulk-shift/commit` | tasks、timeManagement | FR-BLK-06、07；FR-MRK-06 |
| `POST /tasks` | tasks、projects | FR-TSK-01、02；ProjectDetailOut.task_count |
| `PATCH /tasks/{task_id}/owner` | tasks | FR-TSK-06，舊事件 mine 不變 |
| `POST /tasks/{task_id}/status` | tasks | FR-TSK-04、DA-08 |
| `POST /tasks/{task_id}/block` | tasks | FR-TSK-04、07 |
| `POST /tasks/{task_id}/adjust-start` | tasks | FR-TSK-09、AC-62，不進時間管理統計 |
| `POST /tasks/{task_id}/complete` | tasks、timeManagement | FR-TSK-04；FR-MRK-07 完成時精力分布 |
| `POST /tasks/{task_id}/adjust-due` | tasks、timeManagement | FR-DUE-02、04；FR-MRK-06 |
| `POST /tasks/{task_id}/baseline-correction/preview` | 無 | FR-BAS-03；DA-21 僅確認憑證，非正式查詢資料 |
| `POST /tasks/{task_id}/baseline-correction/commit` | tasks、projects | FR-BAS-06、07；ProjectDetailOut.baseline_saved_at |
| `POST /events/{event_id}/annotations` | tasks、timeManagement | FR-MRK-04–06，任務詳情含 events |
| `POST /projects/import/preview` | 無 | FR-IMP-01，預覽不寫入 |
| `POST /projects/import/commit` | projects、tasks | FR-IMP-06、07，建立專案與任務 |
| `POST /ingest` | candidates | FR-INB-01、05，只新增候選 |
| `POST /candidates/{candidate_id}/confirm` | candidates、tasks、timeManagement、projects | FR-INB-09–12；ProjectDetailOut.open_candidates |
| `POST /candidates/{candidate_id}/clarify` | candidates、tasks、timeManagement、projects | FR-INB-13（12.8 四個動作共用同一套失效） |
| `POST /candidates/{candidate_id}/create-task` | candidates、tasks、timeManagement、projects | FR-INB-14 |
| `POST /candidates/{candidate_id}/ignore` | candidates、tasks、timeManagement、projects | FR-INB-09、13、14 |
| `PUT /settings` | settings | FR-SET-02、03 |
| `POST /settings/onboarding/complete` | settings | FR-SET-01，啟用精靈完成 |
| `POST /rubrics/interview` | 無 | FR-RUB-02、03，只回草稿 |
| `POST /rubrics` | rubrics | FR-RUB-03，確認後成立新版本 |
| `POST /sources/purge` | candidates、tasks | FR-GOV-03；候選與任務歷程的原句由 `sources.excerpt` 帶出，清除後變空 |
| `POST /export` | 無 | FR-GOV-02，只讀 |
| `POST /reports/weekly/draft` | weeklyReports | FR-RPT-02、03；本次回應先替換快取，其他週報鍵標 stale 不立即重讀，保留 H2 降級提示 |
| `PUT /reports/weekly/{report_id}/manual` | weeklyReports | FR-RPT-04；人工版保存後更新對應週與 id 快取 |

資源前綴涵蓋全部列表、詳情及篩選查詢。原因、健康不受上述寫入影響。
`runMutationWithInvalidation` 只在成功後失效，等待使用中的查詢重讀，未使用的查詢留待下次讀取。
失敗原樣交回呼叫者，不重送；STALE_VERSION 沿用既有頁面重讀流程。
此共用包裝供後續頁面使用，未改動 Dev-A 功能頁既有的 onSuccess／onError 行為。
`queryCache.test.ts` 對照 OpenAPI 與本表，逐動作驗證失效、重讀及失敗不重送。

自行決定：以資源前綴失效，沿用既有 tasks 前綴慣例。
後端目前完成操作尚未寫精力回報；complete 保留 FR-MRK-07 所需統計失效，避免後續讀到舊統計。

### 專案查詢失效核對（Dev-A 77e3e02）

`status`、`block`、`complete`、`bulk-shift/commit` 對 `projects` 查詢：**已核對，無需失效**。
此結論只適用目前回應欄位，沒有省略任務與時間管理查詢原有的失效規則。

- `backend/app/api/responses.py`：`ProjectOut` 只有 id、name、scope、audience、line_group_id、created_at、updated_at、archived_at，沒有任務進度、完成數或到期日彙總；`ProjectListOut.items` 使用此模型。
- `backend/app/api/routes_projects.py`：列表路由使用 `ProjectListOut`，由 `projects_repo.list_all` 取得專案資料，再經 `project_out` 序列化；`backend/app/db/repo/projects_repo.py` 的列表只查 projects，沒有任務彙總或 join。
- 詳情的 `ProjectDetailOut` 另有 `task_count`、`baseline_saved_at`。依 `backend/app/domain/projects.py` 與 repo 查詢，前者是全部任務數、後者只取 kind=baseline 事件的最新 ts；上述四個動作不增減任務數，也不寫 baseline 事件。
- 任務更新改的是 tasks 的 updated_at；專案 updated_at 由 projects_repo.update 在編輯／封存專案時更新，不是任務活動日期彙總。依據為 projects_repo、tasks_repo 與 domain/projects.py。

建立任務仍使 projects 失效（task_count），基準更正 commit 仍使 projects 失效（baseline_saved_at）。
既有 `queryCache.test.ts` 對這四個動作各有行為測試，同時驗證專案列表與詳情保持有效，並核對 README 與實作一致。
此項是後端模型／路由／查詢的唯讀核對與文件補充，未修改失效實作、後端或 Dev-A 的功能程式／測試。
未啟動資料庫驗證實際專案 HTTP 回應；若後續模型或路由加入進度／日期彙總，需重新檢查本結論。

## MSW 共用資料集（11.7）

測試仍從 `src/test/server.tsx` 匯入 `API`、`server`、`reasons`、`makeTask`、`apiError`、
`renderWithClient`；既有名稱、原因選項順序與 makeTask 覆寫方式保留；A4 後補齊 TaskOut 的 19 欄。
資料單一來源分工：`reasons.ts` 放選項、`fixtures.ts` 放任務與情境快照、
`errorFixtures.ts` 放 spec 5.2 全部 17 個錯誤碼／HTTP 狀態、`handlers.ts` 放 MSW handlers。
Dev-A 測試原有的局部 handler 覆寫保留，沒有刪除或放寬測試。

| 情境 | 依據 | 對應行為測試 |
| --- | --- | --- |
| 全部 17 種錯誤回應 | spec 5.1、5.2 | `spec 5.2 的全部 17 個錯誤碼與狀態集中在單一資料集`；`MSW 錯誤情境 <code> 回傳統一格式`，每碼一項 |
| `INTERNAL_ERROR` 待複核 | DA-19 | 資料集完整性測試另檢查複核標記 |
| todo／doing 狀態切換 | FR-TSK-04、DA-08 | `DA-08 狀態 <status> 使用生成請求型別與完整序列化回應` |
| status 回應欄位全集 | `serialize.py`、`routes_tasks.py` | `status 的 task／event 欄位全集對照後端 serialize.py，不依殘缺產品型別猜欄位` |
| `MARK_IGNORED` 是成功警告 | FR-MRK-02、DA-11 | `DA-11 MARK_IGNORED 仍為 200 警告，不寫入我的註記` |
| 調整開始日成功快照 | FR-TSK-09、AC-62 | `AC-62 adjust-start 成功快照引用正式 AdjustStartOut 的 start 欄位` |
| 開始日晚於預計日仍成功 | AC-62 | `AC-62 START_AFTER_DUE 是 200 警告，不阻擋開始日調整` |
| 開始日調整的 5 種錯誤 | 已核准的 adjust-start 契約 | `adjust-start 錯誤情境 <scenario> 沿用既有錯誤碼` |
| 選項、舊 factory 與隔離 | FR-DUE-05、FR-MRK-03、既有介面相容要求 | `makeTask 與原因選項相容，測試資料可獨立修改而不污染後續情境` |
| 測試手寫形狀不得流入產品 | 本次核准的測試型別邊界 | `產品程式不得引用 src/test 的手寫形狀或 fixture` |

預設 handlers 提供原因選項、任務列表、任務 4 詳情、日期調整、任務 4 狀態切換、
任務 3 開始日調整。使用 `server.use(statusHandler("todo"))`、
`server.use(markIgnoredHandler())`、`server.use(adjustStartHandler("afterDue"))` 切換情境。
全部為固定範例快照，不驗證請求、不持久化狀態、不模擬交易，也不代算伺服器欄位。
錯誤 handler 只驗證統一錯誤格式，不代表測試端點在產品中會回全部錯誤碼；
例如 spec 5.2 的 503 `AI_UNAVAILABLE` 仍僅限量表訪談。

`src/test/fixtureTypes.ts` 全部引用 `types.generated.ts`，只保留測試相容別名，不再手寫形狀：

| 測試別名 | 生成模型／來源 |
| --- | --- |
| `SerializedTaskFixture` | `components.schemas.TaskOut`（19 欄） |
| `SerializedEventFixture` | `components.schemas.EventOut`（21 欄） |
| `StatusFixtureResponse` | `components.schemas.TaskEventOut`；請求使用 `StatusChange` |
| `TaskDetailFixtureResponse` | `components.schemas.TaskDetailOut`，包含 `task`、`events`；空陣列表示範例沒有近期歷程 |
| `AdjustStartFixtureRequest` | `components.schemas.AdjustStart` |
| `AdjustStartFixtureResponse` | `components.schemas.AdjustStartOut`；使用正式的 `task.start` |

0-8b 已移除所有手寫回應介面與舊的待實作標記。
正式 adjust-start 依 `responses.py` 使用 `TaskOut.start`；事件欄位仍為 `field="start_date"`。
既有 API、server、原因選項與 helper 匯出保留，Dev-A 功能／測試不需改動。
本資料集沒有新增建立任務端點 fixture，也不代替後端 AC-61／62 的交易與資料庫驗收。

## 主題（11.4）

亮暗色沿用原型 V4，保留既有 CSS token 名稱；元件只引用變數。未新增外部字型連線，Noto Sans TC 未安裝時使用系統繁中文字型。
預設跟隨 prefers-color-scheme，頁首可手動切換亮色／暗色，再切回跟隨系統。
主題偏好只存 `g4.theme`，讀寫均以 try/catch 保護，保存失敗仍可切換；token 的儲存與傳送未改。
需求測試：`Theme.test.tsx` 驗證系統預設、手動保存與重掛載、無效值、儲存失敗及 token 不受影響。
自行決定清單：主題儲存鍵 `g4.theme`（派工允許 localStorage，鍵名無依據，待裁定）；控制項置於共用頁首（無依據，待裁定）；「色彩主題／跟隨系統／亮色／暗色」為中性標籤（無逐字文案依據，待裁定）。
對比自行決定：亮色成功文字由 V4 的 #1c7c4a 加深為 #1b7b49，避免原型 4.49:1 低於本次 4.5:1 檢查門檻；色值非原型原值，待裁定。其餘色值沿用 V4。
瀏覽器驗證：Microsoft Edge 157，1280／768／390／320，各亮暗色均無頁面水平溢位；手機五入口順序保留。系統切換、手動覆寫與重新載入保存均通過；量測的 8 組文字色配對最低對比亮色 4.55:1、暗色 6.48:1。一般連結亦引用 accent token。

## 共用元件（11.5）

| 元件 | 依據 | 行為測試（shared.test.tsx） |
| --- | --- | --- |
| DatePicker | spec 5.1 日期格式、V4 原生日期選擇 | 日期選擇不預填，送出 YYYY-MM-DD 原字串，不轉時區 |
| ConfirmationPanel | FR-BLK-01、FR-BAS-03；V4 確認面板 | 呼叫者明確允許才可確認，取消不觸發確認 |
| MarkChoice | FR-MRK-01～03、AC-12；V4 註記面板 | 四選項不預選、各註記只能由使用者選擇、稍後註記 payload |
| ReasonSelect | FR-DUE-05、FR-MRK-03 | 不預選、方向篩選、外部原因只提示不代選 |
| ErrorBanner | spec 5.2、既有 11.2 訊息行為 | 空錯誤不顯示、STALE_VERSION 舊訊息、未知錯誤安全退路；client.test.tsx 保留 17 碼測試 |

三個 standin 的實作提升至 components/，舊路徑、props、helper 匯出均保留。
舊 ReasonSelect 入口保留由 MarkChoice 顯示外部提示的方式，避免 Dev-A 頁面重複提示；
正式 ReasonSelect 自行顯示外部提示，搭配 MarkChoice 時不用另設 externalHint。
外部提示文案只有 ExternalReasonHint 一處。原因仍使用 { code, label, direction, external }，不新增選項或改順序。
ConfirmationPanel 不代算商業規則；呼叫端以 canConfirm 明確授權。日期選擇不預填今日，日期限制由呼叫端提供。
沒有刪除入口、功能、測試；沒有改動 src/features/。BulkShiftPage 的預設勾選是其自身狀態，共用元件不介入。
自行決定清單：日期控制項旁另顯示原始 YYYY-MM-DD（格式有規格依據，並列位置無依據，待裁定）；確認面板以既有 card 樣式呈現、取消在確認之前（V4 模式），不自行加入對話框或確認規則。
瀏覽器驗證：Edge 157，1280／768／390／320，亮暗色各一次，共用元件無水平溢位；320px「稍後註記」自然換到下一行。以共用 fixture 攔截 API 載入實際 BulkShiftPage，未完成任務預設勾選、已完成任務排除、原因保持空白；320px 表格文字與日期會折行（既有版面）。未執行真實後端寫入。

## AI 降級顯示（11.6）

| 需求與依據 | 元件／行為測試 |
| --- | --- |
| spec 5.3、AC-50：ok 顯示正常內容 | AIFallback；ok 顯示既有內容，不顯示降級提示與退路 |
| spec 5.3：unavailable／invalid_output 仍為 200 退路 | AIFallback；每個狀態各一測試，顯示 status 提示與呼叫者的退路，不渲染錯誤橫幅、不自動觸發操作 |
| spec 5.4、6.6：僅量表訪談 503 AI_UNAVAILABLE 保留目前版本 | RubricInterviewFallback；目前版本與未送出輸入保留，不重新掛載 |
| spec 5.2：其他錯誤仍依通用錯誤處理 | 500 AI_UNAVAILABLE、503 HTTP_ERROR 各一測試，不誤用量表降級提示 |

元件只呈現呼叫者提供的內容，不定義 API 回應形狀、不新增端點函式、不生成或修改量表／退路資料。
產品頁整合仍屬後續 todo；未替未實作的 AI 端點建立手寫型別。
一般 AI 呼叫成功降級使用 role=status；量表訪談的 503 是例外錯誤，使用 role=alert。
自行決定清單（無逐字規格文案依據，待裁定）：
- unavailable：「AI 暫時無法使用，以下顯示可用內容。」
- invalid_output：「AI 回傳內容未通過檢查，以下顯示可用內容。」
- 訪談 503：「AI 訪談暫時無法使用，目前量表版本維持不變。」
提示使用既有 banner-warn 樣式；語意依 spec 5.3／5.4，未新增畫面或入口。
瀏覽器驗證：Edge 157，1280／768／390／320，亮暗色各一次；正常內容、兩種成功降級提示與退路、量表訪談 503 提示及目前版本均可見，未送出輸入保留，無水平溢位。320px 提示與欄位標籤自然折行。這是元件驗證頁，未呼叫真實 AI／後端端點。
