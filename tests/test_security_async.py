from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt

from backend.security import JWTValidator, TokenContext, auth_dependency


@pytest.mark.asyncio
async def test_auth_dependency_uses_async_jwks(monkeypatch):
    jwks_url = "https://example.com/jwks"
    monkeypatch.setenv("IAM_JWKS_URL", jwks_url)
    monkeypatch.setenv("IAM_ISSUER", "https://issuer.example.com")
    monkeypatch.setenv("SMART_CLIENT_ID", "client-id")

    jwks_calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal jwks_calls
        jwks_calls += 1
        return httpx.Response(200, json={"keys": [{"kid": "kid-1"}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as async_client:
        original_init = JWTValidator.__init__

        def init_with_client(self):
            original_init(self)
            self._async_client = async_client

        monkeypatch.setattr(JWTValidator, "__init__", init_with_client)
        monkeypatch.setattr(
            JWTValidator,
            "_verify_signature",
            lambda self, token, jwk_key: {
                "scope": "user/*.read",
                "sub": "test-user",
                "exp": (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp(),
            },
        )

        dependency = auth_dependency(required_scopes={"user/*.read"})

        app = FastAPI()

        @app.get("/protected")
        async def protected(context: TokenContext = Depends(dependency)):
            return {"subject": context.subject, "scopes": sorted(context.scopes)}

        token = jwt.encode({"sub": "test-user"}, "secret", algorithm="HS256", headers={"kid": "kid-1"})

        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        assert response.json() == {
            "subject": "test-user",
            "scopes": ["user/*.read"],
        }
        assert jwks_calls == 1
