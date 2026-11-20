# 部署文件（todo 13.7）

適用範圍：單機、單一使用者（spec 8.2）。後端行程、靜態前端、PostgreSQL 都在同一台機器上，預設只綁 `127.0.0.1`。

## 1. 需要的軟體

| 軟體 | 版本 | 用途 |
| --- | --- | --- |
| PostgreSQL | 15 以上（開發用 17） | 資料庫 |
| Python | 3.12（用 uv 管理） | 後端 |
| Node.js | 22（CI 版本）；24 也可 | 建置前端、跑前端測試 |
| gitleaks | 最新版 | pre-commit 掃描祕密 |

Node.js 26 跑前端測試時，jsdom 的 `localStorage` 會是 undefined，有 33 個測試失敗（2026-11-17 實測；Node 24 全過）。建置與執行不受影響，但跑測試請用 22 或 24。

## 2. 環境變數

全部放在 `env/local.env`（不進版控）。範例見 `env/example.env`。

| 變數 | 必填 | 說明 |
| --- | --- | --- |
| `G4_DATABASE_URL` | 是 | `postgresql+psycopg://帳號:密碼@127.0.0.1:5432/g4` |
| `G4_API_TOKEN` | 是 | API 的 Bearer token；空值時所有 API 回 401 |
| `G4_BIND_HOST` | 否 | 預設 `127.0.0.1`。改成其他值之前，先完成第 7 節的條件 |
| `G4_PORT` | 否 | 預設 `8000` |
| `G4_TEST_ADMIN_URL` | 只有跑測試時需要 | 可建立與刪除資料庫的帳號，連到 `postgres` 資料庫 |
| `G4_PG_DUMP_CMD` | 否 | 備份指令；未設定時用 `pg_dump --format=custom --dbname=…` |
| `VITE_API_TOKEN` | 否 | 只在前端開發時使用；正式建置不要設定，改在畫面上輸入 token |
| `G4_ENV_FILE` | 否 | 改讀其他路徑的環境檔；預設 `env/local.env` |
| `AI_PROVIDER` | 否 | `off`（預設）或 `anthropic`。不是 `anthropic` 時所有 AI 功能走退路，不呼叫供應商、不產生費用 |
| `AI_MODEL` | 否 | 預設 `claude-sonnet-5-5`（13.4 評估定案）；換模型只改這裡 |
| `ANTHROPIC_API_KEY` | `AI_PROVIDER=anthropic` 時需要 | **只放 `env/local.env`**，不放 `env/example.env`、不進 git |

產生 token：`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

載入規則：後端啟動時讀環境檔，但不覆蓋已存在的環境變數，所以 shell 裡設的值優先。

原文保存天數、每日確認時間等使用者設定存在資料庫的 `settings` 表，在畫面上調整，不用環境變數。

AI 供應商（todo 13.4，`docs/dev-b/13-4-sdd.md` D-2～D-4）：
- 預設關閉。要開時在 `env/local.env` 設 `AI_PROVIDER=anthropic` 與 `ANTHROPIC_API_KEY`，重啟後端。
- 設成 `anthropic` 但沒有 key 或 key 無效時，後端照常啟動，AI 呼叫一律視為不可用、走退路（FR-AI-03）。
- 會把收件摘錄、任務清單等送往供應商（私人範圍在送出前排除）。正式使用前，先確認 spec 8.2「供應商資料處理條件須在上線前確認」〔待決〕已定案【待複核：法規解讀】。
- 要停用（例如 13.3 演練、key 外流時）：改回 `AI_PROVIDER=off` 或拿掉 key，重啟後端。key 外流時同時到供應商主控台撤銷該 key。

## 3. 第一次安裝

```bash
# 資料庫（以 Docker 為例；只綁本機）
docker run -d --name g4-pg -p 127.0.0.1:5433:5432 \
  -e POSTGRES_USER=g4 -e POSTGRES_PASSWORD=<密碼> -e POSTGRES_DB=g4 -e TZ=Asia/Taipei postgres:17

