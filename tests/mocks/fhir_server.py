"""
Mock FHIR Server
Provides a mock FHIR client that returns fixture data instead of making real API calls.
"""

from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import httpx

from tests.fixtures.fhir_bundles import (
    create_patient_bundle,
    create_empty_bundle,
    FHIRBundleFactory,
)
from tests.fixtures.patients import PatientFactory


class MockFHIRServer:
    """
    Mock FHIR server that returns fixture data.
    
    Usage:
        with MockFHIRServer() as fhir:
            fhir.add_patient("patient-123", {"name": "John Doe"})
            result = await some_fhir_client.get_patient("patient-123")
    """
    
    def __init__(self):
        self.patients: Dict[str, Dict[str, Any]] = {}
        self.conditions: Dict[str, List[Dict[str, Any]]] = {}
        self.medications: Dict[str, List[Dict[str, Any]]] = {}
        self._responses: Dict[str, Any] = {}
    
    def add_patient(self, patient_id: str, data: Optional[Dict[str, Any]] = None):
        """Add a patient to the mock server."""
        if data is None:
            data = PatientFactory.create(patient_id=patient_id)
        self.patients[patient_id] = data
        return self
    
    def add_bundle(self, bundle: Dict[str, Any]):
        """Add all resources from a bundle."""
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id")
            
            if resource_type == "Patient":
                self.patients[resource_id] = resource
            elif resource_type == "Condition":
                patient_ref = resource.get("subject", {}).get("reference", "")
                patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
                if patient_id not in self.conditions:
                    self.conditions[patient_id] = []
                self.conditions[patient_id].append(resource)
            elif resource_type == "MedicationStatement":
                patient_ref = resource.get("subject", {}).get("reference", "")
                patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
                if patient_id not in self.medications:
                    self.medications[patient_id] = []
                self.medications[patient_id].append(resource)
        return self
    
    def set_response(self, path: str, response: Any):
        """Set a custom response for a specific path."""
        self._responses[path] = response
        return self
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a patient by ID."""
        if patient_id in self.patients:
            return self.patients[patient_id]
        return None
    
    def search_patients(self, **kwargs) -> Dict[str, Any]:
        """Search patients (returns all as a bundle)."""
        resources = list(self.patients.values())
        return FHIRBundleFactory.create_bundle(resources)
    
    def get_patient_conditions(self, patient_id: str) -> Dict[str, Any]:
        """Get conditions for a patient."""
        resources = self.conditions.get(patient_id, [])
        return FHIRBundleFactory.create_bundle(resources)
    
    def get_patient_medications(self, patient_id: str) -> Dict[str, Any]:
        """Get medications for a patient."""
        resources = self.medications.get(patient_id, [])
        return FHIRBundleFactory.create_bundle(resources)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return mock capability statement."""
        return {
            "resourceType": "CapabilityStatement",
            "status": "active",
            "fhirVersion": "4.0.1",
            "format": ["json", "xml"],
            "rest": [
                {
                    "mode": "server",
                    "resource": [
                        {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                        {"type": "Condition", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                        {"type": "MedicationStatement", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    ]
                }
            ]
        }


@contextmanager
def mock_fhir_client(mock_server: Optional[MockFHIRServer] = None):
    """
    Context manager to mock FHIR HTTP client calls.
    
    Usage:
        with mock_fhir_client() as server:
            server.add_patient("123", {"name": "Test"})
            # Your code that calls FHIR will get mock responses
    """
    if mock_server is None:
        mock_server = MockFHIRServer()
        # Add some default test data
        bundle = create_patient_bundle()
        mock_server.add_bundle(bundle)
    
    async def mock_get(url: str, *args, **kwargs):
        """Mock httpx GET request."""
        response = MagicMock()
        response.status_code = 200
        
        if "/metadata" in url:
            response.json.return_value = mock_server.get_metadata()
        elif "/Patient/" in url:
            patient_id = url.split("/Patient/")[-1].split("?")[0].split("/")[0]
            patient = mock_server.get_patient(patient_id)
            if patient:
                response.json.return_value = patient
            else:
                response.status_code = 404
                response.json.return_value = {"resourceType": "OperationOutcome", "issue": [{"severity": "error"}]}
        elif "/Patient" in url:
            response.json.return_value = mock_server.search_patients()
        elif "/Condition" in url and "patient=" in url:
            patient_id = url.split("patient=")[-1].split("&")[0]
            response.json.return_value = mock_server.get_patient_conditions(patient_id)
        else:
            response.json.return_value = create_empty_bundle()
        
        return response
    
    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        with patch("httpx.Client.get", side_effect=lambda *a, **k: mock_get(*a, **k)):
            yield mock_server
