# Phase 7 SDD：收件、候選與背景工作（Dev-B）

依據：spec 3.11（FR-INB-01～16）、3.16（FR-AI-01～06）、5.3、5.11、6.1、6.6；todo Phase 7（7.1～7.11，7.12 不做）；AC-12a、34～42。
寫入路徑：候選確認只經 Dev-A 的 `adjust_due`、`complete_task`、`set_blocked`、`create_task`，不直接寫 `events` 或 `tasks`。

## 1. 端點（spec 5.11）

| Method | Path | 任務 | 說明 |
| --- | --- | --- | --- |
| POST | `/ingest` | 7.1–7.5 | 貼上文字；≤ 30 行同步，> 30 行建背景工作 |
| GET | `/ingest/jobs/{id}` | 7.5 | 查工作狀態 |
| GET | `/candidates` | 7.6 | `?state=open`（預設 open）。不提供專案篩選：`unmatched` 沒有任務、不屬於任何專案（Phase 5 Q1） |
| POST | `/candidates/{id}/confirm` | 7.6、7.9 | `delay`／`done`／`stuck` 用 |
| POST | `/candidates/{id}/clarify` | 7.7 | `unclear` 用：採用建議 |
| POST | `/candidates/{id}/create-task` | 7.7 | `unmatched` 用：建立新任務 |
| POST | `/candidates/{id}/ignore` | 7.8 | 任何種類皆可 |

`/webhooks/line`（7.12）依分工裁定不做。

## 2. 收件流程與交易切分

AI 呼叫可能長達 20 秒 × 3 次，不能包在資料庫交易裡（會長時間佔住連線與列鎖）。所以一次收件切成三段，每段一個 `Database.run`：

```
交易 1：大小檢查 → 拆訊息 → 去重 → 寫 sources（> 30 行時另寫 jobs(queued)，到此回 async）
（交易外）呼叫 AI-01，最多 3 次（1 次＋重試 2 次）
每次結果一個短交易：失敗只寫 ai_runs；成功時 ai_runs＋R2 後的 candidates(open) 一起寫
```

- AI 全部失敗：sources 保留、不寫任何候選或事件（AC-40）。同步回 200＋`ai_status=unavailable|invalid_output`，背景工作標 `failed`。
- 同步與背景共用同一個函式 `process_sources(source_ids)`，差別只在誰呼叫它。
- 續跑只針對逾時與不合格式；`AIUnavailable`（供應商不可用）不重試，直接走退路。

### 2.1 拆訊息（7.1，Q2 裁定：寬鬆解析）

使用者可以任意貼上，所以解析器的原則是「能認就認，認不出也不丟內容，並告訴使用者哪幾行沒認出來」。

**每行依序嘗試三種樣式**，前一種不符才試下一種：

| 順序 | 樣式 | 例子 |
| --- | --- | --- |
| A | 時間＋發言者＋內容，三者以括號、冒號、Tab 或空白任意組合分隔 | `[10:12] 阿德：延到 11/18`、`10:12<Tab>阿德<Tab>延到 11/18`、`10:12  阿德  延到 11/18`、`下午3:05 阿德 延到 11/18` |
| B | 發言者＋冒號＋內容（沒有時間） | `阿德：延到 11/18` |
| C | 以上皆非 | 接到上一則訊息的內容後面（LINE 匯出的多行訊息）；前面沒有訊息時才算無法辨識 |

**容錯範圍**：
- 分隔符：連續多個 Tab 或空白都視為一個。冒號、括號全形半形都可以（`:`／`：`、`[]`／`［］`／`【】`）。
- 時間：`H:MM` 或 `HH:MM`，可帶「上午／下午」（換成 24 小時制）；全形數字也接受。
- 發言者：1–20 字，避免把內容裡的冒號誤當成分隔（例如「阿德：備註：明天」的發言者是「阿德」）。
- 樣式 B 沒有時間時，`spoken_at` 為 NULL（DDL 允許）。

**行首像時間但時間無效**（例如 `25:99`）：只試樣式 A，不退回樣式 B，免得把「25」當成發言者。

**直接略過、不接到上一則**：空白行；LINE 匯出的日期標題行（例如 `2026/11/11（三）`、`2026.11.11 星期三`）。

