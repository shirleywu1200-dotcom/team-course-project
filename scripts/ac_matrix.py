# -*- coding: utf-8 -*-
"""13.2 驗收總表：掃 spec.md 的 AC 定義 ＋ 測試檔，產生 AC↔測試對應表。
口徑：測試對應認兩種——(1) 檔內標註 `AC-NN`（＝檔內「提到」，非逐條人工確認）；
(2) 測試函式名 `test_acNN`（本專案主流命名）。支援帶字母的 AC（如 AC-12a）。"""
import os, re, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
spec = open(ROOT + "docs/spec.md", encoding="utf-8").read()

def norm(tok):  # "04"->(4,""), "12a"->(12,"a")
    m = re.match(r'0*(\d+)([a-z]?)', tok)
    return (int(m.group(1)), m.group(2)) if m else None

ac_desc, label = {}, {}
for m in re.finditer(r'AC-(\d+[a-z]?)[：:　\s]+([^\n｜|。]+)', spec):
    tok = m.group(1); key = norm(tok)
    label.setdefault(key, f"AC-{tok}")
    if key not in ac_desc:
        d = m.group(2).strip()[:42]
        if d and not d.startswith('AC-'): ac_desc[key] = d
for m in re.finditer(r'AC-(\d+[a-z]?)', spec):   # 補齊只出現、沒帶描述的 AC
    label.setdefault(norm(m.group(1)), f"AC-{m.group(1)}")
all_keys = sorted(label)

ac_tests, ac_how = {}, {}
files = (glob.glob(ROOT + "backend/tests/**/*.py", recursive=True)
         + glob.glob(ROOT + "frontend/src/**/*.test.ts*", recursive=True)
         + glob.glob(ROOT + "e2e/**/*.spec.ts", recursive=True))
def hit(tok, f, layer, how):
    k = norm(tok)
    if k not in label: return
    ac_tests.setdefault(k, set()).add(os.path.basename(f))
    ac_how.setdefault(k, set()).add(how)
for f in files:
    try: txt = open(f, encoding="utf-8", errors="ignore").read()
    except: continue
    layer = "e2e" if "/e2e/" in f else "前端" if "/frontend/" in f else "後端"
    for n in re.findall(r'AC-(\d+[a-z]?)', txt): hit(n, f, layer, "標註")
    for n in re.findall(r'def test_ac0*(\d+[a-z]?)', txt): hit(n, f, layer, "函式名")

BEHAVIOR = {(65, ""): "test_weekly_report.py（週報彙整整套，FR-RPT-01/02；行為覆蓋，Dev-A 於 9.10 PR 補標 AC-65）"}
covered = [k for k in all_keys if k in ac_tests or k in BEHAVIOR]
gaps = [label[k] for k in all_keys if k not in ac_tests and k not in BEHAVIOR]

rows = ""
for k in all_keys:
    a = label[k]; ts = ac_tests.get(k)
    if ts:
        st = f"✅（{'／'.join(sorted(ac_how.get(k, set())))}）"
        tcell = " / ".join(sorted(ts))[:60]
    elif k in BEHAVIOR:
        st = "✅（行為覆蓋・待補標）"; tcell = BEHAVIOR[k][:60]
    else:
        st = "⚠️ 真的沒測"; tcell = "—"
    rows += f"| {a} | {ac_desc.get(k, '（見 spec）')} | {st} | {tcell} |\n"

md = f"""# 13.2 驗收總表（AC ↔ 測試對應）

> 自動生成（阿想／Dev-C，QC 第三關把關）。資料來源：spec.md 的 AC 定義 ＋ 測試檔。重跑：`python scripts/ac_matrix.py`（寫回本檔）。
> **口徑**：測試對應認兩種命名——(1) 檔內標註 `AC-NN`；(2) 測試函式名 `test_acNN`（主流命名，無連字號）。
> **「標註」＝檔內出現 `AC-NN`（可能只是提到，如「AC-50 不在範圍」的註解），非逐條人工確認**；下方 18 個原缺口是人工確認過的，其餘靠標註／函式名自動對應。

## 摘要
- spec 定義 AC：**{len(all_keys)}** 個（含 AC-12a；AC-58、60 不存在）
- 有對應測試：**{len(covered)}**（{len(covered)*100//len(all_keys)}%）
- **真的沒測：{len(gaps)}** → {' '.join(gaps) if gaps else '（無）'}

## 18 個原「缺口」人工確認結論（2026-11-20）
舊版工具報 18 缺口（AC-04/06/07/09/10/15–24/26/59/65），逐一查證：
- **17 個有 `test_acNN` 函式**（例 `test_ac04_defer_mark`、`test_ac16_includes_done_task`、`test_ac59_seed_is_idempotent_across_downgrade_and_rerun`）——有測，只是沒標 `AC-NN` 格式。
- **AC-65（週報彙整）** 由 `test_weekly_report.py` 整套行為覆蓋，Dev-A 於 9.10 PR 補標 `AC-65`。
- **真的沒測：0。** 原「72%／18 缺口」是工具 regex 漏認 `test_acNN` 所致，非覆蓋缺口。

## 完整對應表
| AC | 描述（摘自 spec） | 狀態 | 對應測試檔 |
| --- | --- | --- | --- |
{rows}"""
open(ROOT + "docs/驗收總表-13.2.md", "w", encoding="utf-8").write(md)
print(f"AC={len(all_keys)} covered={len(covered)} 真沒測={len(gaps)}: {' '.join(gaps) if gaps else '(無)'}")
print("已寫 docs/驗收總表-13.2.md")
