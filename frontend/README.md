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

回應模型尚未齊全，既有手寫定義原樣集中至 `src/api/types.pending.ts`。
該檔的 `pending-response` 註解逐一列出使用這些型別的端點，也是檢查程式讀取的清單。
若清單內任一端點的任一 2xx 回應 schema 不再是空物件，檢查會失敗：
待 Dev-A 補齊契約後，應在後續作業移除對應暫存型別與清單項目，改用生成型別。
請勿自行補齊、擴充或推測回應欄位。

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
| `/import` | 12.7 預留 |
| `/inbox`、`/confirmations` | 12.8 預留 |
| `/today`、`/tasks/:taskId/feedback` | 12.9 預留；此處未實作完成回報 |
| `/time-management` | 12.10 預留 |
| `/setup`、`/settings` | 12.11 預留 |
| `/goals` | 12.12 預留 |
| `/reports` | 12.13 預留 |
| `/data-control` | 12.14 預留 |
| `/tasks/new` | 12.15 預留；靜態路由優先於任務編號 |
| 其他網址 | 找不到頁面，可返回工作總覽 |

預留頁面只顯示「此功能尚未開放」，不讀寫 API，也不代表該 todo 已實作。
TokenGate 與 token 儲存、傳送邏輯沿用原有程式。

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

## MSW 共用資料集（11.7）

測試仍從 `src/test/server.tsx` 匯入 `API`、`server`、`reasons`、`makeTask`、`apiError`、
`renderWithClient`；既有名稱、原因選項順序、makeTask 的 13 欄與覆寫方式均保留。
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
| 調整開始日成功快照 | FR-TSK-08、AC-62 | `AC-62 adjust-start 成功快照只改開始日與版本，標示待 Dev-A 實作` |
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

手寫形狀僅在 `src/test/fixtureTypes.ts`，不從 `src/api/` 匯出、不供產品程式引用：

| 手寫形狀 | 來源與邊界 |
| --- | --- |
| `SerializedTaskFixture` | `task_out` 的 19 欄；只在測試擴充原有 Task，不改產品型別 |
| `SerializedEventFixture` | `event_out` 的 21 欄；時間戳使用固定 `+08:00` 字串 |
| `StatusFixtureResponse` | 狀態路由的 `{task,event}`；請求引用生成的 `StatusChange` |
| `AdjustStartFixtureRequest` | 已核准的 `new_start`、`expected_version`、選填 `note` |
| `AdjustStartFixtureResponse` | 已核准成功輸出與 AC-62 的空 mark／delta_days；不補猜測欄位 |

status 形狀標記「形狀取自後端現況，待 Dev-A 補 response_model 後改由生成型別取代」。
adjust-start 的形狀、資料與 handler 均標記「待 Dev-A 實作（todo 2.11）」。
它依已核准的規劃契約使用 `start_date`；現行 task_out 的 `start` 保持原樣，兩者不自行統一。
未擴充其他 12 個空 schema 端點，也未新增 AC-61 的建立任務端點 fixture。
測試型別的補充與固定情境組織方式屬本次授權內的測試實作選擇，不代表產品契約已補齊。
