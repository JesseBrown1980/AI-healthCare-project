import importlib
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so tests can import package modules.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# These aliases allow code that imports modules as top-level names (e.g. "audit_service")
# to work in the test runner, even though the actual modules live under "backend.<module>".
MODULE_ALIASES = [
    "analysis_cache",
    "security",
    "audit_service",
    "fhir_connector",
    "fhir_http_client",
    "llm_engine",
    "rag_fusion",
    "s_lora_manager",
    "mlc_learning",
    "aot_reasoner",
    "patient_analyzer",
    "patient_data_service",
    "notifier",
    "explainability",
]

for name in MODULE_ALIASES:
    if name not in sys.modules:
        sys.modules[name] = importlib.import_module(f"backend.{name}")

# If the DI package exists (added in PR #123), alias it as top-level "di" so
# imports like "from di import ServiceContainer" work during tests.
try:
    if "di" not in sys.modules:
        sys.modules["di"] = importlib.import_module("backend.di")
except ModuleNotFoundError:
    # backend.di doesn't exist until the DI PR is merged; that's fine.
    pass


@pytest.fixture(autouse=True)
def refresh_module_aliases():
    """Ensure aliased modules reference the real backend implementations."""

    for name in MODULE_ALIASES:
        sys.modules.pop(name, None)
        sys.modules.pop(f"backend.{name}", None)
        sys.modules[name] = importlib.import_module(f"backend.{name}")

    try:
        sys.modules.pop("di", None)
        sys.modules.pop("backend.di", None)
        sys.modules["di"] = importlib.import_module("backend.di")
    except ModuleNotFoundError:
        pass

    explainability = importlib.import_module("backend.explainability")
    main_module = sys.modules.get("backend.main")
    if main_module:
        setattr(main_module, "explain_risk", explainability.explain_risk)

    yield

    for name in MODULE_ALIASES:
        sys.modules.pop(name, None)
        sys.modules.pop(f"backend.{name}", None)
        sys.modules[name] = importlib.import_module(f"backend.{name}")

    try:
        sys.modules.pop("di", None)
        sys.modules.pop("backend.di", None)
        sys.modules["di"] = importlib.import_module("backend.di")
    except ModuleNotFoundError:
        sys.modules.pop("di", None)

    explainability = importlib.import_module("backend.explainability")
    main_module = sys.modules.get("backend.main")
    if main_module:
        setattr(main_module, "explain_risk", explainability.explain_risk)


@pytest.fixture(scope="session")
def anyio_backend():
    """Restrict anyio tests to the asyncio backend to avoid incompatible trio runs."""

    yield "asyncio"


@pytest.fixture
def dependency_overrides_guard():
    """Save and restore FastAPI dependency overrides for each test.

    This prevents DI overrides from leaking between tests and keeps tests readable by
    encouraging the standard save/update/restore pattern when injecting doubles.
    """

    from backend.main import app

    original_overrides = dict(app.dependency_overrides)

    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides = original_overrides
