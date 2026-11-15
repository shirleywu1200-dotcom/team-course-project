# SQL 種子夾具庫（QC-1 維護）

QC 用的共用種子資料放這裡（`.sql` 檔）。Dev 可以使用、不可修改；需要新資料時向 QC 提需求（todo 5.7）。

用法：在測試中 `seed(Path("tests/fixtures/xxx.sql").read_text())`。

PostgreSQL 的寫法注意（docs/decisions.md DA-01）：

1. 布林欄位寫 `true`／`false`，不能寫 `0`／`1`（例如 `mine`、`blocked`、`notified`、`bound`）。
2. 日期寫 `'2026-11-11'`；時間戳寫 `'2026-11-11T10:00+08:00'`。
3. JSON 欄位直接寫 JSON 字串，例如 `'["a","b","c","d","e"]'`。
4. **同一份腳本裡，同一張表不要混用「指定 id」與「不指定 id」**。`seed()` 是在整份腳本跑完後才重設 id 序列，混用會撞號。要嘛整張表都指定 id，要嘛都不指定。
5. `events` 與 `rubrics` 只能新增，不能 UPDATE、DELETE、TRUNCATE；每個測試都有獨立資料庫，不需要清資料。
6. **系統種子已在範本資料庫裡**（遷移 0003）：`settings` 有 id=1 那一列、`rubrics` 有 version=0（id=1）。種子 SQL 不要再插入這兩列；要改設定就 UPDATE `settings`；要測多版本量表就插入 `version >= 1`，且不要指定 id 1（spec 4.2.1）。
