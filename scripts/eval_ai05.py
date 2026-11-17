"""AI-05 評估：用評估案例呼叫真實供應商，算出格式通過率、R4 通過率、項目齊全率、延遲與費用
（docs/dev-b/ai-05-sdd.md 第 5 節）。

會產生費用。執行前先印估算並等你輸入 y；累計費用超過 --max-cost 就停止。
終端機只印案例 id 與統計。設了環境變數 EVAL_OUT_DIR（放 env/local.env）時，另存逐案 CSV
（含 draft 與 items，以及空白的「檢視判定」欄供人工看格式與用詞）；案例全是虛構資料，所以可以存原文。

用法（需 env/local.env 有 ANTHROPIC_API_KEY）：
    cd backend
    PYTHONUTF8=1 .venv/Scripts/python ../scripts/eval_ai05.py --model claude-sonnet-5-5
    選項：--cases 檔案（預設 scripts/eval_data/ai05_cases.json）、--only large（只跑指定 id）、--max-cost 0.3（美元）
判定（與正式流程相同的兩道檢查，再加一項齊全度）：
    格式：domain/ai05.parse_output 不丟例外。
    R4：domain/weekly_report.reconcile 通過（每一項都是 payload 允許的組合）。
    齊全：items 的（段落、任務）等於 payload 的全部組合；R4 只擋多出來的，空的 items 也會通過，所以另外算。
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.anthropic_client import AnthropicAIClient  # noqa: E402
from app.ai.client import DEFAULT_TIMEOUT_S, AIError  # noqa: E402
from app.config import DEFAULT_ENV_FILE, load_env_file  # noqa: E402
from app.domain import ai05  # noqa: E402
from app.domain.weekly_report import SECTIONS, WeekData, reconcile  # noqa: E402

PRICES = {   # 美元／百萬 token（輸入, 輸出），2026-11 公告價
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
EST_IN, EST_OUT = 2500, 1500   # 單次估算（SDD 第 5 節），取寬


def cost(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICES[model]
    return (tin * pin + tout * pout) / 1_000_000


def week_data(payload: dict) -> WeekData:
    return WeekData(week_start=date.fromisoformat(payload["week"]["start"]),
                    week_end=date.fromisoformat(payload["week"]["end"]), excluded_private=0,
                    **{s: payload[s] for s in SECTIONS})


def expected_pairs(payload: dict) -> set[tuple[str, int]]:
    return {(s, i["task_id"]) for s in SECTIONS for i in payload[s]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(PRICES))
    ap.add_argument("--cases", default=str(ROOT / "scripts" / "eval_data" / "ai05_cases.json"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--max-cost", type=float, default=0.3)
    args = ap.parse_args()

    load_env_file(Path(os.environ.get("G4_ENV_FILE", DEFAULT_ENV_FILE)))
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]

    est = cost(args.model, EST_IN, EST_OUT) * len(cases)
    print(f"模型 {args.model}，{len(cases)} 次呼叫，估計約 ${est:.3f}（上限 ${args.max_cost}）")
    if input("確定執行？輸入 y：").strip().lower() != "y":
        print("已取消")
        return 1

    ai = AnthropicAIClient(api_key=os.environ.get("ANTHROPIC_API_KEY", ""), model=args.model)
    spent, tin_sum, tout_sum = 0.0, 0, 0
    counts = {"格式": 0, "R4": 0, "齊全": 0}
    rows = []
    for case in cases:
        if spent >= args.max_cost:
            print(f"已達費用上限 ${args.max_cost}，停止")
            break
        payload = case["payload"]
        ai.last_usage = (0, 0)
        started = time.monotonic()
        draft, items, error = "", [], ""
        try:
            draft, items = ai05.parse_output(ai.call(ai05.NODE, payload, timeout_s=DEFAULT_TIMEOUT_S))
        except AIError as exc:
            error = type(exc).__name__
        latency = time.monotonic() - started
        tin, tout = ai.last_usage
        tin_sum, tout_sum = tin_sum + tin, tout_sum + tout
        spent += cost(args.model, tin, tout)
        ok = {"格式": not error}
        ok["R4"] = ok["格式"] and reconcile(items, week_data(payload))
        ok["齊全"] = ok["R4"] and {(i["section"], i["task_id"]) for i in items} == expected_pairs(payload)
        for k, v in ok.items():
            counts[k] += v
        print(f"  {case['id']}：" + "、".join(f"{k}{'✓' if v else '✗'}" for k, v in ok.items())
              + f"；{latency:.1f} 秒；token {tin:,}／{tout:,}" + (f"；{error}" if error else ""))
        rows.append({"id": case["id"], "分類": case["category"], **{k: "Y" if v else "N" for k, v in ok.items()},
                     "錯誤": error, "延遲秒": f"{latency:.1f}", "輸入token": tin, "輸出token": tout,
                     "draft": draft, "items": json.dumps(items, ensure_ascii=False), "檢視判定": "", "備註": ""})

    n = len(rows)
    print("\n" + "、".join(f"{k} {v}/{n}" for k, v in counts.items()))
    if rows:
        slowest = max(float(r["延遲秒"]) for r in rows)
        print(f"最慢 {slowest:.1f} 秒（逾時 {DEFAULT_TIMEOUT_S} 秒；SDD 驗收要低於 15 秒）")
    print(f"token：輸入 {tin_sum:,}、輸出 {tout_sum:,}；費用約 ${spent:.4f}")
    out_dir = os.environ.get("EVAL_OUT_DIR")
    if out_dir and rows:
        path = Path(out_dir) / f"{time.strftime('%Y%m%d-%H%M')}_AI-05_{args.model}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:   # BOM：Excel 開中文不亂碼
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n逐案結果：{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
