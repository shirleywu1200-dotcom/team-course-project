"""AI-01 大量貼上延遲實測：一次真實呼叫，量 N 則訊息的延遲與輸出 token（13-4-sdd 第 4 節）。

會產生費用（150 則約 $0.075），執行前會印估算並等你輸入 y。訊息與任務全部虛構，固定亂數種子，可以重現。
直接呼叫 AnthropicAIClient（逾時 120 秒、不重試），不經過端點，不寫資料庫。
終端機只印統計（延遲、token、各 kind 數量），不印訊息內容與 key。

用法（需 env/local.env 有 ANTHROPIC_API_KEY）：
    cd backend
    PYTHONUTF8=1 .venv/Scripts/python ../scripts/probe_ai01_big_paste.py 150
13.9 試用後要重量時，可以改用真實的訊息量再跑一次，比較每則輸出 token 是否和虛構資料相近。
"""

import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_ai01 import cost  # noqa: E402  與評估腳本共用價格表

from app.ai.anthropic_client import AnthropicAIClient  # noqa: E402
from app.config import load_settings  # noqa: E402

TASKS = ["報價單", "活動海報", "場地合約", "贊助名單", "邀請函", "媒體新聞稿", "直播設備", "餐飲比價",
         "講者簡報", "報名表單", "現場動線圖", "結案報告"]
OWNERS = ["阿德", "小薇", "老周", "阿芳", "我"]
CHAT = ["大家午安", "收到", "好喔謝謝", "明天開會改到十點喔", "有人要訂便當嗎", "哈哈哈", "這週天氣好冷",
        "會議連結在群組記事本", "我晚點回電", "辛苦了！", "OK", "週五聚餐還有人要報名嗎", "了解", "👍",
        "剛剛那個檔案我再看一下", "請問印表機誰在用"]
OUT_TOKENS_PER_MSG = 40   # 2026-11-20 實測 38.5


def line(rng: random.Random) -> str:
    t, r = rng.choice(TASKS), rng.random()
    if r < 0.15:
        return f"{t}要延到 12/{rng.randint(10, 28)} 才能好"
    if r < 0.25:
        return f"{t}已經完成上傳了"
    if r < 0.30:
        return f"{t}卡住了，廠商一直沒回"
    if r < 0.35:
        return f"{t}可能會晚一點，我再確認"
    return rng.choice(CHAT)


def build_payload(n: int) -> dict:
    rng = random.Random(20261120)  # noqa: S311 產生可重現的虛構資料，不用於安全用途
    tasks = [{"id": i + 1, "title": t, "owner": rng.choice(OWNERS), "latest_due": f"2026-12-{(i % 20) + 5:02d}"}
             for i, t in enumerate(TASKS)]
    messages = [{"ref": i + 1, "speaker": rng.choice(OWNERS[:-1]), "spoken_at": f"{9 + i // 20:02d}:{i % 60:02d}",
                 "text": line(rng)} for i in range(n)]
    return {"today": "2026-11-20", "messages": messages, "tasks": tasks}


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    settings = load_settings()
    if not settings.anthropic_api_key:
        print("env/local.env 沒有 ANTHROPIC_API_KEY")
        return 1
    est = cost(settings.ai_model, 1500 + 48 * n, OUT_TOKENS_PER_MSG * n)
    if input(f"模型 {settings.ai_model}、{n} 則訊息，估計約 ${est:.3f}，確定呼叫一次？(y/N) ").strip().lower() != "y":
        return 0
    client = AnthropicAIClient(api_key=settings.anthropic_api_key, model=settings.ai_model)
    started = time.monotonic()
    result, err = None, None
    try:
        result = client.call("AI-01", build_payload(n), timeout_s=120)
    except Exception as exc:  # noqa: BLE001 量測用：只記例外類型
        err = type(exc).__name__
    sec = time.monotonic() - started
    tin, tout = client.last_usage
    print(f"訊息數={n} 延遲={sec:.1f}s 例外={err}")
    print(f"輸入token={tin} 輸出token={tout} 每則輸出≈{tout / n:.1f} 費用≈${cost(settings.ai_model, tin, tout):.3f}")
    if result:
        items = result["items"]
        print(f"items={len(items)} kinds={dict(Counter(i['kind'] for i in items))} "
              f"涵蓋 ref={len({i['ref'] for i in items})}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
