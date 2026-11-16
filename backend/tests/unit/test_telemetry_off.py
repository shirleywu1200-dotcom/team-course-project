"""內建遙測必須關閉（CLAUDE.md 資安規則 2：不新增遙測等對外管道）。

FastAPI 0.162 起內建 OpenTelemetry，預設開啟：程序裡一有全域 provider（例如日後裝了
opentelemetry-sdk 或開了 auto-configure），請求路徑、驗證失敗的輸入值與例外內容就會交給 exporter。

行為測試：在子程序裡掛上會記錄的全域 tracer／logger provider（模擬「有人裝了 SDK」），
打幾個請求，斷言沒有任何 span 或 log 紀錄被建立。全域 provider 一個程序只能設定一次，
所以放在子程序，不影響其他測試。
"""

import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

SCRIPT = r"""
import json
from opentelemetry import trace
from opentelemetry import _logs as logs
from opentelemetry.trace import NoOpTracer, TracerProvider
from opentelemetry._logs import LoggerProvider, NoOpLogger

calls = []

class RecTracer(NoOpTracer):
    def start_span(self, name, *a, **k):
        calls.append(("span", name))
        return super().start_span(name, *a, **k)
    def start_as_current_span(self, name, *a, **k):
        calls.append(("span", name))
        return super().start_as_current_span(name, *a, **k)

class RecTracerProvider(TracerProvider):   # 不能繼承 NoOp*：FastAPI 會當成沒設定而跳過
    def get_tracer(self, *a, **k):
        return RecTracer()

class RecLogger(NoOpLogger):
    def emit(self, *a, **k):
        calls.append(("log", None))

class RecLoggerProvider(LoggerProvider):
    def get_logger(self, *a, **k):
        return RecLogger(*a[:1])

trace.set_tracer_provider(RecTracerProvider())
logs.set_logger_provider(RecLoggerProvider())

from fastapi.testclient import TestClient
from app.config import Settings
from app.db.database import Database
from app.main import create_app

settings = Settings(database_url="postgresql+psycopg://u@127.0.0.1:1/none", api_token="t",
                    bind_host="127.0.0.1", port=0)
app = create_app(settings, db=Database(settings.database_url))
with TestClient(app) as c:
    c.get("/api/v1/tasks")                                   # 401：沒有 token
    c.post("/api/v1/tasks", headers={"Authorization": "Bearer t"},
           json={"title": "機密標記XYZ"})                   # 422：驗證失敗（含輸入值）
    c.get("/api/v1/not-here", headers={"Authorization": "Bearer t"})   # 404
print(json.dumps(calls))
"""


def test_builtin_telemetry_records_nothing_even_with_global_providers():
    # 執行的是本檔固定的腳本與目前的直譯器，沒有外部輸入
    out = subprocess.run([sys.executable, "-c", SCRIPT], cwd=BACKEND_DIR, capture_output=True,  # noqa: S603
                         text=True, timeout=60, check=True)
    calls = json.loads(out.stdout.strip().splitlines()[-1])
    assert calls == []
