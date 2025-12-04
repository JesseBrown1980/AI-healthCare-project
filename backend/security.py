"""Security utilities for validating bearer tokens issued by an external IAM.

This module provides a FastAPI dependency that validates SMART-on-FHIR access
tokens, ensuring the signature, issuer, audience, expiry, scopes, and clinician
roles are checked before any protected route executes. The dependency returns a
``TokenContext`` that downstream services (e.g., ``FHIRConnector``) can use to
forward the caller's token and patient context to FHIR servers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional, Set

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode


bearer_scheme = HTTPBearer(auto_error=False)


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

    def __init__(self) -> None:
        self.jwks_url = os.getenv("IAM_JWKS_URL")
        self.issuer = os.getenv("IAM_ISSUER")
        self.audience = os.getenv("SMART_CLIENT_ID") or os.getenv("IAM_AUDIENCE")
        self._jwks_cache: Optional[Dict[str, Dict]] = None

    def _fetch_jwks(self) -> Dict[str, Dict]:
        if not self.jwks_url:
            raise RuntimeError("IAM_JWKS_URL must be configured for token validation")

        if self._jwks_cache:
            return self._jwks_cache

        with httpx.Client(timeout=10.0) as client:
            response = client.get(self.jwks_url)
            response.raise_for_status()
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

    def validate(self, token: str) -> TokenContext:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Malformed token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        jwks = self._fetch_jwks()
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


def auth_dependency(
    required_scopes: Optional[Iterable[str]] = None,
    required_roles: Optional[Iterable[str]] = None,
):
    """Create a FastAPI dependency that validates bearer tokens and scopes."""

    def _normalize_scopes(scopes: Set[str]) -> Set[str]:
        """Include wildcard equivalents for resource-specific SMART scopes.

        This allows a required scope such as ``patient/*.read`` to be satisfied by a
        token that only carries resource-specific scopes like
        ``patient/Observation.read`` while leaving downstream resource validation to
        the FHIR connector.
        """

        normalized = set(scopes)
        for scope in scopes:
            if "/" in scope and "." in scope:
                try:
                    context, access = scope.split("/", 1)
                    resource, permission = access.split(".", 1)
                except ValueError:
                    continue

                wildcard = f"{context}/*.{permission}"
                normalized.add(wildcard)

                if permission.startswith("r"):
                    normalized.add(f"{context}/*.read")
                if permission.startswith("w"):
                    normalized.add(f"{context}/*.write")

        return normalized

    async def _dependency(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) -> TokenContext:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        validator = JWTValidator()
        token_context = validator.validate(credentials.credentials)

        scopes_set = set(required_scopes or [])
        if scopes_set:
            normalized_scopes = _normalize_scopes(token_context.scopes)
            if not normalized_scopes.intersection(scopes_set):
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
