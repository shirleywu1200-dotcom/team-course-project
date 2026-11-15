"""把 OpenAPI 文件輸出到標準輸出，不需要啟動伺服器或連線資料庫。

用法（在 backend/ 下）：uv run python -m app.export_openapi > ../frontend/openapi.json
給前端由 OpenAPI 產生型別使用（todo 0.8）。
"""

import json

from app.config import Settings
from app.db.database import Database
from app.main import create_app


def build_openapi() -> dict:
    # 只組出路由，不連資料庫：引擎是惰性連線，這裡不會真的連線
    settings = Settings(database_url="postgresql+psycopg://unused@127.0.0.1/unused", api_token="unused",  # noqa: S106 匯出用的假值，不會啟動伺服器
                        bind_host="127.0.0.1", port=0)
    return create_app(settings, db=Database(settings.database_url)).openapi()


if __name__ == "__main__":
    print(json.dumps(build_openapi(), ensure_ascii=False, indent=2))