**回應補一個欄位** `result.unparsed_lines`：無法辨識的行號清單（從 1 起算）。使用者可以照行號修正後重貼，前端也可以據此提示。這是我新增的回應欄位（契約新增，記在 `docs/dev-b/requests-to-dev-a.md` 的通知區，並通知 Dev-C、QC-2）。

**取捨**：樣式 B 可能把內容行（例如「注意：明天開會」）誤判成發言者「注意」。這種情況訊息仍然會送給 AI，只是發言者欄位錯了。我判斷這比整行被略過好。

- 文字超過 20,000 字回 413 `PAYLOAD_TOO_LARGE`；沒有任何可辨識的訊息時，回 `created=0`。
- 30 行門檻以「非空白行數」計（spec FR-INB-05 寫的是行數）。

### 2.2 去重與保存（7.1、AC-38）

- `excerpt_hash = sha256(spoken_at + "\n" + speaker + "\n" + 內容)`；已存在就計入 `duplicates`，不寫 source、不送 AI。
- 同一次貼上內的重複行也只算一次。
- `expires_at = received_at + settings.retention_days`；`settings` 尚無資料列時用預設 30 天。
- `excerpt` 只存該行內容，不存整段貼上文字。

## 3. AI-01 介面（我是 `AIClient` 契約擁有者，這裡定義節點輸入輸出，不改 `call` 簽名）

輸入 `payload`：

```json
{ "today": "2026-11-11",
  "messages": [{ "ref": 3, "speaker": "阿德", "spoken_at": "10:12", "text": "畫面規格 v1 確定延到 11/18" }],
  "tasks": [{ "id": 2, "title": "畫面規格 v1", "owner": "阿德", "latest_due": "2026-11-13" }] }
```

- `ref` 是 source id，用來把輸出對回訊息。
- `tasks` 只送「未完成且 `scope=work`」的任務；有帶 `project_id` 時只送該專案的。私人範圍不送 AI（資安規則 2）。

輸出（`call` 回傳的 dict）：

```json
{ "items": [{ "ref": 3, "kind": "delay", "task_id": 2, "new_due": "11/18", "certainty": "sure" }] }
```

- `kind`：`delay`、`done`、`stuck`、`none`（無關）。AI 回的其他欄位（例如原因推測）一律丟棄（7.9、AC-12a）。
- `ai_runs.raw_output` 存 `json.dumps(輸出)`。`call` 丟 `AIInvalidOutput`／`AITimeout`／`AIUnavailable` 時，記為 `invalid_output`／`timeout`／`error`，`error` 欄只放例外類別名稱。

## 4. R2 規則（7.4，純函式，不靠 AI）

逐項依序判斷，每則訊息最多產生一個候選：

1. **格式**：`items` 不是 list、或單項缺 `ref`／`kind`、`kind` 不在白名單、`ref` 不屬於這次送出的訊息 → 該項丟棄並計入 `skipped`。整個輸出不是 dict 或沒有 `items` → 視為 `invalid_output`，觸發重試。
2. **無關**：`kind=none` → 計入 `skipped`。
3. **對不到任務**：`task_id` 為空，或不在這次送出的任務清單內 → `unmatched`／`to_match`，`task_id=NULL`。程式不做模糊比對（AC-37「不猜」）。
4. **語氣降級**：原句含問號（`?`、`？`）、「嗎」、「會不會」，或含「可能、大概、應該、也許」→ `unclear`／`to_clarify`，AI 原本的建議放進 `suggest`（AC-35、36）。AI 回 `certainty` 不是 `sure` 時也降級。程式只會降級，不會升級。
5. **日期轉值**（只對 `delay`）：接受 `YYYY-MM-DD` 或 `M/D`。`M/D` 取今年；若結果比今天早 180 天以上，改為明年。轉不出來或超出允許範圍（今天前 365 天至後 730 天）→ 降為 `unclear`。
6. **同訊息多項**（D-07）：同一個 `ref` 同時有 `done` 與 `delay` → 只留 `done`（見 Q4）。
7. 其餘 → 原種類，`certainty=sure`，`proposed`：`delay` 為 `{"new_due": …}`，`done`／`stuck` 為 `null`。

## 5. 背景工作（7.5，AC-40、41）

