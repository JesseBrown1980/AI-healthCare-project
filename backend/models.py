from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str
    service: str
    version: str
    vendor: Optional[str] = None


class CacheClearResponse(BaseModel):
    status: str
    analysis_history_cleared: int
    summary_cache_entries_cleared: int
    analysis_cache_cleared: bool


class DeviceRegistrationResponse(BaseModel):
    status: str
    device: Dict[str, Any]


class PatientListEntry(BaseModel):
    id: str
    patient_id: str
    name: str
    full_name: str
    age: Optional[int] = None
    mrn: Optional[str] = None
    last_updated: Optional[str] = None
    highest_alert_severity: Optional[str] = None
    latest_risk_score: Optional[float] = None
    last_analyzed_at: Optional[str] = None


class PatientListResponse(BaseModel):
    patients: List[PatientListEntry]


class DashboardEntry(BaseModel):
    patient_id: str
    name: Optional[str] = None
    latest_risk_score: Optional[float] = None
    highest_alert_severity: Optional[str] = None
    last_analyzed_at: Optional[str] = None


class Alert(BaseModel):
    id: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    severity: Optional[str] = None
    timestamp: Optional[str] = None


class AlertsResponse(BaseModel):
    alerts: List[Alert]


class AnalyzePatientResponse(BaseModel):
    patient_id: str
    status: str
    analysis_timestamp: Optional[str] = None
    last_analyzed_at: Optional[str] = None
    analysis_duration_seconds: Optional[float] = None
    summary: Optional[Dict[str, Any]] = None
    alerts: Optional[List[Any]] = None
    alert_count: Optional[int] = None
    highest_alert_severity: Optional[str] = None
    risk_scores: Optional[Dict[str, Any]] = None
    overall_risk_score: Optional[float] = None
    polypharmacy_risk: Optional[bool] = None
    medication_review: Optional[Any] = None
    recommendations: Optional[List[Any]] = None
    patient_data: Optional[Dict[str, Any]] = None
    active_specialties: Optional[List[str]] = None


class DashboardSummaryEntry(BaseModel):
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    overall_risk_score: Optional[float] = None
    highest_alert_severity: Optional[str] = None
    critical_alerts: Optional[int] = None
    cardiovascular_risk: Optional[float] = None
    readmission_risk: Optional[float] = None
    last_analysis: Optional[str] = None
    last_updated: Optional[str] = None


class PatientFHIRResponse(BaseModel):
    status: str
    patient_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    correlation_id: Optional[str] = None


class ExplainResponse(BaseModel):
    status: str
    patient_id: str
    explanation: Dict[str, Any]
    base_risk: Optional[float] = None
    shap_values: Optional[List[Any]] = None
    feature_names: Optional[List[str]] = None
    model_type: Optional[str] = None
    correlation_id: Optional[str] = None


class QueryResponse(BaseModel):
    status: str
    question: str
    answer: Optional[str] = None
    reasoning: Optional[str] = None
    sources: Optional[List[Any]] = None
    confidence: Optional[float] = None


class FeedbackResponse(BaseModel):
    status: str
    message: str
    query_id: str


class AdapterStatusResponse(BaseModel):
    status: str
    active_adapters: Optional[List[str]] = None
    available_adapters: Optional[List[str]] = None
    memory_usage: Optional[Dict[str, Any]] = None
    specialties: Optional[Dict[str, Any]] = None


class ActivateAdapterResponse(BaseModel):
    status: str
    adapter: str
    active: bool


class StatsResponse(BaseModel):
    status: str
    timestamp: str
    stats: Dict[str, Any]
