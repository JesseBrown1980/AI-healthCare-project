"""
Data Models for Healthcare AI Assistant
Defines Pydantic models for FHIR resources, API requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== FHIR-Related Models ====================

class PatientModel(BaseModel):
    """Patient resource model"""
    id: str
    name: str
    birthDate: Optional[str] = None
    gender: Optional[str] = None
    telecom: List[Dict] = []
    address: List[Dict] = []


class ConditionModel(BaseModel):
    """Condition (diagnosis) resource model"""
    id: str
    code: str
    clinical_status: str
    onset_date: Optional[str] = None
    severity: Optional[str] = None


class MedicationModel(BaseModel):
    """Medication resource model"""
    id: str
    medication: str
    status: str
    dosage: Optional[str] = None
    authored_on: Optional[str] = None


class ObservationModel(BaseModel):
    """Lab result or vital sign model"""
    id: str
    code: str
    value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    interpretation: Optional[str] = None
    effective_date_time: Optional[str] = None


# ==================== API Request/Response Models ====================

class PatientAnalysisRequest(BaseModel):
    """Request for patient analysis"""
    fhir_patient_id: str
    include_recommendations: bool = True
    specialty: Optional[str] = None
    analysis_focus: Optional[str] = None


class PatientAnalysisResponse(BaseModel):
    """Response containing patient analysis"""
    patient_id: str
    status: str
    summary: Optional[Dict] = None
    alerts: Optional[List[Dict]] = None
    risk_scores: Optional[Dict] = None
    recommendations: Optional[Dict] = None
    analysis_timestamp: str
    analysis_duration_seconds: Optional[float] = None


class MedicalQueryRequest(BaseModel):
    """Request for medical query"""
    question: str
    patient_id: Optional[str] = None
    include_reasoning: bool = True


class MedicalQueryResponse(BaseModel):
    """Response to medical query"""
    status: str = "success"
    question: str
    answer: str
    reasoning: Optional[str] = None
    sources: List[str] = []
    confidence: float = 0.0


class FeedbackRequest(BaseModel):
    """User feedback for MLC learning"""
    query_id: str
    feedback_type: str = Field(..., description="positive, negative, or correction")
    corrected_text: Optional[str] = None
    components_used: Optional[List[str]] = None


class FHIRDataRequest(BaseModel):
    """Request for FHIR data"""
    patient_id: str


class FHIRDataResponse(BaseModel):
    """Response with FHIR data"""
    status: str = "success"
    patient_id: str
    data: Dict[str, Any]


class AlertModel(BaseModel):
    """Clinical alert model"""
    severity: str = Field(..., description="critical, high, medium, low")
    type: str = Field(..., description="condition, lab, drug_interaction, etc.")
    message: str
    recommendation: str


# ==================== MLC Learning Models ====================

class LearningComponentModel(BaseModel):
    """Model for learned AI components"""
    component_id: str
    component_type: str
    description: str
    performance: float
    usage_count: int


class FeedbackRecordModel(BaseModel):
    """Record of user feedback"""
    query_id: str
    feedback_type: str
    timestamp: datetime
    processed: bool = False


# ==================== S-LoRA Adapter Models ====================

class LoRAAdapterModel(BaseModel):
    """S-LoRA adapter model"""
    name: str
    specialty: str
    parameters: int
    rank: int
    lora_alpha: int
    status: str = Field(..., description="available, active, loading")
    accuracy_score: float
    memory_mb: float


class AdapterStatusResponse(BaseModel):
    """Response with adapter status"""
    active: List[str]
    available: List[str]
    memory: Dict[str, Any]
    specialties: Dict[str, str]


# ==================== Statistics Models ====================

class SystemStatsResponse(BaseModel):
    """System statistics response"""
    status: str = "success"
    timestamp: str
    stats: Dict[str, Any]