- **形式**：與 API 同一個行程的背景執行緒（見 Q1）。`app.main.run()` 啟動時先把 `running` 重設為 `queued`（保留 `attempts`），再啟動執行緒。`create_app` 不啟動執行緒，所以測試不受影響。
- **取件**：`SELECT … WHERE status='queued' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED`，改成 `running`，然後執行 `process_sources`。
- **嘗試次數**：`jobs.attempts` 每呼叫一次 AI-01 加 1，達 3 次仍失敗就標 `failed`。重啟續跑時從已累積的次數接著算，不重新給 3 次。
- **錯誤訊息**：`jobs.error` 放固定的可顯示文字「AI 解析失敗，可在收件匣手動建立任務」，不放例外內容。
- **測試**：測試直接呼叫 `worker.run_once()`，不開執行緒、不睡眠。

## 6. 候選確認（7.6～7.9）

所有確認類端點都帶 `expected_version`（任務版本）；候選不是 `open` 時回 409 `CANDIDATE_NOT_OPEN`。候選狀態更新與任務寫入在同一個交易內完成。

| 端點 | 適用種類 | 呼叫 | 回應重點 |
| --- | --- | --- | --- |
| `confirm` | `delay` | `adjust_due(…, reason=None, note=None, mark=None, defer_mark=True, origin="candidate", origin_ref=候選id, source_id=…)`；`new_due` 可覆寫建議值 | `needs_mark`（DA-04） |
| `confirm` | `done` | `complete_task(…, origin="candidate", …)` | `feedback_required=true` |
| `confirm` | `stuck` | `set_blocked(…, True, origin="candidate", …)` | |
| `clarify` | `unclear` | 依 `suggest` 的種類，走上面三種之一 | 同上 |
| `create-task` | `unmatched` | `create_task(title, owner, due, project_id)` | 新任務 |
| `ignore` | 全部 | 只改候選狀態 | |

- 用錯端點（例如對 `unclear` 呼叫 `confirm`）→ 422 `VALIDATION_ERROR`。
- `reason`、`mark` 一律傳 `None`（7.9、AC-12a）；回應不含任何原因欄位。
- 任務已完成 → `TASK_DONE`，候選維持 `open`（spec 6.1）。
- `ai_feedback`（7.8，FR-AI-04）：`target_type='candidate'`；照建議確認為 `accepted`，改了日期為 `edited`，忽略為 `ignored`，`create-task` 為 `changed`。
- 每次處理都寫 `decision`、`decided_at`。Dev-A 的「每日確認時間」近似值（`metrics_repo.daily_confirm_span_minutes`）就是讀這兩欄。

## 7. 檔案配置（照 Dev-A 的分層）

| 層 | 檔案 | 內容 |
| --- | --- | --- |
| 資料存取 | `db/repo/sources_repo.py`、`candidates_repo.py`、`jobs_repo.py`、`ai_runs_repo.py`（新） | 各表的 insert／get／update；`jobs_repo.claim_next` |
| 規則 | `domain/inbox/parse.py` | 拆訊息、雜湊（純函式） |
| 規則 | `domain/inbox/r2.py` | R2 規則（純函式） |
| 規則 | `domain/inbox/ingest.py` | 交易切分、AI 呼叫與重試、`process_sources` |
| 規則 | `domain/inbox/confirm.py` | 確認、待釐清、建立任務、忽略 |
| 規則 | `domain/inbox/r1.py` | R1（見 Q6） |
| 背景 | `worker.py` | `run_once`、執行緒迴圈、重啟重設 |
| 介面 | `api/routes_inbox.py` | 7 個端點 |
| 測試 | `tests/unit/test_phase7_*.py` | 純函式測試＋端點測試，AI 一律 `FakeAIClient.script` |

另外改兩個自己的檔：`main.py`（註冊路由；`run()` 啟動 worker）、Phase 5 的 `domain/history.py`（見 Q8）。

## 8. 歧義裁定（2026-11-15 產品負責人：Q1、Q3–Q8 依建議定案；Q2 改為寬鬆解析，見 2.1；需要 Dev-A 調整的事項統一記在 `docs/dev-b/requests-to-dev-a.md`）

