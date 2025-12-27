from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


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
    specialty: Optional[str] = None


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


class AnalyzePatientRequest(BaseModel):
    fhir_patient_id: Optional[str] = None
    patient_id: Optional[str] = None  # Alias for fhir_patient_id
    include_recommendations: bool = True
    specialty: Optional[str] = None
    use_cache: bool = True
    notify: bool = False

    @model_validator(mode="before")
    @classmethod
    def check_patient_ids(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Allow patient_id as alias for fhir_patient_id."""
        if isinstance(values, dict):
            if not values.get("fhir_patient_id") and values.get("patient_id"):
                values["fhir_patient_id"] = values.get("patient_id")
        return values


class AnalyzePatientResponse(BaseModel):
    patient_id: str
    status: Optional[str] = None
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
    feature_names: List[str] = Field(default_factory=list)
    shap_values: List[float] = Field(default_factory=list)
    base_value: Optional[float] = None
    risk_score: Optional[float] = None
    model_type: Optional[str] = None
    correlation_id: Optional[str] = None


class QueryResponse(BaseModel):
    status: str
    question: str
    answer: Optional[str] = None
    reasoning: Optional[Union[str, List[str]]] = None
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
    active: Optional[Any] = None


class StatsResponse(BaseModel):
    status: str
    timestamp: str
    stats: Dict[str, Any]


class DemoLoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    patient: Optional[str] = None


class DemoLoginResponse(BaseModel):
    access_token: str
    expires_in: int


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")
    roles: Optional[List[str]] = Field(None, description="User roles (default: ['viewer'])")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()


class RegisterResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    roles: List[str]
    message: str = "User registered successfully"


class DeviceRegistration(BaseModel):
    device_token: str
    platform: str = "unknown"

    @model_validator(mode="before")
    @classmethod
    def populate_device_token(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Allow payloads that send push_token instead of device_token."""
        if isinstance(values, dict):
            if not values.get("device_token") and values.get("push_token"):
                values["device_token"] = values["push_token"]
        return values

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        normalized = value.strip().lower() if value else "unknown"
        if normalized in {"ios", "android"}:
            return "iOS" if normalized == "ios" else "Android"
        if normalized in {"expo", "unknown", ""}:
            return "Expo" if normalized == "expo" else "Unknown"
        raise ValueError("platform must be iOS, Android, or Expo")
