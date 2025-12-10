"""Compatibility shim for legacy imports.

The original :class:`FHIRConnector` has been split into two layers:

* :class:`backend.fhir_http_client.FhirHttpClient` manages discovery, SMART
  token handling, retries, and low-level HTTP interactions.
* :class:`backend.fhir_resource_service.FhirResourceService` builds on the
  HTTP client to fetch, normalize, and cache patient resources.

Existing callers can continue importing :class:`FHIRConnector`, which aliases
the new :class:`FhirResourceService`.
"""

from .fhir_http_client import FHIRConnectorError, FhirHttpClient
from .fhir_resource_service import FhirResourceService

FHIRConnector = FhirResourceService

__all__ = [
    "FHIRConnectorError",
    "FhirHttpClient",
    "FhirResourceService",
    "FHIRConnector",
]

