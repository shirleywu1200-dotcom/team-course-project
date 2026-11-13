"""FastAPI 應用程式組裝。

`create_app` 只負責接線：設定、資料庫、AI 用戶端、中介層、錯誤處理、路由。
"""

from fastapi import APIRouter, FastAPI

from app.ai.client import AIClient, FakeAIClient
from app.api import error_handlers, routes_events, routes_projects, routes_tasks
from app.api.middleware import API_PREFIX, BearerTokenMiddleware, IdempotencyMiddleware
from app.config import Settings, load_settings
from app.db.database import Database


def create_app(settings: Settings | None = None, db: Database | None = None,
               ai: AIClient | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="個人大總管 APP", version="0.1.0")
    app.state.settings = settings
    app.state.db = db or Database(settings.database_url)
    # 真實供應商在 Phase 13.4 由 Dev-B 接入；在那之前一律用不可用的假實作，所有 AI 端點走退路。
    app.state.ai = ai or FakeAIClient(available=False)

    error_handlers.install(app)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(BearerTokenMiddleware)   # 後加的在外層，先執行

    api = APIRouter(prefix=API_PREFIX)
    for r in (routes_projects.router, routes_tasks.router, routes_events.router):
        api.include_router(r)
    app.include_router(api)
    return app


def run() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(create_app(settings), host=settings.bind_host, port=settings.port)


if __name__ == "__main__":
    run()
