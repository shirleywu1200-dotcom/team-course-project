"""路由共用的相依項。"""

from fastapi import Request

from app.ai.client import AIClient
from app.db.database import Database


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_ai(request: Request) -> AIClient:
    return request.app.state.ai
