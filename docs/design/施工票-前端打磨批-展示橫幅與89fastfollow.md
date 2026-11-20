# 施工票 前端打磨批：展示橫幅 ＋ #89 fast-follow — Dev-C

**狀態**：可開工（不卡 Dev-A；都在 main 上的前端）
**分支**：`dev-c/feat-demo-polish`（起點 `main`）

## A. 展示用橫幅（選 A 展示實例需要）
- 全頁頂常駐一條：「展示實例・資料皆為範例・請勿輸入真實資料」。
- 用全域 CSS 變數、亮/暗兩套、Noto Sans TC；由環境旗標開關（正式展示部署才顯示，一般開發隱藏）。
- 不擋操作、不佔主內容空間（sticky bar 或頂部 banner）。

## B. #89 階段1 的兩個 fast-follow（MoraChen approve 時列、可留階段2，現補）
1. `GoalLinkInbox` 收到 `STALE_VERSION` 時，順手 invalidate `goalsMatrix` 與 `goalStats`（否則別處已關聯的任務，矩陣要等下一次成功關聯才追上）。
2. 「已在其他地方處理」提示：下次 mutate 時清掉 `staleTaskId`，否則提示殘留。

## C. Demo 打磨兩項（#94 MoraChen 提；**PO 2026-11-20 已確認納入，要做**）
- 匯入私人專案的「AI 無法判斷欄位」→ 改「私人專案不送 AI，請手動指定」。
- 匯入成功訊息 → 連到專案頁（連結到對應專案頁）。
- 兩項都要補/調對應前端測試。

## 完成定義
- 行為與測試全綠；完整前端測試維持全數通過；typecheck／build／format:check 全過。
- 只動 `frontend/`，不碰後端／契約。
- 完成後回報阿想複審 → 阿想開 PR、指派 Dev-A 審。

## 回報
照交接單格式：分支、commit、完成定義、改動檔案與理由、`git diff --stat`、未做項、PR 狀態。
