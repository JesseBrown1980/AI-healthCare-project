import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app


CRITICAL_ROUTES = {
    "/api/v1/device/register",
    "/api/v1/register-device",
    "/api/v1/notifications/register",
    "/api/v1/patients",
    "/api/v1/patients/dashboard",
    "/api/v1/alerts",
    "/api/v1/dashboard-summary",
    "/api/v1/patient/{patient_id}/fhir",
    "/api/v1/patient/{patient_id}/explain",
    "/api/v1/explain/{patient_id}",
}


def test_expected_routes_remain_available():
    """Guard critical endpoints and legacy aliases from accidental removal."""

    with TestClient(app) as client:
        route_paths = {route.path for route in client.app.routes}

    missing = CRITICAL_ROUTES - route_paths
    assert not missing, f"Missing expected routes: {sorted(missing)}"
