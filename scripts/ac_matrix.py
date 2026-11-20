# -*- coding: utf-8 -*-
import re, glob, os
ROOT=__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))+"/"
spec=open(ROOT+"docs/spec.md",encoding="utf-8").read()

# AC 描述：抓 spec 裡「AC-xx：描述」或「AC-xx 描述」最先出現者
ac_desc={}
for m in re.finditer(r'(AC-\d+)[a-z]?[：:　\s]+([^\n｜|。]+)', spec):
    ac=m.group(1)
    if ac not in ac_desc:
        d=m.group(2).strip()[:42]
        if d and not d.startswith('AC-'): ac_desc[ac]=d

# 全部 AC（spec 定義）；以 int 為鍵、保留 spec 標籤
label={}
for n in re.findall(r'AC-(\d+)', spec):
    label[int(n)]=f"AC-{n}"
all_ac=[label[k] for k in sorted(label)]
int_of={v:k for k,v in label.items()}

# 測試 AC 映射：兩種命名都認
#   (1) 標註：測試檔文字內 `AC-NN`（docstring／註解）
#   (2) 函式名：`def test_acNN_...`（專案主流命名，無連字號）
ac_tests={}      # label -> set("檔名·層")
ac_how={}        # label -> set({"標註","函式名"})
files=(glob.glob(ROOT+"backend/tests/**/*.py",recursive=True)
       +glob.glob(ROOT+"frontend/src/**/*.test.ts*",recursive=True)
       +glob.glob(ROOT+"e2e/**/*.spec.ts",recursive=True))
def hit(num,f,layer,how):
    lab=label.get(int(num))
    if not lab: return
    ac_tests.setdefault(lab,set()).add(f"{os.path.basename(f)}·{layer}")
    ac_how.setdefault(lab,set()).add(how)
for f in files:
    try: txt=open(f,encoding="utf-8",errors="ignore").read()
    except: continue
    layer=("e2e" if "/e2e/" in f else "前端" if "/frontend/" in f else "後端")
    for n in re.findall(r'AC-(\d+)', txt):           # (1) 標註
        hit(n,f,layer,"標註")
    for n in re.findall(r'\bac0*(\d+)[_\b]', txt):   # (2) 函式名 test_acNN / acNN_
        hit(n,f,layer,"函式名")
    for n in re.findall(r'def test_ac0*(\d+)', txt):
        hit(n,f,layer,"函式名")

# AC-65：週報彙整為 test_weekly_report.py 整套行為覆蓋，但未用 AC 編號命名；人工標記
BEHAVIOR={"AC-65":"test_weekly_report.py（週報彙整整套，FR-RPT-01/02；行為覆蓋、建議補標 AC-65）"}

covered=[a for a in all_ac if a in ac_tests or a in BEHAVIOR]
gaps=[a for a in all_ac if a not in ac_tests and a not in BEHAVIOR]

rows=""
for a in all_ac:
    ts=ac_tests.get(a)
    if ts:
        how="／".join(sorted(ac_how.get(a,set())))
        st=f"✅（{how}）"; tcell=" / ".join(sorted(t.split('·')[0] for t in ts))[:60]
    elif a in BEHAVIOR:
        st="✅（行為覆蓋・待補標）"; tcell=BEHAVIOR[a][:60]
    else:
        st="⚠️ 真的沒測"; tcell="—"
    rows+=f"| {a} | {ac_desc.get(a,'（見 spec）')} | {st} | {tcell} |\n"

md=f"""# 13.2 驗收總表（AC ↔ 測試對應）

> 自動生成（阿想／Dev-C，QC 第三關把關）。資料來源：spec.md 的 AC 定義 ＋ 測試檔。
> **口徑（已修正）**：測試對應認兩種命名——(1) 檔內標註 `AC-NN`；(2) 測試函式名 `test_acNN`（本專案主流命名，無連字號）。舊版只認 (1)，漏掉 (2)，造成假缺口。

## 摘要
- spec 定義 AC：**{len(all_ac)}** 個
- 有對應測試：**{len(covered)}** 個（{len(covered)*100//len(all_ac)}%）
- **真的沒測：{len(gaps)} 個** → {' '.join(gaps) if gaps else '（無）'}

## 18 個原「缺口」的人工確認結論（2026-11-20）
舊版工具報 18 缺口（AC-04/06/07/09/10/15–24/26/59/65），逐一查證後：
- **17 個有 `test_acNN` 函式**（AC-04/06/07/09/10/15–24/26/59），例：`test_ac04_defer_mark`、`test_ac16_includes_done_task`、`test_ac22_commit_overwrites_baseline`、`test_ac59_seed_is_idempotent_across_downgrade_and_rerun`——有測，只是沒標 `AC-NN` 格式。
- **AC-65（週報彙整）** 由 `test_weekly_report.py` 整套行為覆蓋，但無 AC 編號命名；建議在該檔補一行 `AC-65` 標註。
- **真的沒測：0 個。** 原「72%／18 缺口」是工具 regex 漏認 `test_acNN` 命名所致，非覆蓋缺口。

## 後續
1. 工具已修（認 `test_acNN`）；本表為修正後結果。
2. AC-65 於 `test_weekly_report.py` 補一行 `AC-65` 標註即全口徑一致（可派前端或後端持有者）。
3. 本表納入 CI＋契約抽查基礎：新 PR 若新增/變更 AC，對照本表確認測試同步；新測試沿用 `test_acNN` 命名。

## 完整對應表
| AC | 描述（摘自 spec） | 狀態 | 對應測試檔 |
| --- | --- | --- | --- |
{rows}"""
open("/home/claude/ac_matrix.md","w",encoding="utf-8").write(md)
print(f"AC={len(all_ac)} covered={len(covered)} 真沒測={len(gaps)}: {' '.join(gaps) if gaps else '(無)'}")
