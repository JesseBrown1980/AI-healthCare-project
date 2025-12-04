"""
FHIR Connector Module
Handles integration with FHIR-compliant EHR systems
Implements OAuth2 authentication and FHIR resource parsing
"""

import asyncio
import base64
import hashlib
import logging
import random
import secrets
import urllib.parse
import httpx
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from contextvars import ContextVar
import json
import urllib.parse

try:
    from fhir.resources.patient import Patient
except ImportError:  # Optional dependency for schema validation
    class Patient:
        """Fallback Patient model when fhir.resources is unavailable."""

        @staticmethod
        def model_validate(fhir_patient):
            class _Validated:
                def __init__(self, payload):
                    self.payload = payload

                def model_dump(self, mode=None):
                    return self.payload

            return _Validated(fhir_patient)

logger = logging.getLogger(__name__)


class FHIRConnectorError(Exception):
    """Custom error type for unrecoverable FHIR connector failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.correlation_id = correlation_id

    def __str__(self) -> str:  # pragma: no cover - simple representation
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.correlation_id:
            parts.append(f"correlation_id={self.correlation_id}")
        return "; ".join(parts)


class FHIRConnector:
    """
    Connects to FHIR-compliant healthcare systems
    Handles authentication, data fetching, and resource normalization
    Allows optional use of environment-configured proxies for compatibility
    """
    
    def __init__(
        self,
        server_url: str,
        *,
        client_id: str = "",
        client_secret: str = "",
        scope: str = "system/*.read patient/*.read user/*.read",
        auth_url: Optional[str] = None,
        token_url: Optional[str] = None,
        well_known_url: Optional[str] = None,
        audience: Optional[str] = None,
        refresh_token: Optional[str] = None,
        use_proxies: bool = True,
        cache_ttl: Optional[int] = 300,
    ):
        """
        Initialize FHIR connector

        Args:
            server_url: FHIR server base URL
            client_id: SMART-on-FHIR client ID for OAuth 2.0
            client_secret: Confidential client secret for token exchange
            scope: Space-delimited SMART scopes to request
            auth_url: Authorization endpoint (overrides discovery)
            token_url: Token endpoint (overrides discovery)
            well_known_url: Explicit SMART configuration URL (optional)
            audience: Optional token audience/`aud` parameter
            refresh_token: Previously issued refresh token
            use_proxies: Whether to honor proxy settings from environment variables
            cache_ttl: Cache time-to-live for patient data in seconds (None disables expiration)
        """
        self.server_url = server_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.audience = audience
        self.refresh_token = refresh_token
        self.use_proxies = use_proxies
        self.session: Optional[httpx.AsyncClient] = None
        self.discovery_document: Dict[str, Any] = {}
        self.auth_url = auth_url
        self.token_url = token_url
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
        self.cache_ttl: Optional[timedelta] = (
            timedelta(seconds=cache_ttl) if cache_ttl is not None else None
        )
        self._cache: Dict[str, Dict[str, Any]] = {}

        self.well_known_url = (
            well_known_url
            or f"{self.server_url}/.well-known/smart-configuration"
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
        Temporarily override the connector's token and scopes for a specific request.

        This allows the connector to forward caller-provided SMART access tokens so
        downstream FHIR requests enforce the original scopes and patient context.
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
                context.get("patient")
                if context.get("patient") is not None
                else self.patient_context,
                context.get("user")
                if context.get("user") is not None
                else self.user_context,
            )
        return self.access_token, self.granted_scopes, self.patient_context, self.user_context

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        max_attempts: int = 4,
        correlation_context: str = "",
    ) -> httpx.Response:
        """
        Send an HTTP request with exponential backoff retries for transient failures.

        Args:
            method: HTTP method to use.
            url: Full request URL.
            params: Optional query parameters.
            max_attempts: Maximum attempts to avoid thundering-herd issues.
            correlation_context: Additional context for log correlation.
        """

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
            logger.warning(
                "SMART discovery failed at %s: %s", self.well_known_url, exc
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Unexpected error during SMART discovery: %s", exc)

    def _initialize_session(self) -> httpx.AsyncClient:
        """Initialize HTTP session for FHIR interactions using SMART auth"""

        logger.info(f"FHIR connector initialized for {self.server_url}")

        trust_env = self.use_proxies
        try:
            return httpx.AsyncClient(
                timeout=30.0,
                trust_env=trust_env,
            )
        except ImportError as exc:
            # Handles environments lacking optional proxy dependencies (e.g., socksio)
            logger.warning(
                "Proxy support unavailable (%s); creating session without proxies.",
                exc,
            )
            return httpx.AsyncClient(
                timeout=30.0,
                trust_env=False,
            )

    def _resolve_next_link(self, bundle: Dict[str, Any]) -> Optional[str]:
        """Return an absolute URL for the bundle's next link if present."""

        next_link = next(
            (link for link in bundle.get("link", []) if link.get("relation") == "next"),
            None,
        )
        if not next_link:
            return None

        url = next_link.get("url")
        if not url:
            return None

        if url.startswith(("http://", "https://")):
            return url

        return urllib.parse.urljoin(f"{self.server_url}/", url.lstrip("/"))

    def invalidate_patient_cache(self, patient_id: Optional[str] = None) -> None:
        """Invalidate cached patient data.

        Args:
            patient_id: Specific patient ID to invalidate. If omitted, clears all caches.
        """

        if patient_id:
            self._patient_cache.pop(patient_id, None)
            return

        self._patient_cache.clear()

    def _get_cached_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Return cached patient data if still valid."""

        cached = self._patient_cache.get(patient_id)
        if not cached:
            return None

        if cached["expires_at"] < datetime.now(timezone.utc):
            self._patient_cache.pop(patient_id, None)
            return None

        return cached["data"]

    def _cache_patient(self, patient_id: str, data: Dict[str, Any]) -> None:
        """Persist patient data with an expiry."""

        self._patient_cache[patient_id] = {
            "data": data,
            "expires_at": datetime.now(timezone.utc) + self.cache_ttl,
        }

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
        """
        Prepare a SMART-on-FHIR authorization URL using the authorization-code + PKCE flow.

        Returns the redirect URL and the state value that should be validated by callers
        when handling the authorization response.
        """

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
        """Exchange an authorization code for SMART access and refresh tokens."""

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
        """Persist access/refresh tokens, scope grants, and SMART context."""

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

    def _require_scopes(self, resource_type: str) -> None:
        """Ensure the SMART access token covers the requested resource type."""

        if not self.client_id:
            # Skip enforcement if SMART isn't configured
            return

        _, scopes, _, _ = self._effective_context()
        if not scopes:
            raise PermissionError(
                "No SMART scopes granted. Ensure authorization was completed and consent allows data sharing."
            )

        allowed_scopes = {
            f"patient/{resource_type}.read",
            "patient/*.read",
            f"user/{resource_type}.read",
            "user/*.read",
            f"system/{resource_type}.read",
            "system/*.read",
        }

        if not scopes.intersection(allowed_scopes):
            raise PermissionError(
                (
                    f"Missing required SMART scopes for {resource_type}.read. "
                    f"Requested scopes: {self.scope}; granted: {' '.join(sorted(scopes)) or 'none'}. "
                    "Ask the user to authorize the appropriate patient/user access."
                )
            )

    def _auth_headers(self) -> Dict[str, str]:
        access_token, _, _, _ = self._effective_context()
        if not access_token:
            return self.default_headers.copy()

        headers = self.default_headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"
        return headers

    async def _request_token(self) -> None:
        if not self.token_url:
            raise RuntimeError("Token endpoint is not configured for SMART authentication")

        data = {
            "grant_type": "client_credentials",
            "scope": self.scope,
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
                f"SMART token exchange failed ({response.status_code}): {detail or 'consent or credentials invalid'}"
            )

        token_data = response.json()
        self._persist_token_data(token_data)

    async def _refresh_access_token(self) -> None:
        if not self.refresh_token:
            await self._request_token()
            return

        async with httpx.AsyncClient(trust_env=self.use_proxies, timeout=30.0) as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "scope": self.scope,
                },
                auth=(self.client_id, self.client_secret) if self.client_secret else None,
            )

        if response.status_code >= 400:
            detail = response.json().get("error_description") if response.content else response.text
            logger.warning(
                "SMART token refresh failed (%s): %s", response.status_code, detail
            )
            await self._request_token()
            return

        token_data = response.json()
        self._persist_token_data(token_data)

    async def _ensure_valid_token(self) -> None:
        context = self._request_context.get()
        if context and context.get("access_token"):
            # Caller-provided token is already validated upstream
            return

        if not self.client_id:
            return

        needs_token = not self.access_token
        is_expired = self.token_expires_at and datetime.now(timezone.utc) >= self.token_expires_at - timedelta(seconds=60)

        if needs_token:
            await self._request_token()
        elif is_expired:
            await self._refresh_access_token()

    async def submit_resource(
        self,
        resource_type: str,
        resource: Dict[str, Any],
        *,
        correlation_context: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Submit a FHIR resource to the configured server.

        Args:
            resource_type: FHIR resource type (e.g., "AuditEvent").
            resource: JSON payload to send.
            correlation_context: Identifier to correlate audit logs when retries occur.
        """

        await self._ensure_valid_token()
        url = f"{self.server_url}/{resource_type}"
        response = await self.session.post(
            url, json=resource, headers=self._auth_headers()
        )

        if response.status_code >= 400:
            logger.warning(
                "Failed to submit %s (status=%s, correlation=%s): %s",
                resource_type,
                response.status_code,
                correlation_context,
                response.text,
            )
            return None

        try:
            return response.json()
        except ValueError:
            return {}

    async def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """
        Fetch patient resource from FHIR server
        
        Args:
            patient_id: FHIR patient ID
            
        Returns:
            Parsed patient data including demographics, active conditions, medications
        """
        try:
            cached = self._cache.get(patient_id)
            if cached:
                if self.cache_ttl is None:
                    return cached["data"]

                age = datetime.now(timezone.utc) - cached["fetched_at"]
                if age <= self.cache_ttl:
                    return cached["data"]

            await self._ensure_valid_token()
            self._require_scopes("Patient")
            # Fetch Patient resource
            patient_response = await self._request_with_retry(
                "GET",
                f"{self.server_url}/Patient/{patient_id}",
                correlation_context=f"patient_id={patient_id}",
            )
            patient_response.raise_for_status()
            patient = self._validate_patient_resource(patient_response.json())

            # Fetch related resources concurrently after patient existence is confirmed
            (
                conditions,
                medications,
                observations,
                encounters,
            ) = await asyncio.gather(
                self._get_patient_conditions(patient_id),
                self._get_patient_medications(patient_id),
                self._get_patient_observations(patient_id),
                self._get_patient_encounters(patient_id),
            )

            fetched_at = datetime.now(timezone.utc)
            patient_data = {
                "patient": self._normalize_patient(patient),
                "conditions": conditions,
                "medications": medications,
                "observations": observations,
                "encounters": encounters,
                "fetched_at": fetched_at.isoformat(),
            }

            self._cache[patient_id] = {
                "data": patient_data,
                "fetched_at": fetched_at,
            }

            return patient_data

        except httpx.HTTPError as e:
            logger.error(f"Error fetching patient {patient_id}: {str(e)}")
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Error fetching patient {patient_id}: {str(e)}",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    def invalidate_cache(self, patient_id: Optional[str] = None) -> None:
        """Invalidate cached patient data."""

        if patient_id is None:
            self._cache.clear()
            return

        self._cache.pop(patient_id, None)

    def _validate_patient_resource(self, fhir_patient: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming patient resource using FHIR resource models."""
        try:
            validated = Patient.model_validate(fhir_patient)
            return validated.model_dump(mode="json")
        except Exception as exc:
            logger.warning("FHIR Patient validation failed: %s", exc)
            return fhir_patient
    
    async def _get_patient_conditions(self, patient_id: str) -> List[Dict]:
        """Fetch patient's active conditions (diagnoses)"""
        try:
            await self._ensure_valid_token()
            self._require_scopes("Condition")
            bundle_url = f"{self.server_url}/Condition"
            request_params = {
                "patient": patient_id,
                "clinical-status": "active",
            }
            correlation_context = f"patient_id={patient_id}"

            conditions = []
            while bundle_url:
                response = await self._request_with_retry(
                    "GET",
                    bundle_url,
                    params=request_params,
                    correlation_context=correlation_context,
                )
                response.raise_for_status()
                bundle = response.json()

                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    conditions.append(self._normalize_condition(resource))

                bundle_url = self._resolve_next_link(bundle)
                request_params = None

            return conditions
        except Exception as e:
            if isinstance(e, FHIRConnectorError):
                raise
            logger.warning(f"Error fetching conditions for {patient_id}: {str(e)}")
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch conditions for {patient_id}: {str(e)}",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e
    
    async def _get_patient_medications(self, patient_id: str) -> List[Dict]:
        """Fetch patient's active medications"""
        try:
            await self._ensure_valid_token()
            self._require_scopes("MedicationRequest")
            # First get MedicationRequest resources
            bundle_url = f"{self.server_url}/MedicationRequest"
            request_params = {
                "patient": patient_id,
                "status": "active",
            }
            correlation_context = f"patient_id={patient_id}"

            medications = []
            while bundle_url:
                response = await self._request_with_retry(
                    "GET",
                    bundle_url,
                    params=request_params,
                    correlation_context=correlation_context,
                )
                response.raise_for_status()
                bundle = response.json()

                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    medications.append(self._normalize_medication(resource))

                bundle_url = self._resolve_next_link(bundle)
                request_params = None

            return medications
        except Exception as e:
            if isinstance(e, FHIRConnectorError):
                raise
            logger.warning(f"Error fetching medications for {patient_id}: {str(e)}")
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch medications for {patient_id}: {str(e)}",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_observations(self, patient_id: str, limit: int = 50) -> List[Dict]:
        """Fetch patient's lab results and vital signs"""
        try:
            await self._ensure_valid_token()
            self._require_scopes("Observation")
            bundle_url = f"{self.server_url}/Observation"
            request_params = {
                "patient": patient_id,
                "_sort": "-date",
                "_count": limit,
            }
            correlation_context = f"patient_id={patient_id}"

            observations = []
            while bundle_url:
                response = await self._request_with_retry(
                    "GET",
                    bundle_url,
                    params=request_params,
                    correlation_context=correlation_context,
                )
                response.raise_for_status()
                bundle = response.json()

                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    observations.append(self._normalize_observation(resource))

                bundle_url = self._resolve_next_link(bundle)
                request_params = None

            return observations
        except Exception as e:
            if isinstance(e, FHIRConnectorError):
                raise
            logger.warning(f"Error fetching observations for {patient_id}: {str(e)}")
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch observations for {patient_id}: {str(e)}",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_encounters(self, patient_id: str, limit: int = 20) -> List[Dict]:
        """Fetch patient's recent encounters (visits)"""
        try:
            await self._ensure_valid_token()
            self._require_scopes("Encounter")
            bundle_url = f"{self.server_url}/Encounter"
            request_params = {
                "patient": patient_id,
                "_sort": "-date",
                "_count": limit,
            }
            correlation_context = f"patient_id={patient_id}"

            encounters = []
            while bundle_url:
                response = await self._request_with_retry(
                    "GET",
                    bundle_url,
                    params=request_params,
                    correlation_context=correlation_context,
                )
                response.raise_for_status()
                bundle = response.json()

                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    encounters.append(self._normalize_encounter(resource))

                bundle_url = self._resolve_next_link(bundle)
                request_params = None

            return encounters
        except Exception as e:
            if isinstance(e, FHIRConnectorError):
                raise
            logger.warning(f"Error fetching encounters for {patient_id}: {str(e)}")
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch encounters for {patient_id}: {str(e)}",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e
    
    # ==================== NORMALIZATION METHODS ====================
    
    def _normalize_patient(self, fhir_patient: Dict) -> Dict:
        """Normalize FHIR Patient resource"""
        return {
            "id": fhir_patient.get("id"),
            "name": self._get_name(fhir_patient),
            "birthDate": fhir_patient.get("birthDate"),
            "gender": fhir_patient.get("gender"),
            "telecom": fhir_patient.get("telecom", []),
            "address": fhir_patient.get("address", []),
            "maritalStatus": fhir_patient.get("maritalStatus"),
            "contact": fhir_patient.get("contact", [])
        }
    
    def _normalize_condition(self, fhir_condition: Dict) -> Dict:
        """Normalize FHIR Condition resource"""
        return {
            "id": fhir_condition.get("id"),
            "code": fhir_condition.get("code", {}).get("coding", [{}])[0].get("display"),
            "codeSystem": fhir_condition.get("code", {}).get("coding", [{}])[0].get("system"),
            "clinicalStatus": fhir_condition.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
            "onsetDate": fhir_condition.get("onsetDateTime") or fhir_condition.get("onsetDate"),
            "abatementDate": fhir_condition.get("abatementDateTime") or fhir_condition.get("abatementDate"),
            "severity": fhir_condition.get("severity", {}).get("coding", [{}])[0].get("display")
        }
    
    def _normalize_medication(self, fhir_med_request: Dict) -> Dict:
        """Normalize FHIR MedicationRequest resource"""
        return {
            "id": fhir_med_request.get("id"),
            "medication": fhir_med_request.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
            "medicationCode": fhir_med_request.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("code"),
            "status": fhir_med_request.get("status"),
            "dosageInstruction": fhir_med_request.get("dosageInstruction", []),
            "authoredOn": fhir_med_request.get("authoredOn"),
            "effectivePeriod": fhir_med_request.get("dosageInstruction", [{}])[0].get("timing", {}).get("repeat", {})
        }
    
    def _normalize_observation(self, fhir_observation: Dict) -> Dict:
        """Normalize FHIR Observation resource (labs, vitals)"""
        value = fhir_observation.get("valueQuantity", {})
        
        return {
            "id": fhir_observation.get("id"),
            "code": fhir_observation.get("code", {}).get("coding", [{}])[0].get("display"),
            "codeSystem": fhir_observation.get("code", {}).get("coding", [{}])[0].get("code"),
            "value": value.get("value"),
            "unit": value.get("unit"),
            "referenceRange": fhir_observation.get("referenceRange", []),
            "interpretation": fhir_observation.get("interpretation", [{}])[0].get("coding", [{}])[0].get("display"),
            "effectiveDateTime": fhir_observation.get("effectiveDateTime"),
            "status": fhir_observation.get("status")
        }
    
    def _normalize_encounter(self, fhir_encounter: Dict) -> Dict:
        """Normalize FHIR Encounter resource"""
        period = fhir_encounter.get("period", {})
        return {
            "id": fhir_encounter.get("id"),
            "type": fhir_encounter.get("type", [{}])[0].get("coding", [{}])[0].get("display"),
            "status": fhir_encounter.get("status"),
            "start": period.get("start"),
            "end": period.get("end"),
            "reasonCode": fhir_encounter.get("reasonCode", [{}])[0].get("coding", [{}])[0].get("display"),
            "class": fhir_encounter.get("class", {}).get("code")
        }
    
    def _get_name(self, patient: Dict) -> str:
        """Extract patient name from FHIR format"""
        names = patient.get("name", [])
        if names:
            name = names[0]
            parts = []
            if name.get("given"):
                parts.extend(name.get("given", []))
            if name.get("family"):
                parts.append(name.get("family"))
            return " ".join(parts)
        return "Unknown"
    
    def get_stats(self) -> Dict:
        """Get connector statistics"""
        return {
            "server": self.server_url,
            "authenticated": bool(self.access_token or self.granted_scopes),
            "status": "connected"
        }

    async def aclose(self) -> None:
        """Cleanup session asynchronously"""
        session = getattr(self, "session", None)
        if session:
            await session.aclose()

    def __del__(self):
        """Attempt best-effort cleanup of the async session"""
        try:
            session = getattr(self, "session", None)
            if not session:
                return

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(session.aclose())
            else:
                loop = loop or asyncio.new_event_loop()
                try:
                    loop.run_until_complete(session.aclose())
                finally:
                    loop.close()
        except Exception:
            pass