| # | 歧義 | 我的建議 | 影響 |
| --- | --- | --- | --- |
| Q1 | 背景工作在哪裡跑 | 與 API 同行程的背景執行緒＋`FOR UPDATE SKIP LOCKED`。單使用者、本機部署，不另開 worker 行程或佇列服務 | 部署只要啟動一個行程；之後若要分開，`run_once` 可原封搬走 |
| Q2 | 貼上文字的格式只有 spec 一個範例 | **裁定改為寬鬆解析**：三種樣式＋分隔符容錯＋無法辨識的行回報行號（2.1） | 多出 `result.unparsed_lines` 回應欄位 |
| Q3 | AI 失敗後，同一段文字重貼會被判成重複，沒辦法重跑 | 照 spec：只回重複數，退路是手動建立任務（FR-INB-04、08） | 要支援「重貼即重跑」，`sources` 需要記錄處理狀態，得請 Dev-A 加遷移；不建議為 demo 做 |
| Q4 | D-07 同一則訊息同時有延期與完成 | 採 spec 預設：完成優先，延期留待手動 | 7.10；D-07 正式裁定前先照預設做 |
| Q5 | `create_task` 沒有 `origin` 參數，`unmatched` 建立的任務事件只能記成 `manual`，歷程看不到「依據候選 #id」 | 請 Dev-A 比照 `set_blocked`，給 `create_task` 加 `origin`、`origin_ref`、`source_id` 三個選填關鍵字參數（與 DA-03 同模式，舊呼叫不受影響）。Dev-A 加之前，我先用 `manual`（記為 `requests-to-dev-a.md` R-01） | FR-HIS-04；改的是 Dev-A 的檔案，不是凍結契約 |
| Q6 | 7.12 webhook 不做，R1（AC-42）沒有入口可測 | 仍寫 R1 純函式 `accept_line_message(group)`，在函式層測 AC-42，留給之後的 webhook 使用 | 約 10 行；不建任何端點 |
| Q7 | FR-INB-16「每日確認時間」要記錄實際使用時間，但資料表沒有欄位 | Phase 7 只確實寫 `decided_at`，讓 Dev-A 的近似值可用；推播與實際計時不在 todo Phase 7 | 衡量值缺口 2 維持「近似值」；要精確值需另開票與遷移 |
| Q8 | FR-INB-13 待釐清的事件「依據註記為『待釐清，你確認』」，但 `complete_task`、`set_blocked` 沒有 `note` 參數 | 不寫進事件，改在讀取時推導：Phase 5 的依據標籤遇到 `candidate` 且該候選種類是 `unclear` 時，顯示「候選 #id（待釐清，你確認）」 | 不必改 Dev-A 的函式；事實只存在 `candidates.kind` 一處 |

## 9. 驗收對照

| AC | 測試 |
| --- | --- |
| AC-12a | `FakeAIClient` 輸出夾帶 `reason` → 確認後事件 `reason`、`mark` 為空，回應沒有原因欄位 |
| AC-34 | 收件產生 `open` 候選 → 甘特圖、時間管理統計不變（沿用 Phase 5 測試，再加收件路徑） |
| AC-35、36 | 問句、含「可能」的延期 → `unclear`，任務 `blocked`、`latest_due` 不變 |
| AC-37 | AI 回不在清單內的 `task_id` → `unmatched`、`task_id=NULL` |
| AC-38 | 同一段文字貼兩次 → 第二次 `duplicates`＝行數、`created=0` |
| AC-39 | 確認 `delay`：負責人是我 → `needs_mark=true`；不是我 → `false` |
| AC-40 | `FakeAIClient` 連續 3 次不合格式 → 工作 `failed`、`attempts=3`、`sources` 保留、候選與事件 0 筆 |
| AC-41 | 31 行 → `mode=async`＋`job_id`；`run_once` 後可查到 `succeeded` |
| AC-42 | 未綁定或未告知的群組 → R1 回丟棄，`sources` 不新增 |
| 重啟 | 種子一筆 `running` 工作 → 重設後為 `queued`，`attempts` 保留 |
| 寬鬆解析 | spec 範例、Tab 分隔、多個空白、全形冒號與括號、上午／下午、無時間、多行訊息接續、日期標題略過、無法辨識的行號 |
| 確認衝突 | `TASK_DONE`、`STALE_VERSION`、`CANDIDATE_NOT_OPEN`、用錯端點 |
