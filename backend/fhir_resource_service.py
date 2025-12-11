"""Resource-focused service that builds on :class:`FhirHttpClient`."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import anyio
import httpx

from .fhir_http_client import FHIRConnectorError, FhirHttpClient

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


class FhirResourceService:
    """Higher-level operations for fetching and normalizing FHIR resources."""

    def __init__(
        self,
        client: FhirHttpClient,
        *,
        cache_ttl: Optional[int] = 300,
        cache_ttl_seconds: Optional[int] = None,
    ) -> None:
        self.client = client
        ttl_seconds = cache_ttl if cache_ttl_seconds is None else cache_ttl_seconds
        self.cache_ttl: Optional[timedelta] = (
            timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        )
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._patient_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API helpers
    # ------------------------------------------------------------------
    @property
    def server_url(self) -> str:
        return self.client.server_url

    @property
    def granted_scopes(self) -> set:
        return self.client.granted_scopes

    @property
    def patient_context(self) -> Optional[str]:
        return self.client.patient_context

    @patient_context.setter
    def patient_context(self, value: Optional[str]) -> None:
        self.client.patient_context = value

    @property
    def user_context(self) -> Optional[str]:
        return self.client.user_context

    @user_context.setter
    def user_context(self, value: Optional[str]) -> None:
        self.client.user_context = value

    def request_context(self, *args, **kwargs):
        return self.client.request_context(*args, **kwargs)

    # ------------------------------------------------------------------
    # Resource submission
    # ------------------------------------------------------------------
    async def submit_resource(
        self,
        resource_type: str,
        resource: Dict[str, Any],
        *,
        correlation_context: str = "",
    ) -> Optional[Dict[str, Any]]:
        await self.client.ensure_valid_token()
        url = f"{self.server_url}/{resource_type}"
        response = await self.client.request(
            "POST",
            url,
            json=resource,
            correlation_context=correlation_context,
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

    # ------------------------------------------------------------------
    # Patient fetching / caching
    # ------------------------------------------------------------------
    async def get_patient(self, patient_id: str) -> Dict[str, Any]:
        try:
            cached = self._get_cached_patient(patient_id)
            if cached:
                return cached

            await self.client.ensure_valid_token()
            self._require_scopes("Patient")
            patient_response = await self.client.request(
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
            logger.error(f"Error fetching patient {patient_id}: {str(e)}")
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

    def invalidate_cache(self, patient_id: Optional[str] = None) -> None:
        self.invalidate_patient_cache(patient_id)

    # ------------------------------------------------------------------
    # Validators / cache helpers
    # ------------------------------------------------------------------
    def _require_scopes(self, resource_type: str) -> None:
        if not self.client.client_id:
            return

        _, scopes, _, _ = self.client.get_effective_context()
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
                    f"Requested scopes: {self.client.scope}; granted: {' '.join(sorted(scopes)) or 'none'}. "
                    "Ask the user to authorize the appropriate patient/user access."
                )
            )

    def _cache_patient(self, patient_id: str, data: Dict[str, Any]) -> None:
        expires_at = (
            datetime.now(timezone.utc) + self.cache_ttl if self.cache_ttl else None
        )
        self._patient_cache[patient_id] = {"data": data, "expires_at": expires_at}

    def _get_cached_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        cached = self._patient_cache.get(patient_id)
        if not cached:
            return None
        if cached.get("expires_at") and cached["expires_at"] < datetime.now(timezone.utc):
            del self._patient_cache[patient_id]
            return None
        return cached.get("data")

    def invalidate_patient_cache(self, patient_id: Optional[str] = None) -> None:
        if patient_id:
            self._patient_cache.pop(patient_id, None)
            return
        self._patient_cache.clear()

    def _validate_patient_resource(self, fhir_patient: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validated = Patient.model_validate(fhir_patient)
            return validated.model_dump(mode="json")
        except Exception as exc:  # pragma: no cover - optional dependency best effort
            logger.warning("FHIR Patient validation failed: %s", exc)
            return fhir_patient

    # ------------------------------------------------------------------
    # Resource fetchers
    # ------------------------------------------------------------------
    async def _get_patient_conditions(self, patient_id: str) -> List[Dict]:
        try:
            await self.client.ensure_valid_token()
            self._require_scopes("Condition")
            bundle_url = f"{self.server_url}/Condition"
            request_params = {
                "patient": patient_id,
                "clinical-status": "active",
            }
            correlation_context = f"patient_id={patient_id}"

            conditions = []
            while bundle_url:
                response = await self.client.get_resource(
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
                error_type="conditions_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_medications(self, patient_id: str) -> List[Dict]:
        try:
            await self.client.ensure_valid_token()
            self._require_scopes("MedicationRequest")
            bundle_url = f"{self.server_url}/MedicationRequest"
            request_params = {
                "patient": patient_id,
                "status": "active",
            }
            correlation_context = f"patient_id={patient_id}"

            medications = []
            while bundle_url:
                response = await self.client.get_resource(
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
                error_type="medications_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_observations(self, patient_id: str, limit: int = 50) -> List[Dict]:
        try:
            await self.client.ensure_valid_token()
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
                response = await self.client.get_resource(
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
                error_type="observations_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    async def _get_patient_encounters(
        self, patient_id: str, limit: int = 20
    ) -> List[Dict]:
        try:
            await self.client.ensure_valid_token()
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
                response = await self.client.get_resource(
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
                error_type="encounters_fetch_failed",
                status_code=status_code,
                correlation_id=patient_id,
            ) from e

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------
    def _resolve_next_link(self, bundle: Dict[str, Any]) -> Optional[str]:
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                url = link.get("url")
                if url and url.startswith("http"):
                    return url
                if url:
                    return f"{self.server_url}/{url.lstrip('/')}"
        return None

    def _normalize_patient(self, fhir_patient: Dict) -> Dict:
        fhir_patient = self._normalize_vendor_extensions(fhir_patient)
        return {
            "id": fhir_patient.get("id"),
            "name": self._get_name(fhir_patient),
            "mrn": self._extract_mrn(fhir_patient.get("identifier", [])),
            "birthDate": fhir_patient.get("birthDate"),
            "gender": fhir_patient.get("gender"),
            "telecom": fhir_patient.get("telecom", []),
            "address": fhir_patient.get("address", []),
            "maritalStatus": fhir_patient.get("maritalStatus"),
            "contact": fhir_patient.get("contact", []),
        }

    def _extract_mrn(self, identifiers: List[Dict[str, Any]]) -> Optional[str]:
        """Attempt to pull a medical record number from FHIR identifiers."""

        for identifier in identifiers or []:
            coding = (identifier.get("type") or {}).get("coding", [{}])[0]
            system = (identifier.get("system") or "").lower()
            code = (coding.get("code") or "").lower()

            if "mrn" in system or code in {"mr", "mrn"}:
                return identifier.get("value") or coding.get("display")

        return None

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
            "effectivePeriod": fhir_med_request.get("dosageInstruction", [{}])[0].get("timing", {}).get("repeat", {}),
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
            "interpretation": fhir_observation.get("interpretation", [{}])[0].get("coding", [{}])[0].get("display"),
            "effectiveDateTime": fhir_observation.get("effectiveDateTime"),
            "status": fhir_observation.get("status"),
        }

    def _normalize_encounter(self, fhir_encounter: Dict) -> Dict:
        fhir_encounter = self._normalize_vendor_extensions(fhir_encounter)
        period = fhir_encounter.get("period", {})
        return {
            "id": fhir_encounter.get("id"),
            "type": fhir_encounter.get("type", [{}])[0].get("coding", [{}])[0].get("display"),
            "status": fhir_encounter.get("status"),
            "start": period.get("start"),
            "end": period.get("end"),
            "reasonCode": fhir_encounter.get("reasonCode", [{}])[0].get("coding", [{}])[0].get("display"),
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
            "authenticated": bool(self.client.access_token or self.granted_scopes),
            "status": "connected",
        }

    def _normalize_vendor_extensions(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        extensions = resource.get("extension", [])
        vendor_extensions = []

        filtered_extensions = []
        for ext in extensions:
            url = ext.get("url")
            if url and any(vendor in url for vendor in ("epic.com", "cerner.com")):
                vendor_extensions.append(ext)
                continue
            filtered_extensions.append(ext)

        if vendor_extensions:
            resource = dict(resource)
            resource["extension"] = filtered_extensions
            resource["_vendorExtensions"] = vendor_extensions

        return resource

