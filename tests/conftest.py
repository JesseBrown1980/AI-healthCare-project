import importlib
import sys
from pathlib import Path

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
