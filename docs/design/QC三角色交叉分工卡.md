# QC 三角色交叉分工卡

> 版本：2026-11-19 產品負責人裁定（**方案甲** ＋ **真人 QC 第三關**，解讀②）。
> 本卡為「審查與驗收分工」的單一事實來源；與本卡衝突的舊敘述以本卡為準。
> README 的「審查配對」（line 23）與第 15 行已同步更新為方案甲。

## 一、角色對照
| 代號 | 角色 | GitHub | 線 |
|---|---|---|---|
| A | Dev-A 核心規則線 | @n731110NK | Phase 0–4、前端 12.2/12.4/12.5 |
| B | Dev-B 資料進出與 AI 線 | @MoraChen | Phase 5–8、前端 12.7/12.8/12.11 |
| C | Dev-C 前端與目標週報線（＝產品負責人） | @shirleywu1200-dotcom | Phase 9–11、前端其餘頁面 |
| QC（第三關） | CI 自動 AC ＋ 阿想契約抽查 | 阿想（Claude，≠實作者） | 黑箱依 spec／OpenAPI／AC；L2 由 PO 抽查 |

## 二、三關卡順序（每張 PR 都要走完）
1. **自測綠**：開發自己的單元測試 ＋ CI 全綠（typecheck／build／openapi:check／format…）。
2. **Code Review（配對開發）**：依第三節配對，由「另一位開發」讀碼審查通過。
3. **QC 驗收（CI＋阿想抽查）**：CI 跑 acceptance／AC 測試（綠才可合）；阿想依 spec／OpenAPI／AC 做黑箱契約抽查，**不讀實作**。關鍵前端頁的 L2 runtime 由 PO 抽查。

→ 三關皆過才合併；**不得自審自核**（C＝PO 的 PR 一樣要經 A 審，PO 不自行核准）。
→ 對應 README「合併條件」：① 開發單元測試綠＝關卡1；② QC 的 AC 驗收測試綠＝關卡3（真人）；③ 另一位開發審查通過＝關卡2。

## 三、Code Review 配對（方案甲，循環 A→B→C→A）
| 功能來源 | 寫碼 | Code Reviewer |
|---|---|---|
| Dev-A 的 | A | **B（@MoraChen）** |
| Dev-B 的 | B | **C（@shirleywu1200-dotcom）** |
| Dev-C 的 | C | **A（@n731110NK）** |

- 記法：各自審「上一棒」（A 審 C、B 審 A、C 審 B）。
- **特例**：涉及 `adjust_due` 的 PR，A 與 B 互審（沿 README line 24 既有規則）。

## 四、QC 驗收＝CI 自動 AC ＋ 阿想契約抽查（2026-11-19 更新；取消真人 QC-2）
- **CI 自動 AC 驗收**：acceptance／AC 測試依 spec／OpenAPI／AC 撰寫，CI 每次執行、綠才可合（對應 README 合併條件②）。測試由**阿想維護／把關契約一致性**（Dev 可提交、阿想審）；小工頭不碰驗收。
- **阿想契約抽查**：阿想依 spec／OpenAPI／AC 黑箱抽查，**不讀實作**；獨立性來自「阿想≠實作者，且跨模型（Claude 抽查 Codex）」。
- **L2 真人 runtime**：關鍵前端頁（今日頁／回報頁等）由 PO（大梅）抽查，或接受降級。
- **鐵律**：小工頭只實作自己線、**永不驗收任何 PR**。
- 取消 QC-2 真人第三關（#79）。保留的核心獨立性在**真人 Code Review**（方案甲 Dev-A／Dev-B／阿想 互審）。

## 五、生效與過渡
- 本卡自 **2026-11-19** 生效。
- **在途不回溯**：PR #66、#75（Dev-C 的）續由 @MoraChen 審完；新配對（Dev-C 的 PR 由 A 審）自其後的 PR 起算。
- **啟用時序**：C 的 Reviewer 角色即刻生效（審 Dev-B 的功能）；B 的 Reviewer 角色待 B 就緒後生效（審 Dev-A 的功能，含 #76）。B 就緒前，Dev-A 的 PR 若需 Review，由產品負責人協調安排。
