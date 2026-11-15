"""全域中介層：未預期例外（最外層）、Bearer token 驗證（todo 0.4）、Idempotency-Key（todo 0.5）。

執行順序：先攔例外，再驗 token，最後處理冪等，所以未授權的請求拿不到重送結果。
"""

import hmac
import json
import logging
from datetime import timedelta

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.clock import get_clock
from app.db.repo import misc_repo
from app.errors import DomainError

log = logging.getLogger("g4")

API_PREFIX = "/api/v1"
IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH"}
IDEMPOTENCY_TTL = timedelta(hours=24)
# 回應含全部原文，不能存進快取，否則多一份要清除的副本（Phase 8 SDD 第 6 節）
NO_CACHE_PATHS = {f"{API_PREFIX}/export"}


def _error(code: str, message: str | None = None) -> JSONResponse:
    err = DomainError(code, message)
    return JSONResponse(err.to_body(), status_code=err.status)


class UnhandledErrorMiddleware(BaseHTTPMiddleware):
    """攔下所有未預期的例外：只記錄例外類型，回 500 INTERNAL_ERROR，不再往外拋。

    例外訊息可能含使用者內容（例如 PostgreSQL 的錯誤訊息會引用輸入值），
    往外拋會讓 uvicorn 把完整 traceback 寫進 log（CLAUDE.md 資安 3）。
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 最外層統一處理，避免例外內容進 log
            log.error("unhandled error: %s", type(exc).__name__)
            return _error("INTERNAL_ERROR")


class BearerTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(API_PREFIX):
            expected = request.app.state.settings.api_token
            header = request.headers.get("Authorization", "")
            given = header[7:] if header.startswith("Bearer ") else ""
            if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
                return _error("UNAUTHORIZED")
        return await call_next(request)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("Idempotency-Key")
        path = request.url.path
        if not key or request.method not in IDEMPOTENT_METHODS or not path.startswith(API_PREFIX) \
                or path in NO_CACHE_PATHS:
            return await call_next(request)
        db = request.app.state.db
        endpoint = f"{request.method} {request.url.path}"
        since = get_clock().now() - IDEMPOTENCY_TTL
        found = await run_in_threadpool(db.run, lambda c: misc_repo.get_idempotency(c, key, since))
        if found is not None:
            if found["endpoint"] != endpoint:
                return _error("VALIDATION_ERROR", "Idempotency-Key 已用於其他端點")
            stored = found["response"]
            return JSONResponse(stored["body"], status_code=stored["status"], headers={"Idempotent-Replay": "true"})

        response = await call_next(request)
        if response.status_code >= 500:
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = None
        if parsed is not None:
            record = {"status": response.status_code, "body": parsed}
            await run_in_threadpool(db.run, lambda c: misc_repo.save_idempotency(
                c, key, endpoint, record, get_clock().now(), since))
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return Response(body, status_code=response.status_code, headers=headers, media_type=response.media_type)
