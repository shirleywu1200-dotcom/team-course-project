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
