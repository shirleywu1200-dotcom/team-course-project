"""AI-03 評估：用評估案例呼叫真實供應商，算出格式、id 合法、覆蓋、準確率、reason 長度、延遲與費用
（docs/dev-b/ai-03-04-sdd.md 第 5 節）。

會產生費用。執行前先印估算並等你輸入 y；累計費用超過 --max-cost 就停止。
終端機只印案例 id 與統計。設了環境變數 EVAL_OUT_DIR（放 env/local.env）時，另存逐案 CSV
（含 items 與空白的「檢視判定」欄供人工看 reason 用詞）；案例全是虛構資料，所以可以存原文。

用法（需 env/local.env 有 ANTHROPIC_API_KEY）：
    cd backend
    PYTHONUTF8=1 .venv/Scripts/python ../scripts/eval_ai03.py --model claude-sonnet-5-5
    選項：--cases 檔案（預設 scripts/eval_data/ai03_cases.json）、--only large（只跑指定 id）、--max-cost 0.3（美元）
payload 由正式的 app.domain.ai03.build_payload 產生，輸出經正式的 parse_output（#85）。
判定：
    格式：節點 Output 驗證與 parse_output 都通過（不丟例外）。
    id 合法：模型原始輸出的每一項，task_id 在 payload、goal_id 在 payload 或為 null
    （parse_output 會靜默丟掉不合法的項目，所以這項看原始輸出，量模型本身）。
    覆蓋：parse_output 之後每個任務剛好一項（使用者實際看到的）。
    準確：parse_output 之後 goal_id 等於案例標註的 expected（以任務計，跨案例加總；expected 為陣列時任一皆算對）。
    困難案例：--cases ../scripts/eval_data/ai03_hard_cases.json
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
from app.domain.ai03 import build_payload, parse_output  # noqa: E402

PRICES = {   # 美元／百萬 token（輸入, 輸出），2026-11 公告價
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
EST_IN, EST_OUT = 1500, 1200   # 單次估算（SDD 第 5 節），取寬


def cost(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICES[model]
    return (tin * pin + tout * pout) / 1_000_000


def formal_payload(case_payload: dict) -> dict:
    # 案例存的是送出格式；還原成 build_payload 的輸入（目標用 id、完成日是 date）再組一次
    goals = [{"id": g["goal_id"], "type": g["type"], "title": g["title"], "period": g["period"]}
             for g in case_payload["goals"]]
    tasks = [{"task_id": t["task_id"], "title": t["title"], "done_date": date.fromisoformat(t["done_date"])}
             for t in case_payload["tasks"]]
    return build_payload(goals, tasks)


def ids_valid(items: list[dict], payload: dict) -> bool:
    tasks = {t["task_id"] for t in payload["tasks"]}
    goals = {g["goal_id"] for g in payload["goals"]}
    return all(i["task_id"] in tasks and (i["goal_id"] is None or i["goal_id"] in goals) for i in items)


def covered(items: list[dict], payload: dict) -> bool:
    got = [i["task_id"] for i in items]
    return len(got) == len(set(got)) and set(got) == {t["task_id"] for t in payload["tasks"]}


def correct_count(items: list[dict], expected: dict[str, int | None | list[int]]) -> int:
    # expected 為陣列時表示兩者皆可（例：一個任務同時沾到兩個目標）
    got = {str(i["task_id"]): i["goal_id"] for i in items}
    return sum(1 for tid, gid in expected.items()
               if tid in got and (got[tid] in gid if isinstance(gid, list) else got[tid] == gid))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(PRICES))
    ap.add_argument("--cases", default=str(ROOT / "scripts" / "eval_data" / "ai03_cases.json"))
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
    counts = {"格式": 0, "id合法": 0, "覆蓋": 0}
    hit, total, longest = 0, 0, 0
    rows = []
    for case in cases:
        if spent >= args.max_cost:
            print(f"已達費用上限 ${args.max_cost}，停止")
            break
        payload, expected = formal_payload(case["payload"]), case["expected"]
        ai.last_usage = (0, 0)
        started = time.monotonic()
        raw, items, error = [], [], ""
        try:
            output = ai.call("AI-03", payload, timeout_s=DEFAULT_TIMEOUT_S)
            raw = output["items"]
            items = parse_output(output, payload)
        except AIError as exc:
            error = type(exc).__name__
        latency = time.monotonic() - started
        tin, tout = ai.last_usage
        tin_sum, tout_sum = tin_sum + tin, tout_sum + tout
        spent += cost(args.model, tin, tout)
        ok = {"格式": not error}
        ok["id合法"] = ok["格式"] and ids_valid(raw, payload)
        ok["覆蓋"] = ok["格式"] and covered(items, payload)
        for k, v in ok.items():
            counts[k] += v
        n_hit = correct_count(items, expected)
        hit, total = hit + n_hit, total + len(expected)
        reason_max = max((len(i["reason"]) for i in items), default=0)
        longest = max(longest, reason_max)
        print(f"  {case['id']}：" + "、".join(f"{k}{'✓' if v else '✗'}" for k, v in ok.items())
              + f"；準確 {n_hit}/{len(expected)}；reason 最長 {reason_max} 字"
              + f"；{latency:.1f} 秒；token {tin:,}／{tout:,}"
              + (f"；{error}" if error else ""))
        rows.append({"id": case["id"], "分類": case["category"], **{k: "Y" if v else "N" for k, v in ok.items()},
                     "準確": f"{n_hit}/{len(expected)}", "錯誤": error, "延遲秒": f"{latency:.1f}",
                     "輸入token": tin, "輸出token": tout, "items": json.dumps(raw, ensure_ascii=False),
                     "expected": json.dumps(expected, ensure_ascii=False), "檢視判定": "", "備註": ""})

    n = len(rows)
    print("\n" + "、".join(f"{k} {v}/{n}" for k, v in counts.items())
          + (f"；準確率 {hit}/{total}（{hit / total:.0%}，參考門檻 70%）" if total else ""))
    if rows:
        slowest = max(float(r["延遲秒"]) for r in rows)
        print(f"最慢 {slowest:.1f} 秒（逾時 {DEFAULT_TIMEOUT_S} 秒；SDD 驗收要低於 15 秒）")
        print(f"reason 最長 {longest} 字（上限 200）")
    print(f"token：輸入 {tin_sum:,}、輸出 {tout_sum:,}；費用約 ${spent:.4f}")
    out_dir = os.environ.get("EVAL_OUT_DIR")
    if out_dir and rows:
        path = Path(out_dir) / f"{time.strftime('%Y%m%d-%H%M')}_AI-03_{args.model}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:   # BOM：Excel 開中文不亂碼
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n逐案結果：{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
