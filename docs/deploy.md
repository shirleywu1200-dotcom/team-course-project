# 部署文件（todo 13.7）

適用範圍：單機、單一使用者（spec 8.2）。後端行程、靜態前端、PostgreSQL 都在同一台機器上，預設只綁 `127.0.0.1`。

## 1. 需要的軟體

| 軟體 | 版本 | 用途 |
| --- | --- | --- |
| PostgreSQL | 15 以上（開發用 17） | 資料庫 |
| Python | 3.12（用 uv 管理） | 後端 |
| Node.js | 22 以上 | 建置前端 |
| gitleaks | 最新版 | pre-commit 掃描祕密 |

## 2. 環境變數

全部放在 `env/local.env`（不進版控）。範例見 `env/example.env`。

| 變數 | 必填 | 說明 |
| --- | --- | --- |
| `G4_DATABASE_URL` | 是 | `postgresql+psycopg://帳號:密碼@127.0.0.1:5432/g4` |
| `G4_API_TOKEN` | 是 | API 的 Bearer token；空值時所有 API 回 401 |
| `G4_BIND_HOST` | 否 | 預設 `127.0.0.1`。改成其他值之前，先完成第 6 節的條件 |
| `G4_PORT` | 否 | 預設 `8000` |
| `G4_TEST_ADMIN_URL` | 只有跑測試時需要 | 可建立與刪除資料庫的帳號，連到 `postgres` 資料庫 |
| `G4_PG_DUMP_CMD` | 否 | 備份指令；未設定時用 `pg_dump --format=custom --dbname=…` |
| `VITE_API_TOKEN` | 否 | 只在前端開發時使用；正式建置不要設定，改在畫面上輸入 token |

產生 token：`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

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

## 5. 備份與還原

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

## 6. 對外開放前的條件（spec 8.2）

預設只綁 `127.0.0.1`。要讓其他裝置（例如手機）連線之前，下列三項都要完成：

1. **TLS**：由反向代理終結 TLS（例如 Caddy 或 nginx），後端仍只綁本機，只由代理轉入。
2. **token 輪替**：見第 7 節，並把輪替週期寫進維運紀錄。
3. **限制來源**：反向代理只允許必要的來源（例如家用網段或 VPN），不直接暴露在公網。

## 7. token 輪替

1. 產生新 token，寫入 `env/local.env` 的 `G4_API_TOKEN`。
2. 重新啟動後端；舊 token 立即失效。
3. 在前端畫面重新輸入 token（前端存在瀏覽器的 `localStorage`）。

目前一次只接受一個 token，輪替時會短暫中斷，單一使用者情境可接受。

## 8. 日誌

- 後端日誌只記錯誤類型與 ID，不記文件內容、摘錄原文或 token（CLAUDE.md 資安 3）。
- 未預期的例外只記錄類型名稱，不留 traceback；資料庫例外訊息也不帶 SQL 參數值（DA-25）。除錯時請在本機用測試重現。
- API 文件：`/docs`、`/redoc` 已關閉；OpenAPI 在 `/api/v1/openapi.json`，需要 token（DA-24）。
- 不接任何第三方遙測或錯誤回報服務（CLAUDE.md 資安 2）。
