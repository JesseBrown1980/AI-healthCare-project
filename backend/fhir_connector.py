"""
FHIR Connector Module
High-level FHIR resource service built on top of a low-level HTTP client.
"""

import asyncio
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import anyio
import httpx

try:
    from fhir.resources.patient import Patient
except ImportError:  # Optional dependency for schema validation
    class Patient:  # type: ignore
        """Fallback Patient model when fhir.resources is unavailable."""

        @staticmethod
        def model_validate(fhir_patient):
            class _Validated:
                def __init__(self, payload):
                    self.payload = payload

                def model_dump(self, mode=None):
                    return self.payload

            return _Validated(fhir_patient)

from .fhir_http_client import FHIRConnectorError, FhirHttpClient

logger = logging.getLogger(__name__)


class FHIRConnector(FhirHttpClient):
    """
    Connects to FHIR-compliant healthcare systems.

    Delegates SMART-on-FHIR authentication, retries, and HTTP concerns to
    ``FhirHttpClient`` while focusing on domain resource retrieval and
    normalization.
    """

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
        cache_ttl: Optional[int] = 300,
        cache_ttl_seconds: Optional[int] = None,
    ):
        super().__init__(
            server_url,
            vendor=vendor,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            auth_url=auth_url,
            token_url=token_url,
            well_known_url=well_known_url,
            audience=audience,
            refresh_token=refresh_token,
            use_proxies=use_proxies,
        )
        ttl_seconds = cache_ttl if cache_ttl_seconds is None else cache_ttl_seconds
        self.cache_ttl: Optional[timedelta] = (
            timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        )
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._patient_cache: Dict[str, Dict[str, Any]] = {}

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
        """Invalidate cached patient data."""

        if patient_id:
            self._patient_cache.pop(patient_id, None)
        else:
            self._patient_cache.clear()

    def _get_cached_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        cached = self._patient_cache.get(patient_id)
        if not cached:
            return None

        fetched_at_str = cached.get("fetched_at")
        if not fetched_at_str:
            return cached

        if not self.cache_ttl:
            return cached

        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
        except (TypeError, ValueError):
            return cached

        if datetime.now(timezone.utc) - fetched_at <= self.cache_ttl:
            return cached

        return None

    def _cache_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> None:
        if self.cache_ttl is None:
            return
        self._patient_cache[patient_id] = patient_data

    def _validate_patient_resource(self, patient_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate patient resource using fhir.resources if available."""

        try:
            validated = Patient.model_validate(patient_json)
            return validated.model_dump(mode="json")
        except Exception:
            return patient_json

    async def submit_resource(
        self,
        resource_type: str,
        resource: Dict[str, Any],
        *,
        correlation_context: str = "",
    ) -> Optional[Dict[str, Any]]:
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
        """Fetch patient resource and related domain data."""

        try:
            cached = self._get_cached_patient(patient_id)
            if cached:
                return cached

            await self._ensure_valid_token()
            self._require_scopes("Patient")
            patient_response = await self._request_with_retry(
                "GET",
                f"{self.server_url}/Patient/{patient_id}",
                correlation_context=f"patient_id={patient_id}",
            )
            patient_response.raise_for_status()
            patient = self._validate_patient_resource(patient_response.json())

            resources: Dict[str, Any] = {}
            async with anyio.create_task_group() as tg:
                tg.start_soon(
                    self._fetch_and_store,
                    self._get_patient_conditions,
                    patient_id,
                    resources,
                    "conditions",
                )
                tg.start_soon(
                    self._fetch_and_store,
                    self._get_patient_medications,
                    patient_id,
                    resources,
                    "medications",
                )
                tg.start_soon(
                    self._fetch_and_store,
                    self._get_patient_observations,
                    patient_id,
                    resources,
                    "observations",
                )
                tg.start_soon(
                    self._fetch_and_store,
                    self._get_patient_encounters,
                    patient_id,
                    resources,
                    "encounters",
                )

            fetched_at = datetime.now(timezone.utc)
            patient_data = {
                "patient": self._normalize_patient(patient),
                "conditions": resources.get("conditions", []),
                "medications": resources.get("medications", []),
                "observations": resources.get("observations", []),
                "encounters": resources.get("encounters", []),
                "fetched_at": fetched_at.isoformat(),
            }

            self._cache_patient(patient_id, patient_data)
            return patient_data

        except httpx.HTTPError as e:
            logger.error("Error fetching patient %s: %s", patient_id, str(e))
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Error fetching patient {patient_id}: {str(e)}",
                error_type="patient_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _fetch_and_store(
        self,
        fetcher,
        patient_id: str,
        store: Dict[str, Any],
        key: str,
    ) -> None:
        store[key] = await fetcher(patient_id)

    async def _get_patient_conditions(self, patient_id: str) -> List[Dict]:
        try:
            await self._ensure_valid_token()
            self._require_scopes("Condition")
            bundle_url = f"{self.server_url}/Condition"
            request_params = {"patient": patient_id, "clinical-status": "active"}
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
            logger.warning("Error fetching conditions for %s: %s", patient_id, str(e))
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch conditions for {patient_id}: {str(e)}",
                error_type="conditions_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_medications(self, patient_id: str) -> List[Dict]:
        try:
            await self._ensure_valid_token()
            self._require_scopes("MedicationRequest")
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
            logger.warning("Error fetching medications for %s: %s", patient_id, str(e))
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch medications for {patient_id}: {str(e)}",
                error_type="medications_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_observations(self, patient_id: str, limit: int = 50) -> List[Dict]:
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
            logger.warning("Error fetching observations for %s: %s", patient_id, str(e))
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch observations for {patient_id}: {str(e)}",
                error_type="observations_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_encounters(self, patient_id: str, limit: int = 20) -> List[Dict]:
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
            logger.warning("Error fetching encounters for %s: %s", patient_id, str(e))
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise FHIRConnectorError(
                f"Failed to fetch encounters for {patient_id}: {str(e)}",
                error_type="encounters_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    # ==================== NORMALIZATION METHODS ====================

    def _normalize_patient(self, fhir_patient: Dict) -> Dict:
        fhir_patient = self._normalize_vendor_extensions(fhir_patient)
        return {
            "id": fhir_patient.get("id"),
            "name": self._get_name(fhir_patient),
            "birthDate": fhir_patient.get("birthDate"),
            "gender": fhir_patient.get("gender"),
            "telecom": fhir_patient.get("telecom", []),
            "address": fhir_patient.get("address", []),
            "maritalStatus": fhir_patient.get("maritalStatus"),
            "contact": fhir_patient.get("contact", []),
        }

    def _normalize_condition(self, fhir_condition: Dict) -> Dict:
        fhir_condition = self._normalize_vendor_extensions(fhir_condition)
        return {
            "id": fhir_condition.get("id"),
            "code": fhir_condition.get("code", {}).get("coding", [{}])[0].get("display"),
            "codeSystem": fhir_condition.get("code", {}).get("coding", [{}])[0].get("system"),
            "clinicalStatus": fhir_condition.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
            "onsetDate": fhir_condition.get("onsetDateTime") or fhir_condition.get("onsetDate"),
            "abatementDate": fhir_condition.get("abatementDateTime") or fhir_condition.get("abatementDate"),
            "severity": fhir_condition.get("severity", {}).get("coding", [{}])[0].get("display"),
        }

    def _normalize_medication(self, fhir_med_request: Dict) -> Dict:
        fhir_med_request = self._normalize_vendor_extensions(fhir_med_request)
        return {
            "id": fhir_med_request.get("id"),
            "medication": fhir_med_request.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
            "medicationCode": fhir_med_request.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("code"),
            "status": fhir_med_request.get("status"),
            "dosageInstruction": fhir_med_request.get("dosageInstruction", []),
            "authoredOn": fhir_med_request.get("authoredOn"),
            "effectivePeriod": fhir_med_request.get("dosageInstruction", [{}])[0]
            .get("timing", {})
            .get("repeat", {}),
        }

    def _normalize_observation(self, fhir_observation: Dict) -> Dict:
        fhir_observation = self._normalize_vendor_extensions(fhir_observation)
        value = fhir_observation.get("valueQuantity", {})

        return {
            "id": fhir_observation.get("id"),
            "code": fhir_observation.get("code", {}).get("coding", [{}])[0].get("display"),
            "codeSystem": fhir_observation.get("code", {}).get("coding", [{}])[0].get("code"),
            "value": value.get("value"),
            "unit": value.get("unit"),
            "referenceRange": fhir_observation.get("referenceRange", []),
            "interpretation": fhir_observation.get("interpretation", [{}])[0]
            .get("coding", [{}])[0]
            .get("display"),
            "effectiveDateTime": fhir_observation.get("effectiveDateTime"),
            "status": fhir_observation.get("status"),
        }

    def _normalize_encounter(self, fhir_encounter: Dict) -> Dict:
        fhir_encounter = self._normalize_vendor_extensions(fhir_encounter)
        period = fhir_encounter.get("period", {})
        return {
            "id": fhir_encounter.get("id"),
            "type": fhir_encounter.get("type", [{}])[0]
            .get("coding", [{}])[0]
            .get("display"),
            "status": fhir_encounter.get("status"),
            "start": period.get("start"),
            "end": period.get("end"),
            "reasonCode": fhir_encounter.get("reasonCode", [{}])[0]
            .get("coding", [{}])[0]
            .get("display"),
            "class": fhir_encounter.get("class", {}).get("code"),
        }

    def _get_name(self, patient: Dict) -> str:
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
        return {
            "server": self.server_url,
            "authenticated": bool(self.access_token or self.granted_scopes),
            "status": "connected",
        }

    def _normalize_vendor_extensions(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        if not resource:
            return resource

        extensions = resource.get("extension") or []
        if not extensions:
            return resource

        vendor_hosts = (
            "open.epic.com",
            "fhir.epic.com",
            "fhir-ehr.cerner.com",
            "fhir.cerner.com",
        )

        retained_extensions: List[Dict[str, Any]] = []
        vendor_extensions: List[Dict[str, Any]] = []

        for extension in extensions:
            url = extension.get("url", "")
            if any(host in url for host in vendor_hosts):
                vendor_extensions.append(
                    {
                        "url": url,
                        "vendor": "epic"
                        if "epic" in url
                        else "cerner"
                        if "cerner" in url
                        else "unknown",
                        "value": self._extract_extension_value(extension),
                    }
                )
                continue

            retained_extensions.append(extension)

        if not vendor_extensions:
            return resource

        normalized = dict(resource)
        normalized["extension"] = retained_extensions
        normalized["_vendorExtensions"] = vendor_extensions
        return normalized

    def _extract_extension_value(self, extension: Dict[str, Any]) -> Any:
        for key, value in extension.items():
            if key.startswith("value") and key != "valueReference":
                return value

        nested_extensions = extension.get("extension") or []
        if nested_extensions:
            return [self._extract_extension_value(ext) for ext in nested_extensions]

        return None

    async def aclose(self) -> None:
        session = getattr(self, "session", None)
        if session:
            await session.aclose()

    def __del__(self):  # pragma: no cover - best effort cleanup
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
