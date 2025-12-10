"""Low-level FHIR HTTP client handling SMART auth, retries, and caching helpers."""

import asyncio
import base64
import hashlib
import logging
import os
import random
import secrets
import urllib.parse
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set, Tuple

import httpx

logger = logging.getLogger(__name__)


class FHIRConnectorError(Exception):
    """Custom error type for unrecoverable FHIR connector failures."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str = "fhir_connector_error",
        status_code: Optional[int] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.correlation_id = correlation_id

    def __str__(self) -> str:  # pragma: no cover - simple representation
        parts = [f"{self.error_type}: {self.message}"]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.correlation_id:
            parts.append(f"correlation_id={self.correlation_id}")
        return "; ".join(parts)


class FhirHttpClient:
    """SMART-on-FHIR aware HTTP client that handles auth and retries."""

    def __init__(
        self,
        server_url: str,
        *,
        vendor: Optional[str] = None,
        client_id: str = "",
        client_secret: str = "",
        scope: str = "system/*.read patient/*.read user/*.read",
        auth_url: Optional[str] = None,
        token_url: Optional[str] = None,
        well_known_url: Optional[str] = None,
        audience: Optional[str] = None,
        refresh_token: Optional[str] = None,
        use_proxies: bool = True,
    ) -> None:
        self.vendor = vendor.lower() if vendor else None

        vendor_server_url = server_url
        vendor_auth_url = auth_url
        vendor_token_url = token_url

        if self.vendor == "epic":
            vendor_server_url = os.getenv("EPIC_FHIR_BASE_URL", vendor_server_url)
            vendor_auth_url = os.getenv("EPIC_SMART_AUTH_URL", vendor_auth_url)
            vendor_token_url = os.getenv("EPIC_SMART_TOKEN_URL", vendor_token_url)
        elif self.vendor == "cerner":
            vendor_server_url = os.getenv("CERNER_FHIR_BASE_URL", vendor_server_url)
            vendor_auth_url = os.getenv("CERNER_SMART_AUTH_URL", vendor_auth_url)
            vendor_token_url = os.getenv("CERNER_SMART_TOKEN_URL", vendor_token_url)

        self.server_url = (vendor_server_url or server_url).rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.audience = audience
        self.refresh_token = refresh_token
        self.use_proxies = use_proxies
        self.session: Optional[httpx.AsyncClient] = None
        self.discovery_document: Dict[str, Any] = {}
        self.auth_url = vendor_auth_url
        self.token_url = vendor_token_url
        self.access_token: Optional[str] = None
        self.granted_scopes: Set[str] = set()
        self.token_expires_at: Optional[datetime] = None
        self.default_headers = {"Accept": "application/fhir+json"}
        self._request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
            "fhir_request_context", default=None
        )
        self.patient_context: Optional[str] = None
        self.user_context: Optional[str] = None
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        self.code_challenge_method: str = "S256"

        self.well_known_url = (
            well_known_url or f"{self.server_url}/.well-known/smart-configuration"
        )

        self._configure_from_well_known()
        self.session = self._initialize_session()

    @asynccontextmanager
    async def request_context(
        self,
        access_token: str,
        scopes: Set[str],
        patient_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Temporarily override the client's token and scopes for a specific request.
        """

        previous_context = self._request_context.get()
        self._request_context.set(
            {
                "access_token": access_token,
                "scopes": set(scopes or []),
                "patient": patient_id if patient_id is not None else self.patient_context,
                "user": user_id if user_id is not None else self.user_context,
            }
        )
        try:
            yield
        finally:
            self._request_context.set(previous_context)

    def _effective_context(
        self,
    ) -> Tuple[Optional[str], Set[str], Optional[str], Optional[str]]:
        """Return the active access token, scopes, patient, and user context."""

        context = self._request_context.get()
        if context:
            return (
                context.get("access_token"),
                set(context.get("scopes") or set()),
                context.get("patient") if context.get("patient") is not None else self.patient_context,
                context.get("user") if context.get("user") is not None else self.user_context,
            )
        return self.access_token, self.granted_scopes, self.patient_context, self.user_context

    def _configure_from_well_known(self) -> None:
        """Load SMART-on-FHIR metadata from the server's discovery document."""

        try:
            with httpx.Client(trust_env=self.use_proxies, timeout=10.0) as client:
                response = client.get(self.well_known_url)
                response.raise_for_status()
                self.discovery_document = response.json()
                self.auth_url = self.auth_url or self.discovery_document.get(
                    "authorization_endpoint"
                )
                self.token_url = self.token_url or self.discovery_document.get(
                    "token_endpoint"
                )
                if not self.scope:
                    self.scope = self.discovery_document.get("scopes_supported", "")
        except httpx.HTTPError as exc:
            logger.warning("SMART discovery failed at %s: %s", self.well_known_url, exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Unexpected error during SMART discovery: %s", exc)

    def _initialize_session(self) -> httpx.AsyncClient:
        """Initialize HTTP session for FHIR interactions using SMART auth"""

        logger.info("FHIR HTTP client initialized for %s", self.server_url)

        trust_env = self.use_proxies
        try:
            return httpx.AsyncClient(
                timeout=30.0,
                trust_env=trust_env,
            )
        except ImportError as exc:
            logger.warning(
                "Proxy support unavailable (%s); creating session without proxies.",
                exc,
            )
            return httpx.AsyncClient(
                timeout=30.0,
                trust_env=False,
            )

    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate a PKCE code_verifier and corresponding code_challenge."""

        verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode()
        verifier = verifier.rstrip("=")
        challenge = hashlib.sha256(verifier.encode()).digest()
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode().rstrip("=")
        return verifier, challenge_b64

    def build_authorization_url(
        self,
        redirect_uri: str,
        *,
        state: Optional[str] = None,
        audience: Optional[str] = None,
        launch: Optional[str] = None,
        patient: Optional[str] = None,
        user: Optional[str] = None,
    ) -> Tuple[str, str]:
        if not self.auth_url:
            raise RuntimeError(
                "Authorization endpoint is not configured for SMART authentication"
            )

        self.code_verifier, self.code_challenge = self._generate_pkce_pair()
        state = state or secrets.token_urlsafe(24)
        audience = audience or self.audience or self.server_url

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
        }

        if audience:
            params["aud"] = audience
        if launch:
            params["launch"] = launch
        if patient:
            params["patient"] = patient
        if user:
            params["user"] = user

        query = urllib.parse.urlencode(params)
        return f"{self.auth_url}?{query}", state

    async def complete_authorization(
        self,
        code: str,
        redirect_uri: str,
        *,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.token_url:
            raise RuntimeError("Token endpoint is not configured for SMART authentication")

        verifier = code_verifier or self.code_verifier
        if not verifier:
            raise ValueError("code_verifier is required to complete the PKCE flow")

        data: Dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "code_verifier": verifier,
        }
        if self.audience:
            data["aud"] = self.audience

        async with httpx.AsyncClient(trust_env=self.use_proxies, timeout=30.0) as client:
            response = await client.post(
                self.token_url,
                data=data,
                auth=(self.client_id, self.client_secret) if self.client_secret else None,
            )

        if response.status_code >= 400:
            detail = response.json().get("error_description") if response.content else response.text
            raise PermissionError(
                f"SMART authorization code exchange failed ({response.status_code}): {detail or 'authorization denied'}"
            )

        token_data = response.json()
        self._persist_token_data(token_data)
        return token_data

    def _persist_token_data(self, token_data: Dict[str, Any]) -> None:
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        expires_in = token_data.get("expires_in")
        self.token_expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            if expires_in
            else None
        )
        scopes_from_token = token_data.get("scope") or self.scope
        self.granted_scopes = set(scopes_from_token.split()) if scopes_from_token else set()
        self.patient_context = (
            token_data.get("patient")
            or token_data.get("launch_patient")
            or self.patient_context
        )
        self.user_context = (
            token_data.get("user")
            or token_data.get("username")
            or token_data.get("profile")
            or self.user_context
        )

    async def _ensure_valid_token(self) -> None:
        access_token, _, _, _ = self._effective_context()
        if access_token:
            if self.token_expires_at and datetime.now(timezone.utc) < self.token_expires_at:
                return
            if self.token_expires_at is None:
                return

        if self.refresh_token and self.token_url:
            await self._refresh_access_token()
            return

        if self.client_id and self.token_url:
            await self._request_client_credentials_token()
            return

        raise PermissionError("FHIR access token is missing or expired")

    async def _refresh_access_token(self) -> None:
        if not self.refresh_token:
            raise PermissionError("Cannot refresh token: no refresh token available")

        if not self.token_url:
            raise PermissionError("Cannot refresh token: token endpoint unavailable")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
        }
        if self.audience:
            data["aud"] = self.audience

        async with httpx.AsyncClient(trust_env=self.use_proxies, timeout=30.0) as client:
            response = await client.post(
                self.token_url,
                data=data,
                auth=(self.client_id, self.client_secret) if self.client_secret else None,
            )

        if response.status_code >= 400:
            raise PermissionError(
                f"Failed to refresh token ({response.status_code}): {response.text}"
            )

        token_data = response.json()
        self._persist_token_data(token_data)

    async def _request_client_credentials_token(self) -> None:
        """Obtain a new access token using the client_credentials grant."""

        if not self.token_url:
            raise PermissionError("Cannot obtain token: token endpoint unavailable")

        data: Dict[str, Any] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
        }
        if self.scope:
            data["scope"] = self.scope
        if self.audience:
            data["aud"] = self.audience

        async with httpx.AsyncClient(trust_env=self.use_proxies, timeout=30.0) as client:
            response = await client.post(
                self.token_url,
                data=data,
                auth=(self.client_id, self.client_secret) if self.client_secret else None,
            )

        if response.status_code >= 400:
            raise PermissionError(
                f"Failed to obtain client credentials token ({response.status_code}): {response.text}"
            )

        token_data = response.json()
        self._persist_token_data(token_data)

    def _auth_headers(self) -> Dict[str, str]:
        access_token, _, _, _ = self._effective_context()
        if not access_token:
            return self.default_headers
        return {**self.default_headers, "Authorization": f"Bearer {access_token}"}

    def _require_scopes(self, *required_resources: str) -> None:
        _, granted_scopes, _, _ = self._effective_context()
        if not granted_scopes:
            return

        # SMART scopes are typically like "patient/*.read" or "Patient/*.read"
        normalized = {scope.lower() for scope in granted_scopes}

        for resource in required_resources:
            lower_resource = resource.lower()
            wildcard_scopes = {f"{prefix}/*.read" for prefix in ("patient", "user", "system")}
            resource_variants = {
                f"{lower_resource}/*.read",
                f"{lower_resource}.read",
            }
            for prefix in ("patient", "user", "system"):
                resource_variants.update(
                    {
                        f"{prefix}/{lower_resource}/*.read",
                        f"{prefix}/{lower_resource}.read",
                    }
                )

            allowed = bool(normalized & wildcard_scopes)
            if not allowed:
                allowed = bool(normalized & resource_variants)

            if not allowed:
                raise PermissionError(
                    (
                        f"Missing required scope for {resource}: expected one of "
                        f"{', '.join(sorted(resource_variants | wildcard_scopes))} "
                        f"(granted: {', '.join(sorted(normalized))})"
                    )
                )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        max_attempts: int = 4,
        correlation_context: str = "",
    ) -> httpx.Response:
        retryable_statuses = {429, 500, 502, 503, 504}
        attempt = 1
        while True:
            try:
                await self._ensure_valid_token()
                response = await self.session.request(
                    method,
                    url,
                    params=params,
                    headers=self._auth_headers(),
                )
                if response.status_code in {401, 403}:
                    await self._refresh_access_token()
                    if attempt >= max_attempts:
                        raise PermissionError(
                            (
                                f"FHIR request rejected with {response.status_code}. "
                                "Confirm SMART authorization, patient consent, and granted scopes."
                            )
                        )
                    reason = f"status {response.status_code}"
                    attempt += 1
                    continue
                if response.status_code not in retryable_statuses:
                    return response

                reason = f"status {response.status_code}"
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                response = None
                reason = f"exception: {exc}"

            if attempt >= max_attempts:
                logger.warning(
                    "Max attempts reached for %s (correlation=%s); last reason: %s",
                    url,
                    correlation_context,
                    reason,
                )
                status_code = response.status_code if response is not None else None
                raise FHIRConnectorError(
                    f"Request to {url} failed after {max_attempts} attempts: {reason}",
                    error_type="request_failed",
                    status_code=status_code,
                    correlation_id=correlation_context,
                )

            backoff = 0.5 * (2 ** (attempt - 1))
            sleep_time = backoff + random.uniform(0, backoff / 2)
            logger.info(
                "Retrying %s %s (attempt %s/%s, correlation=%s) after %.2fs due to %s",
                method,
                url,
                attempt + 1,
                max_attempts,
                correlation_context,
                sleep_time,
                reason,
            )
            attempt += 1
            await asyncio.sleep(sleep_time)
