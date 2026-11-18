"""AI-04 評估：用評估案例呼叫真實供應商，算出格式、R3 第 1 點與第 2 點通過率、延遲與費用
（docs/dev-b/ai-03-04-sdd.md 第 5 節）。

會產生費用。執行前先印估算並等你輸入 y；累計費用超過 --max-cost 就停止。
終端機只印案例 id 與統計。設了環境變數 EVAL_OUT_DIR（放 env/local.env）時，另存逐案 CSV
（含 draft、figures、不在允許名單的數字，以及空白的「檢視判定」欄：R3 失敗逐筆填「真錯」或「誤判」）。

R3 對帳是暫用版（SDD Q1-A）：依 spec 5.3a 寫在這裡，只供評估用。Dev-A 的正式函式合併後，
改 import 正式函式、刪掉本檔的 r3_rule1／r3_rule2，再重跑一輪當基準線。

用法（需 env/local.env 有 ANTHROPIC_API_KEY）：
    cd backend
    PYTHONUTF8=1 .venv/Scripts/python ../scripts/eval_ai04.py --model claude-sonnet-5-5
    選項：--cases 檔案（預設 scripts/eval_data/ai04_cases.json）、--only null_judgement（只跑指定 id）、
    --max-cost 0.3（美元）
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.anthropic_client import AnthropicAIClient  # noqa: E402
from app.ai.client import DEFAULT_TIMEOUT_S, AIError  # noqa: E402
from app.config import DEFAULT_ENV_FILE, load_env_file  # noqa: E402

PRICES = {   # 美元／百萬 token（輸入, 輸出），2026-11 公告價
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
EST_IN, EST_OUT = 1500, 1200   # 單次估算（SDD 第 5 節），取寬
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def cost(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICES[model]
    return (tin * pin + tout * pout) / 1_000_000


def flat_stats(stats: dict, prefix: str = "") -> dict[str, float]:
    out = {}
    for k, v in stats.items():
        if isinstance(v, dict):
            out |= flat_stats(v, f"{prefix}{k}.")
        elif isinstance(v, int | float) and not isinstance(v, bool):
            out[prefix + k] = float(v)
    return out


def numbers(text: str) -> list[float]:
    # 正規化：全形轉半形（NFKC）；4.0＝4（以 float 比）；100% 只取 100
    return [float(n) for n in NUMBER.findall(unicodedata.normalize("NFKC", text))]


def allowed(payload: dict) -> set[float]:
    texts = [payload["goal"]["title"], payload["goal"]["period"]] + [t["title"] for t in payload["tasks"]]
    names = set(flat_stats(payload["stats"]).values())
    names |= {n for t in texts for n in numbers(t)}
    names |= {float(p) for t in payload["tasks"] for p in t["done_date"].split("-")}
    return names


def r3_rule1(figures: list[dict], payload: dict) -> bool:
    stats = flat_stats(payload["stats"])
    return all(f["key"] in stats and stats[f["key"]] == float(f["value"]) for f in figures)


def r3_rule2_misses(draft: str, payload: dict) -> list[float]:
    ok = allowed(payload)
    return [n for n in numbers(draft) if n not in ok]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(PRICES))
    ap.add_argument("--cases", default=str(ROOT / "scripts" / "eval_data" / "ai04_cases.json"))
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
    counts = {"格式": 0, "R3-1": 0, "R3-2": 0}
    rows = []
    for case in cases:
        if spent >= args.max_cost:
            print(f"已達費用上限 ${args.max_cost}，停止")
            break
        payload = case["payload"]
        ai.last_usage = (0, 0)
        started = time.monotonic()
        draft, figures, error = "", [], ""
        try:
            out = ai.call("AI-04", payload, timeout_s=DEFAULT_TIMEOUT_S)
            draft, figures = out["draft"], out["figures"]
        except AIError as exc:
            error = type(exc).__name__
        latency = time.monotonic() - started
        tin, tout = ai.last_usage
        tin_sum, tout_sum = tin_sum + tin, tout_sum + tout
        spent += cost(args.model, tin, tout)
        misses = r3_rule2_misses(draft, payload) if not error else []
        ok = {"格式": not error and bool(draft.strip())}
        ok["R3-1"] = ok["格式"] and r3_rule1(figures, payload)
        ok["R3-2"] = ok["格式"] and not misses
        for k, v in ok.items():
            counts[k] += v
        print(f"  {case['id']}：" + "、".join(f"{k}{'✓' if v else '✗'}" for k, v in ok.items())
              + f"；{latency:.1f} 秒；token {tin:,}／{tout:,}" + (f"；{error}" if error else ""))
        rows.append({"id": case["id"], "分類": case["category"], **{k: "Y" if v else "N" for k, v in ok.items()},
                     "名單外數字": " ".join(f"{n:g}" for n in misses), "錯誤": error, "延遲秒": f"{latency:.1f}",
                     "輸入token": tin, "輸出token": tout, "draft": draft,
                     "figures": json.dumps(figures, ensure_ascii=False), "檢視判定": "", "備註": ""})

    n = len(rows)
    print("\n" + "、".join(f"{k} {v}/{n}" for k, v in counts.items())
          + "（R3 失敗請在 CSV「檢視判定」逐筆填真錯／誤判）")
    if rows:
        slowest = max(float(r["延遲秒"]) for r in rows)
        print(f"最慢 {slowest:.1f} 秒（逾時 {DEFAULT_TIMEOUT_S} 秒；SDD 驗收要低於 15 秒）")
    print(f"token：輸入 {tin_sum:,}、輸出 {tout_sum:,}；費用約 ${spent:.4f}")
    out_dir = os.environ.get("EVAL_OUT_DIR")
    if out_dir and rows:
        path = Path(out_dir) / f"{time.strftime('%Y%m%d-%H%M')}_AI-04_{args.model}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:   # BOM：Excel 開中文不亂碼
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n逐案結果：{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
