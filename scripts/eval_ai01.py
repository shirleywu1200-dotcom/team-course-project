"""AI-01 評估：用標註集呼叫真實供應商，算出「收件匣結果」的命中率、延遲與費用（13.4 SDD D-5、第 3 節）。

會產生費用。執行前先印估算並等你輸入 y；累計費用超過 --max-cost 就停止。
終端機只印案例 id、分類與統計。設了環境變數 EVAL_OUT_DIR（放 env/local.env）時，另存逐則 CSV
（含訊息、預期、AI 原始輸出、R2 結果，以及空白的「檢視判定」欄供人工標記）；標註集只放虛構對話，所以可以存原文。

用法（需 env/local.env 有 ANTHROPIC_API_KEY）：
    cd backend
    PYTHONUTF8=1 .venv/Scripts/python ../scripts/eval_ai01.py --model claude-sonnet-5-5
    選項：--cases 檔案（預設 scripts/eval_data/ai01_cases.json）、--limit 10（只跑前 N 則）、--max-cost 1.0（美元）
判定：每則訊息經 R2 規則後的 kind、task_id、new_due 與 expect 全部相同才算命中。
上下文案例（有 messages 陣列）整段一起送一次，裡面每則訊息各自計分，id 記為 c16-1、c16-2。
延遲與 token 是整次呼叫的數字，上下文案例的每一列重複顯示。
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.anthropic_client import AnthropicAIClient  # noqa: E402
from app.ai.client import AIError  # noqa: E402
from app.config import DEFAULT_ENV_FILE, load_env_file  # noqa: E402
from app.domain.inbox import r2  # noqa: E402

PRICES = {   # 美元／百萬 token（輸入, 輸出），2026-11 公告價
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
EST_IN, EST_OUT = 1200, 150   # 單次估算：冒煙測試實測約 1,100／50，取寬


def cost(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICES[model]
    return (tin * pin + tout * pout) / 1_000_000


def messages_of(case: dict) -> list[dict]:
    """單則案例（speaker/text/expect）或上下文案例（messages 陣列）都轉成訊息清單。"""
    return case.get("messages") or [{k: case[k] for k in ("speaker", "text", "expect")}]


def outcomes(output: dict, texts: dict[int, str], task_ids: set[int], today: date) -> dict[int, dict]:
    """經 R2 後每則訊息（ref）在收件匣的結果；沒有候選的訊息為 none。"""
    got = {ref: {"kind": "none", "task_id": None, "new_due": None} for ref in texts}
    for d in r2.apply(output, texts, task_ids, today):
        got[d.source_id] = {"kind": d.kind, "task_id": d.task_id,
                            "new_due": d.proposed["new_due"] if d.kind == "delay" else None}
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(PRICES))
    ap.add_argument("--cases", default=str(ROOT / "scripts" / "eval_data" / "ai01_cases.json"))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-cost", type=float, default=1.0)
    args = ap.parse_args()

    load_env_file(Path(os.environ.get("G4_ENV_FILE", DEFAULT_ENV_FILE)))
    data = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    cases = data["cases"][: args.limit]
    today = date.fromisoformat(data["today"])
    task_ids = {t["id"] for t in data["tasks"]}

    est = cost(args.model, EST_IN, EST_OUT) * len(cases)
    print(f"模型 {args.model}，{len(cases)} 次呼叫，估計約 ${est:.3f}（上限 ${args.max_cost}）")
    if input("確定執行？輸入 y：").strip().lower() != "y":
        print("已取消")
        return 1

    ai = AnthropicAIClient(api_key=os.environ.get("ANTHROPIC_API_KEY", ""), model=args.model)
    spent, tin_sum, tout_sum, latencies = 0.0, 0, 0, []
    by_cat = defaultdict(lambda: [0, 0])
    misses, rows = [], []
    for case in cases:
        if spent >= args.max_cost:
            print(f"已達費用上限 ${args.max_cost}，停止")
            break
        msgs = messages_of(case)   # 上下文案例整段一起送，與實際收件相同
        texts = {i: m["text"] for i, m in enumerate(msgs, 1)}
        payload = {"today": data["today"], "tasks": data["tasks"],
                   "messages": [{"ref": i, "speaker": m["speaker"], "spoken_at": None, "text": m["text"]}
                                for i, m in enumerate(msgs, 1)]}
        ai.last_usage = (0, 0)
        started = time.monotonic()
        raw = None
        try:
            raw = ai.call("AI-01", payload)
            got_by_ref = outcomes(raw, texts, task_ids, today)
        except AIError as exc:
            got_by_ref = {i: {"error": type(exc).__name__} for i in texts}
        latencies.append(time.monotonic() - started)
        tin, tout = ai.last_usage
        tin_sum, tout_sum = tin_sum + tin, tout_sum + tout
        spent += cost(args.model, tin, tout)
        for i, m in enumerate(msgs, 1):   # 每則訊息各自計分
            mid = case["id"] if len(msgs) == 1 else f"{case['id']}-{i}"
            exp, got = m["expect"], got_by_ref[i]
            hit = got == exp
            by_cat[case["category"]][0] += hit
            by_cat[case["category"]][1] += 1
            if not hit:
                misses.append((mid, case["category"], exp, got))
            rows.append({"id": mid, "分類": case["category"], "發言者": m["speaker"], "訊息": m["text"],
                         "命中": "Y" if hit else "N",
                         "預期_kind": exp["kind"], "預期_task_id": exp["task_id"], "預期_new_due": exp["new_due"],
                         "實際_kind": got.get("kind", got.get("error")), "實際_task_id": got.get("task_id"),
                         "實際_new_due": got.get("new_due"),
                         "AI原始輸出": "" if raw is None else json.dumps(raw, ensure_ascii=False),
                         "延遲秒": f"{latencies[-1]:.1f}", "輸入token": tin, "輸出token": tout,
                         "檢視判定": "", "備註": ""})

    done = sum(n for _, n in by_cat.values())
    hits = sum(h for h, _ in by_cat.values())
    print(f"\n命中 {hits}/{done}（{hits / max(done, 1):.0%}）")
    for cat, (h, n) in sorted(by_cat.items()):
        print(f"  {cat}：{h}/{n}")
    if latencies:
        lat = sorted(latencies)
        print(f"延遲：中位數 {lat[len(lat) // 2]:.1f} 秒，最慢 {lat[-1]:.1f} 秒")
    print(f"token：輸入 {tin_sum:,}、輸出 {tout_sum:,}；費用約 ${spent:.4f}")
    if misses:
        print("\n未命中（id、分類、預期 → 實際）：")
        for cid, cat, exp, got in misses:
            print(f"  {cid} {cat}：{exp} → {got}")
    out_dir = os.environ.get("EVAL_OUT_DIR")
    if out_dir and rows:
        path = Path(out_dir) / f"{time.strftime('%Y%m%d-%H%M')}_AI-01_{args.model}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:   # BOM：Excel 開中文不亂碼
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n逐則結果：{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
