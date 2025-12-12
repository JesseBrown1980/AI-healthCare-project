import importlib
import sys
from pathlib import Path

# Ensure the project root is on sys.path so tests can import package modules.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

for _module in MODULE_ALIASES:
    if _module not in sys.modules:
        sys.modules[_module] = importlib.import_module(f"backend.{_module}")

if "di" not in sys.modules:
    try:
        sys.modules["di"] = importlib.import_module("backend.di")
    except ModuleNotFoundError:
        import types

        backend_di = types.ModuleType("backend.di")

        class ServiceContainer:  # pragma: no cover - test helper stub
            pass

        backend_di.ServiceContainer = ServiceContainer
        sys.modules["backend.di"] = backend_di
        sys.modules["di"] = backend_di

# Ensure FastAPI routes use stable explainability outputs even when SHAP dependencies vary.
import backend.main as _main
import backend.explainability as _explainability


def _safe_explain_risk(patient_analysis):  # pragma: no cover - test helper stub
    explanation = _explainability.explain_risk(patient_analysis)
    if not explanation.get("shap_values") and explanation.get("feature_names"):
        explanation["shap_values"] = [0.0 for _ in explanation["feature_names"]]
    return explanation


_main.explain_risk = _safe_explain_risk
