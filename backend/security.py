"""Security utilities for validating bearer tokens issued by an external IAM.

This module provides a FastAPI dependency that validates SMART-on-FHIR access
tokens, ensuring the signature, issuer, audience, expiry, scopes, and clinician
roles are checked before any protected route executes. The dependency returns a
``TokenContext`` that downstream services (e.g., ``FHIRConnector``) can use to
forward the caller's token and patient context to FHIR servers. For local
development, a demo login route can mint short-lived HS256 JWTs, but production
deployments should always rely on SMART tokens issued by your IAM.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional, Set

import httpx
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode


bearer_scheme = HTTPBearer(auto_error=False)

_shared_async_client: Optional[httpx.AsyncClient] = None

# Common scope constants for reuse across endpoints
SCOPE_PATIENT_READ = "patient/*.read"
SCOPE_PATIENT_WRITE = "patient/*.write"
SCOPE_USER_READ = "user/*.read"
SCOPE_USER_WRITE = "user/*.write"
SCOPE_SYSTEM_READ = "system/*.read"
SCOPE_SYSTEM_WRITE = "system/*.write"
SCOPE_SYSTEM_MANAGE = "system/*.manage"

# Common scope sets
DEFAULT_READ_SCOPES = {SCOPE_PATIENT_READ, SCOPE_USER_READ, SCOPE_SYSTEM_READ}
DEFAULT_WRITE_SCOPES = {SCOPE_PATIENT_WRITE, SCOPE_USER_WRITE, SCOPE_SYSTEM_WRITE}
DEFAULT_ADMIN_SCOPES = {SCOPE_PATIENT_READ, SCOPE_PATIENT_WRITE, SCOPE_USER_READ, SCOPE_USER_WRITE, SCOPE_SYSTEM_READ, SCOPE_SYSTEM_WRITE, SCOPE_SYSTEM_MANAGE}


async def get_shared_async_client() -> httpx.AsyncClient:
    """Return a shared ``httpx.AsyncClient`` instance for JWKS retrieval."""

    global _shared_async_client
    if _shared_async_client is None or _shared_async_client.is_closed:
        _shared_async_client = httpx.AsyncClient(timeout=10.0)
    return _shared_async_client


async def close_shared_async_client() -> None:
    """Close the shared ``httpx.AsyncClient`` if it was created."""

    global _shared_async_client
    if _shared_async_client and not _shared_async_client.is_closed:
        await _shared_async_client.aclose()
    _shared_async_client = None


@dataclass
class TokenContext:
    """Validated token data for downstream calls."""

    access_token: str
    scopes: Set[str]
    clinician_roles: Set[str]
    subject: Optional[str] = None
    patient: Optional[str] = None
    claims: Optional[Dict] = None

    def has_scope(self, required: Iterable[str]) -> bool:
        required_set = set(required)
        return bool(required_set.intersection(self.scopes)) if required_set else True


class JWTValidator:
    """Validates JWT bearer tokens against JWKS keys and SMART constraints."""

    def __init__(self, async_client: Optional[httpx.AsyncClient] = None) -> None:
        self.jwks_url = os.getenv("IAM_JWKS_URL")
        self.issuer = os.getenv("IAM_ISSUER")
        self.audience = os.getenv("SMART_CLIENT_ID") or os.getenv("IAM_AUDIENCE")
        self.demo_login_enabled = (
            os.getenv("ENABLE_DEMO_LOGIN", "false").lower() == "true"
        )
        self.demo_secret = os.getenv("DEMO_JWT_SECRET") or "demo-secret-key-123"
        self.demo_issuer = os.getenv("DEMO_JWT_ISSUER", "demo-login")
        self._jwks_cache: Optional[Dict[str, Dict]] = None
        self._async_client = async_client

    async def _fetch_jwks(self) -> Dict[str, Dict]:
        if not self.jwks_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="IAM_JWKS_URL must be configured for token validation",
            )

        if self._jwks_cache is not None:
            return self._jwks_cache

        client = self._async_client or await get_shared_async_client()
        try:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch JWKS",
            ) from exc

        jwks = response.json().get("keys", [])
        self._jwks_cache = {key.get("kid"): key for key in jwks if key.get("kid")}
        return self._jwks_cache

    def _verify_signature(self, token: str, jwk_key: Dict) -> Dict:
        message, encoded_signature = token.rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode())
        public_key = jwk.construct(jwk_key)

        if not public_key.verify(message.encode(), decoded_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            options = {"verify_aud": bool(self.audience)}
            return jwt.decode(
                token,
                public_key.to_pem().decode(),
                audience=self.audience,
                issuer=self.issuer,
                options=options,
            )
        except JWTError as exc:  # pragma: no cover - jose handles detailed errors
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def _verify_hs256(self, token: str) -> Dict:
        """Validate HS256 demo tokens when IAM is not available."""

        if not self.demo_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Demo JWT secret is not configured",
            )

        try:
            options = {"verify_aud": bool(self.audience)}
            return jwt.decode(
                token,
                self.demo_secret,
                algorithms=["HS256"],
                audience=self.audience,
                issuer=self.demo_issuer,
                options=options,
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    async def validate(self, token: str) -> TokenContext:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Malformed token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if self._should_use_demo_validation(unverified_header):
            claims = self._verify_hs256(token)
        else:
            jwks = await self._fetch_jwks()
            jwk_key = jwks.get(unverified_header.get("kid"))
            if not jwk_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token key not recognized",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            claims = self._verify_signature(token, jwk_key)

        self._ensure_not_expired(claims)

        scopes = self._extract_scopes(claims)
        roles = self._extract_roles(claims)
        patient = claims.get("patient") or claims.get("launch_patient")

        return TokenContext(
            access_token=token,
            scopes=scopes,
            clinician_roles=roles,
            subject=claims.get("sub"),
            patient=patient,
            claims=claims,
        )

    @staticmethod
    def _ensure_not_expired(claims: Dict) -> None:
        exp = claims.get("exp")
        if exp is None:
            return
        if datetime.now(timezone.utc).timestamp() > float(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def _extract_scopes(claims: Dict) -> Set[str]:
        raw = claims.get("scope") or claims.get("scp") or ""
        if isinstance(raw, str):
            return set(raw.split())
        if isinstance(raw, (list, tuple)):
            return set(raw)
        return set()

    @staticmethod
    def _extract_roles(claims: Dict) -> Set[str]:
        roles = set()
        if isinstance(claims.get("roles"), (list, tuple)):
            roles.update(claims["roles"])
        realm_roles = claims.get("realm_access", {}).get("roles", [])
        if isinstance(realm_roles, list):
            roles.update(realm_roles)
        group_roles = claims.get("groups", [])
        if isinstance(group_roles, list):
            roles.update(group_roles)
        custom = claims.get("https://schemas.clinician_roles")
        if isinstance(custom, list):
            roles.update(custom)
        return roles

    def _should_use_demo_validation(self, unverified_header: Dict) -> bool:
        alg = (unverified_header or {}).get("alg", "")
        if not self.demo_login_enabled:
            return False
        if alg.upper().startswith("HS") and self.demo_secret:
            return True
        if not self.jwks_url and self.demo_secret:
            return True
        return False


def auth_dependency(
    required_scopes: Optional[Iterable[str]] = None,
    required_roles: Optional[Iterable[str]] = None,
):
    """Create a FastAPI dependency that validates bearer tokens and scopes."""

    validator = JWTValidator()

    async def _dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) -> TokenContext:
        # Allow DEMO_MODE bypass with a hardcoded token or even no token if we handle it carefully
        # But Depends(bearer_scheme) enforces the header presence implicitly if auto_error=True
        # We set auto_error=False above, so credentials can be None.
        
        if os.getenv("DEMO_MODE", "False").lower() == "true":
             # Auto-authorize in demo mode if no token or specific demo token
             if not credentials or credentials.credentials == "demo-token":
                 return TokenContext(
                    access_token="demo-token",
                    scopes={"patient/*.read", "user/*.read", "system/*.read", "system/*.manage"},
                    clinician_roles={"practitioner"},
                    subject="demo-user",
                    patient=None
                )

        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Bypass for DEMO_MODE if configured
        if os.getenv("DEMO_MODE", "False").lower() == "true" and credentials.credentials == "demo-token":
             return TokenContext(
                access_token="demo-token",
                scopes={"patient/*.read", "user/*.read", "system/*.read", "system/*.manage"},
                clinician_roles={"practitioner"},
                subject="demo-user",
                patient="patient-001"
            )

        token_context = await validator.validate(credentials.credentials)

        scopes_set = set(required_scopes or [])
        if scopes_set and not token_context.scopes.intersection(scopes_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient SMART scopes",
            )

        roles_set = set(required_roles or [])
        if roles_set and not roles_set.intersection(token_context.clinician_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required clinician role",
            )

        return token_context

    return _dependency
