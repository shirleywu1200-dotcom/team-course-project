"""Phase 0：錯誤格式、token、冪等、AI 假實作、健康檢查。"""

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.ai.client import AIInvalidOutput, AITimeout, AIUnavailable, FakeAIClient
from app.errors import ERROR_STATUS, DomainError
from tests.unit.seeds import BASE


@pytest.mark.parametrize("code", sorted(ERROR_STATUS))
def test_every_domain_error_has_uniform_format(app, client, code):
    router = APIRouter()

    @router.get(f"/api/v1/_raise/{code}")
    def boom():
        raise DomainError(code, details={"x": 1})

    app.include_router(router)
    r = client.get(f"/api/v1/_raise/{code}")
    assert r.status_code == ERROR_STATUS[code]
    body = r.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["error"]["details"] == {"x": 1}


def test_unregistered_error_code_is_rejected():
    with pytest.raises(ValueError):
        DomainError("NOT_A_CODE")


def test_missing_or_wrong_token_is_401(app):
    with TestClient(app) as anon:
        assert anon.get("/api/v1/meta/health").json()["error"]["code"] == "UNAUTHORIZED"
    with TestClient(app, headers={"Authorization": "Bearer wrong"}) as bad:
        assert bad.get("/api/v1/meta/health").status_code == 401


def test_unknown_path_is_not_found_format(client):
    r = client.get("/api/v1/no-such-thing")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_validation_error_lists_fields_without_echoing_input(client):
    r = client.post("/api/v1/tasks", json={"title": "祕密內容", "due": "not-a-date"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR" and "due" in err["details"]["fields"]
    assert "祕密內容" not in r.text and "not-a-date" not in r.text


def test_unexpected_exception_returns_internal_error_without_detail(app, db):
    router = APIRouter()

    @router.get("/api/v1/_crash")
    def crash():
        raise RuntimeError("內部祕密")

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False, headers={"Authorization": "Bearer test-token"}) as c:
        r = c.get("/api/v1/_crash")
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "內部祕密" not in r.text


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_public_api_docs_are_disabled(app, path):
    with TestClient(app) as anon:
        r = anon.get(path)
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_openapi_requires_token(app, client):
    with TestClient(app) as anon:
        assert anon.get("/api/v1/openapi.json").status_code == 401
    spec = client.get("/api/v1/openapi.json").json()
    assert "/api/v1/tasks/{task_id}/adjust-due" in spec["paths"]


def test_export_openapi_without_server():
    from app.export_openapi import build_openapi
    assert "/api/v1/projects/{project_id}/bulk-shift/commit" in build_openapi()["paths"]


def test_sqlalchemy_hides_parameters(db):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError) as e:
        db.run(lambda c: c.execute(text("SELECT CAST(:v AS integer)"), {"v": "abc"}))
    assert db.engine.hide_parameters is True
    assert "SQL parameters hidden" in str(e.value)


def test_db_error_content_never_reaches_logs_or_response(app, db, caplog):
    """CLAUDE.md 資安 3：PostgreSQL 的錯誤訊息會引用輸入值，這類例外不可往外拋進 uvicorn 的 traceback。"""
    import logging

    from sqlalchemy import text
    secret = "使用者的機密備註-XYZ"
    router = APIRouter()

    @router.get("/api/v1/_dberror")
    def dberror():
        db.run(lambda c: c.execute(text("SELECT CAST(:v AS integer)"), {"v": secret}))

    app.include_router(router)
    caplog.set_level(logging.DEBUG)
    # raise_server_exceptions=True：若例外仍往外拋，這裡會直接失敗
    with TestClient(app, headers={"Authorization": "Bearer test-token"}) as c:
        r = c.get("/api/v1/_dberror")
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert secret not in r.text
    assert secret not in caplog.text and "DataError" in caplog.text


def test_health_reports_db_and_ai(client, ai):
    assert client.get("/api/v1/meta/health").json() == {"db": "ok", "ai": "ok"}
    ai.available = False
    assert client.get("/api/v1/meta/health").json()["ai"] == "unavailable"


def test_idempotency_key_replays_first_result(client, seed, query):
    seed(BASE)
    headers = {"Idempotency-Key": "k-1"}
    body = {"title": "新任務", "due": "2026-11-20"}
    first = client.post("/api/v1/tasks", json=body, headers=headers)
    second = client.post("/api/v1/tasks", json=body, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert second.headers.get("Idempotent-Replay") == "true"
    assert len(query("SELECT id FROM tasks WHERE title = '新任務'")) == 1


def test_idempotency_key_expires_after_24_hours(client, seed, query, clock):
    from datetime import timedelta
    seed(BASE)
    body = {"title": "新任務", "due": "2026-11-20"}
    client.post("/api/v1/tasks", json=body, headers={"Idempotency-Key": "k-2"})
    clock.set(clock.now() + timedelta(hours=25))
    client.post("/api/v1/tasks", json=body, headers={"Idempotency-Key": "k-2"})
    assert len(query("SELECT id FROM tasks WHERE title = '新任務'")) == 2


def test_idempotency_rows_older_than_24_hours_are_purged(client, seed, query, clock):
    from datetime import timedelta
    seed(BASE)
    client.post("/api/v1/tasks", json={"title": "a", "due": "2026-11-20"}, headers={"Idempotency-Key": "old"})
    clock.set(clock.now() + timedelta(hours=25))
    client.post("/api/v1/tasks", json={"title": "b", "due": "2026-11-20"}, headers={"Idempotency-Key": "new"})
    assert [r["key"] for r in query("SELECT key FROM idempotency_keys")] == ["new"]


def test_idempotency_key_reused_on_other_endpoint_is_rejected(client, seed):
    seed(BASE)
    client.post("/api/v1/tasks", json={"title": "a", "due": "2026-11-20"}, headers={"Idempotency-Key": "k-3"})
    r = client.post("/api/v1/projects", json={"name": "p"}, headers={"Idempotency-Key": "k-3"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_fake_ai_client_scripted_outputs_and_failures():
    ai = FakeAIClient()
    ai.script("AI-01", {"candidates": []}, AITimeout, AIInvalidOutput("AI-01"))
    assert ai.call("AI-01", {"text": "x"}) == {"candidates": []}
    with pytest.raises(AITimeout):
        ai.call("AI-01", {})
    with pytest.raises(AIInvalidOutput):
        ai.call("AI-01", {})
    with pytest.raises(AIUnavailable):
        ai.call("AI-01", {})
    assert [c[0] for c in ai.calls] == ["AI-01"] * 4


def test_fixed_clock_controls_today(clock):
    from datetime import date

    from app.clock import get_clock
    assert get_clock().today() == date(2026, 11, 11)
    assert get_clock().now().utcoffset().total_seconds() == 8 * 3600