cp env/example.env env/local.env      # 填入實際值；連接埠要與上面 -p 的本機埠一致
```

範例的本機連接埠是 `5433`。綁不上時（例如被其他 PostgreSQL 或系統保留範圍占用），換一個沒被占用的值，並同步改 `env/local.env` 裡兩個連線字串的連接埠。

- Windows 會保留一段動態連接埠範圍，各台電腦不同。查詢保留範圍：`netsh interface ipv4 show excludedportrange protocol=tcp`
- Mac／Linux 查詢是否被占用：`lsof -iTCP:5433 -sTCP:LISTEN`

```bash
cd backend
uv sync
uv run alembic upgrade head        # 建立資料表與 events 只增觸發器
uv run pytest                      # 確認環境正常

cd ../frontend
npm ci
npm run build                         # 產出 frontend/dist
```

## 4. 啟動

```bash
cd backend && uv run python -m app.main      # 只綁 G4_BIND_HOST:G4_PORT
```

前端靜態檔 `frontend/dist` 交給本機的靜態伺服器（或反向代理），並把 `/api` 轉給後端。開發時用 `npm run dev`，Vite 會自動代理 `/api`。

`app.main` 在同一個行程裡啟動三樣東西：

| 元件 | 做什麼 | 啟動時 |
| --- | --- | --- |
| API（uvicorn） | 所有 `/api/v1` 端點 | — |
| 收件背景工作（todo 7.5） | 處理 `jobs` 表裡排隊的收件工作 | 先把上次停在 `running` 的工作重設為 `queued`，再開始處理 |
| 原文清除排程（todo 8.5） | 清除保存期限已過的原文 | 先跑一次，之後每小時一次；冪等，關機漏跑的部分下次會補上 |

- **只啟動一個後端行程**（spec 8.2）。不要用多個 worker 或多個行程啟動，背景工作與排程沒有設計成多行程並行。
- **`AI_PROVIDER` 不是 `anthropic` 時，AI 一律視為不可用**：收件、週報等 AI 功能走退路，其餘功能照常（AC-50）。這是預期行為，不是故障。開了 `anthropic` 仍走退路時，先查 key 是否正確、供應商是否可連線；AI 用戶端的 log 只記節點、HTTP 狀態碼或「連線失敗或逾時」、停止原因與 token 數，不記內容（`ai/anthropic_client.py`）。

## 5. 更新版本

以下指令都從 repo 根目錄開始：

```bash
(cd backend && uv run python -m app.db.backup /path/to/backups)   # 先備份（見第 6 節）
git pull
(cd backend && uv sync && uv run alembic upgrade head)            # 套用新遷移
(cd frontend && npm ci && npm run build)
# 停掉舊的後端行程，再照第 4 節啟動
```

- Schema 只經 Alembic 遷移變更，而且只新增遷移（CLAUDE.md）。`alembic upgrade head` 可重複執行，已套用的遷移會略過。
- 確認目前版本：`uv run alembic current`。
- 遷移失敗時不要手動改資料表，用更新前的備份還原（第 6 節），再回報錯誤。

## 6. 備份與還原

- 每日備份（spec 8.2：保留 14 份）：
  ```bash
  cd backend && uv run python -m app.db.backup /path/to/backups
  ```
  可用 cron 或 launchd 每天執行一次。Docker 環境可設 `G4_PG_DUMP_CMD="docker exec g4-pg pg_dump -U g4 --format=custom g4"`。
- 還原（會覆蓋目標資料庫，先確認目標）：
  ```bash
  pg_restore --clean --if-exists --dbname=<目標資料庫> /path/to/backups/g4-YYYYMMDD-HHMMSS.dump
  ```
- 還原演練（todo 13.6）由 QC-1 主導，Dev-A 支援。

## 7. 對外開放前的條件（spec 8.2）

預設只綁 `127.0.0.1`。要讓其他裝置（例如手機）連線之前，下列三項都要完成：

1. **TLS**：由反向代理終結 TLS（例如 Caddy 或 nginx），後端仍只綁本機，只由代理轉入。沒有 TLS 時，Bearer token 和所有資料都以明文經過網路。
2. **token 輪替**：見第 8 節，並把輪替週期寫進維運紀錄。
3. **限制來源**：反向代理只允許必要的來源（例如家用網段或 VPN），不直接暴露在公網。

## 8. token 輪替

1. 產生新 token，寫入 `env/local.env` 的 `G4_API_TOKEN`。
2. 重新啟動後端；舊 token 立即失效。
3. 在前端畫面重新輸入 token。token 存在各瀏覽器的 `localStorage`，每台用過的裝置都要重新輸入一次。

目前一次只接受一個 token，輪替時會短暫中斷，單一使用者情境可接受。

除了定期輪替，懷疑 token 外流時（例如裝置遺失、token 被貼進聊天或文件）也要立刻輪替。

## 9. 日誌

- 後端日誌只記錯誤類型與 ID，不記文件內容、摘錄原文或 token（CLAUDE.md 資安 3）。
- 未預期的例外只記錄類型名稱，不留 traceback；資料庫例外訊息也不帶 SQL 參數值（DA-25）。除錯時請在本機用測試重現。
- API 文件：`/docs`、`/redoc` 已關閉；OpenAPI 在 `/api/v1/openapi.json`，需要 token（DA-24）。
- 不接任何第三方遙測或錯誤回報服務（CLAUDE.md 資安 2）。FastAPI 內建的 OpenTelemetry 已在 `create_app` 全部關閉；不要安裝 `opentelemetry-sdk` 或任何 exporter。
- 不要開 SDK 的除錯 log：`ANTHROPIC_LOG=debug`，或把 `anthropic`、`httpx` 的 logger 調到 DEBUG，會把送出的內容、回應原文或 API key 寫進 log。

## 10. 例外演練（todo 13.5，Dev-A；#98）

`cd backend && .venv/bin/python ../scripts/drills/exception_drill.py`：以真實行程（`app.main.run`，含背景工作）對暫時資料庫 `g4_drill_ex`（port 8765、AI 關閉）演練，結束時關閉行程、刪除資料庫。崩潰一律用 `SIGKILL` 模擬；要讓行程停在交易中途，是由另一條連線鎖住它接下來要寫的表或列。

| 情境 | 做法 | 預期（依據） |
| --- | --- | --- |
| A 重啟時有 `running` 工作 | 31 行貼上產生背景工作；鎖住 `ai_runs`，工作停在 `running` 時砍掉行程，再重啟 | 工作改回 `queued` 續跑完成，`attempts` 保留後再加一（spec 6.1） |
| B 寫入中途崩潰 | 鎖住 `events`，整批順延 commit 已寫入 batch（交易已有 xid）、卡在寫事件時砍掉行程 | 任務日期與版本、`events`、`batches` 都沒變；重啟後同一請求成功（AC-57） |
| C1 列被鎖住 | 另一連線 `FOR UPDATE` 鎖住任務 2 秒後放開 | 改期請求等待後完成，只寫一筆事件 |
| C2 鎖住期間版本被改 | 另一連線鎖住並把 `version` 加一後提交 | 改期請求回 409 `STALE_VERSION`，不寫入（spec 7） |
| C3 死結 | 另一連線先鎖任務 22，整批順延鎖 13、14 後等 22，另一連線再鎖 13；另一連線 `deadlock_timeout=10s`，讓服務端被選為犧牲者 | 服務端收到 40P01 後整筆重試並成功；`pg_stat_database.deadlocks` 加一（spec 7：重試最多 3 次） |

| 日期 | 環境 | 結果 |
| --- | --- | --- |
| 2026-11-20 | macOS、Docker `postgres:17`、遷移 0005、`weekly.sql` 種子 | 12／12 項通過 |

- 破壞檢查：把 `Database.run` 的 `MAX_RETRIES` 暫時改成 0，C3 變成 HTTP 500（已還原），確認演練抓得到「沒有重試」。這次 500 的日誌只記 `unhandled error: OperationalError`，沒有 traceback 或資料庫訊息（DA-25、資安規則 3）。
- 已知問題：背景工作在「候選已存、工作狀態未更新」之間崩潰時，重啟後會重複建立候選並再呼叫 AI，見 #107（Dev-B）。演練以行程內模擬重現，修正後由 #107 的測試涵蓋。
- 資料庫整個停掉的情境不在 13.5 範圍；`pool_pre_ping` 會在資料庫恢復後重新連線。
