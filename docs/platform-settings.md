# GitHub 平台設定清單（開工會議程第 5 項）

對應 todo 5.10 第 5 項與 6.2 保護清單。負責人：Dev-A、QC-1。設定需要 repo 管理員（擁有者 `shirleywu1200-dotcom`）執行；開發與 QC 的帳號只有 Write 權限，改不了 repo 設定。

## 1. 先要決定的事：這個 repo 能不能強制保護

這個 repo 是**個人帳號擁有的私人 repo**。GitHub 官方方案頁在 GitHub Pro 底下列出「Advanced tools and insights in private repositories」，其中包含 Required pull request reviewers、Protected branches、Code owners。

由此推論：在 Free 方案的私人 repo 中，分支保護與 CODEOWNERS 審查無法強制執行【待查證：推論，官方頁面未直接寫出 Free 不可用】。擁有者打開 Settings → Branches 時，若看到需要升級的提示，即可確認。

來源：<https://docs.github.com/en/get-started/learning-about-github/githubs-plans>（2026-11-13 讀取）

| 選項 | 能強制的事 | 代價 | 適合 |
| --- | --- | --- | --- |
| A. 擁有者升級 GitHub Pro | 分支保護、必要審查、CODEOWNERS 審查、必要 CI 檢查 | 擁有者每月付費（金額請以 GitHub 定價頁為準） | 想要平台強制擋下違規合併 |
| B. 把 repo 改為公開 | 同 A，免費 | spec、todo、程式碼全部公開 | 內容沒有保密需求 |
| C. 維持 Free 私人 repo | 平台不強制；只靠 CI 顯示紅燈，加上團隊約定 | 違規合併只能靠人擋 | 接受人工把關 |

**建議**：課程專案沒有保密需求時選 B；需要保密選 A。選 C 時，第 4 節的 CI 路徑檢查就是唯一的自動防線。

## 2. 選 A 或 B 時：`main` 分支保護設定

Settings → Branches → Add branch protection rule，Branch name pattern 填 `main`：

- [ ] Require a pull request before merging
  - [ ] Required approvals：1（審查配對見 todo 5.8）
  - [ ] Dismiss stale pull request approvals when new commits are pushed
  - [ ] Require review from Code Owners
- [ ] Require status checks to pass before merging：勾選 `backend`、`frontend`、`secrets`、`migration-guard`
  - [ ] Require branches to be up to date before merging
- [ ] Do not allow bypassing the above settings（管理員也一樣）
- [ ] 不允許 force push、不允許刪除分支（預設即不允許，確認未打開）

## 3. CODEOWNERS 草稿（檔案位置：`.github/CODEOWNERS`）

需要先收齊各角色的 GitHub 帳號名稱。Code owner 必須對 repo 有 Write 權限（官方 About code owners 頁面）。

```text
# 後面的規則優先於前面的規則
*                                   <產品負責人帳號>

# DDL 與遷移只有 Dev-A 能動（todo 6.2）
/backend/app/db/migrations/         @n731110NK

# 凍結契約（todo 5.7）
/backend/app/domain/events.py       @n731110NK
/backend/app/domain/due.py          @n731110NK
/backend/app/errors.py              @n731110NK
/backend/app/ai/client.py           <Dev-B 帳號>

# QC 的驗收測試與夾具庫只有 QC 能動（todo 6.2）
/backend/tests/acceptance/          <QC-1 帳號> <QC-2 帳號>
/backend/tests/fixtures/            <QC-1 帳號>

# 規格與契約變更需產品負責人核可
/docs/spec.md                       <產品負責人帳號>
/docs/todo.md                       <產品負責人帳號>
```

帳號名稱收齊後由 Dev-A 建立檔案；`<…>` 佔位字不能直接提交，GitHub 會把它標成錯誤的擁有者。

## 4. 不論選哪個方案都要做

- [ ] **Actions 預設權限改為唯讀**：Settings → Actions → General → Workflow permissions 選「Read repository contents and packages permissions」。`ci.yml` 中需要額外權限的工作已自行宣告（`secrets` 工作）。
- [ ] **協作者角色**：開發、QC 為 Write；產品負責人為 Admin 或 Maintain。
- [ ] **Dependabot alerts**：Settings → Code security 開啟。官方方案頁將 Dependabot alerts 列在 Free 方案內。
- [ ] **團隊約定（選 C 時特別重要）**：CI 任何一項紅燈不合併；合併前要有一位審查者在 PR 留下核可；QC 目錄與遷移檔只由負責人修改。

選 C 時可另外加一個 CI 檢查：PR 若修改受保護路徑，而作者不在該路徑的負責人名單中，CI 就亮紅燈。這需要先收齊帳號名稱，並由 Dev-A 實作；平台不會阻止合併，但違規會在 PR 上很明顯。

## 5. 需要收集的資訊

| 項目 | 向誰收 |
| --- | --- |
| Dev-B、Dev-C、QC-1、QC-2 的 GitHub 帳號名稱 | 各本人 |
| 產品負責人的 GitHub 帳號名稱 | 產品負責人 |
| 選 A、B 或 C | 產品負責人與 repo 擁有者 |
