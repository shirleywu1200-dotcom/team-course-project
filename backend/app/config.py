"""執行設定：全部從環境變數讀取。

`env/local.env`（若存在）會先載入，但不覆蓋已存在的環境變數。
祕密（token、資料庫密碼）只放 `env/local.env`，該檔不進版控。
"""

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / "env" / "local.env"
IDEMPOTENCY_TTL = timedelta(hours=24)


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_token: str
    bind_host: str
    port: int
    ai_provider: str = "off"           # off 或 anthropic（13.4 SDD D-4）
    ai_model: str = "claude-sonnet-5-5"
    anthropic_api_key: str = ""


def load_settings() -> Settings:
    load_env_file(Path(os.environ.get("G4_ENV_FILE", DEFAULT_ENV_FILE)))
    return Settings(
        database_url=os.environ.get("G4_DATABASE_URL", ""),
        api_token=os.environ.get("G4_API_TOKEN", ""),
        bind_host=os.environ.get("G4_BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("G4_PORT", "8000")),
        ai_provider=os.environ.get("AI_PROVIDER", "off"),
        ai_model=os.environ.get("AI_MODEL", "claude-sonnet-5-5"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
