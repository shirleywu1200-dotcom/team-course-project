"""API 回應快照：改回應模型或序列化前後，錄下測試中的實際 2xx 回應並逐筆比對。

用途：補 `response_model` 時，模型漏寫的欄位會被 FastAPI 靜默濾掉；用前後快照確認回應內容不變。

錄製（當 pytest 外掛載入；RESP_LOG 指定輸出檔，RESP_PATHS 可用逗號分隔的正規式限定路徑，預設全錄）：
    cd backend
    export RESP_LOG=/tmp/before.jsonl PYTHONPATH=../scripts PYTHONUTF8=1
    .venv/Scripts/python -m pytest -p resp_snapshot tests/unit
    （改程式後同樣錄一份 after.jsonl）
    Git Bash 會把開頭是 / 的環境變數值轉成 Windows 路徑；設 RESP_PATHS 時前面加 MSYS_NO_PATHCONV=1。
比對：
    python ../scripts/resp_snapshot.py /tmp/before.jsonl /tmp/after.jsonl
    帶小數秒的時間戳（種子遷移 now() 的真實時間）會先遮掉；鍵順序不同只計數，不算內容差異。
"""

import json
import os
import re
import sys

_REAL_TS = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+[+-]\d\d:\d\d")

if "RESP_LOG" in os.environ:   # 當 pytest 外掛載入
    import httpx
    from starlette.testclient import TestClient

    _patterns = [re.compile(p) for p in os.environ.get("RESP_PATHS", "").split(",") if p]
    _orig = TestClient.request

    def _request(self, method, url, *args, **kwargs):
        resp = _orig(self, method, url, *args, **kwargs)
        path = httpx.URL(str(url)).path
        if 200 <= resp.status_code < 300 and (not _patterns or any(p.fullmatch(path) for p in _patterns)):
            with open(os.environ["RESP_LOG"], "a", encoding="utf-8") as f:
                f.write(json.dumps({"test": os.environ.get("PYTEST_CURRENT_TEST", "").split(" ")[0],
                                    "method": method.upper(), "path": path, "status": resp.status_code,
                                    "body": resp.content.decode("utf-8")}, ensure_ascii=False) + "\n")
        return resp

    TestClient.request = _request


def compare(before_path: str, after_path: str) -> int:
    def load(p):
        with open(p, encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    before, after = load(before_path), load(after_path)
    if len(before) != len(after):
        print(f"筆數不同：{len(before)} vs {len(after)}")
        return 1
    content_diff, order_diff = 0, 0
    for b, a in zip(before, after, strict=True):
        bb, ab = _REAL_TS.sub("<NOW>", b["body"]), _REAL_TS.sub("<NOW>", a["body"])
        same_req = (b["test"], b["method"], b["path"], b["status"]) == (a["test"], a["method"], a["path"], a["status"])
        if not same_req or json.loads(bb) != json.loads(ab):
            content_diff += 1
            print("內容不同：", b["test"], b["method"], b["path"])
        elif bb != ab:
            order_diff += 1
    print(f"共 {len(before)} 筆；內容不同 {content_diff}；僅鍵順序不同 {order_diff}")
    return 1 if content_diff else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(compare(sys.argv[1], sys.argv[2]))
