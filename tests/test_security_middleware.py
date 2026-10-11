from __future__ import annotations

import asyncio
import base64

import httpx
import pytest

from src.api import app


def _get(path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send())


def test_local_mode_sets_security_headers_without_forcing_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("APP_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("APP_AUTH_PASSWORD", raising=False)

    response = _get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_configured_basic_auth_protects_all_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_REQUIRE_AUTH", raising=False)
    monkeypatch.setenv("APP_AUTH_USERNAME", "qa-user")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "test-only-secret")

    denied = _get("/api/health")
    assert denied.status_code == 401
    assert "www-authenticate" in denied.headers
    assert denied.headers["x-content-type-options"] == "nosniff"
    assert _get("/").status_code == 401

    token = base64.b64encode(b"qa-user:test-only-secret").decode("ascii")
    allowed = _get("/api/health", {"Authorization": f"Basic {token}"})
    assert allowed.status_code == 200
    assert allowed.headers["cache-control"] == "no-store"
