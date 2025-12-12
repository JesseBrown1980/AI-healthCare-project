export interface Alert {
  message: string;
  severity?: string;
  code?: string;
  recommendation?: string;
  timestamp?: string;
}

export interface Recommendation {
  title?: string;
  recommendation?: string;
  rationale?: string;
  priority?: string;
}

export interface PatientSummary {
  patient_name?: string;
  age?: number;
  gender?: string;
  active_conditions_count?: number;
  current_medications_count?: number;
  narrative_summary?: string;
  key_conditions?: string[];
  key_medications?: string[];
}

export interface MedicationItem {
  name?: string;
  status?: string;
}

export interface MedicationReview {
  total_medications?: number;
  potential_issues?: string[];
  medications?: MedicationItem[];
}

export interface AnalysisMetadata {
  analysis_duration_seconds?: number;
  model?: string;
  correlation_id?: string;
  specialty_used?: string;
  include_recommendations?: boolean;
}

export interface DashboardPatient {
  patient_id: string;
  name?: string;
  latest_risk_score?: number;
  highest_alert_severity?: string;
  specialty?: string;
  last_analyzed_at?: string | null;
}

export interface DashboardSummary {
  patient_id: string;
  critical_alerts?: number;
  cardiovascular_risk?: number;
  readmission_risk?: number;
  last_analysis?: string;
  last_updated?: string;
}

export interface AnalysisResult {
  status?: string;
  patient_id: string;
  patient_data?: Record<string, unknown>;
  risk_scores?: Record<string, number>;
  overall_risk_score?: number;
  highest_alert_severity?: string;
  alerts?: Alert[];
  recommendations?: Recommendation[];
  summary?: PatientSummary;
  medication_review?: MedicationReview;
  analysis_timestamp?: string;
  last_analyzed_at?: string;
  notify_sent?: boolean;
  analysis_duration_seconds?: number;
  analysis_metadata?: AnalysisMetadata;
  reasoning?: string | string[];
}

export interface QueryResult {
  status: string;
  question: string;
  answer?: string;
  reasoning?: string | null;
  sources?: unknown;
  confidence?: number;
}

export interface FeedbackResponse {
  status: string;
  message: string;
  query_id: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  vendor?: string;
}

export interface AdaptersStatus {
  status: string;
  active_adapters?: string[];
  available_adapters?: string[];
  memory_usage?: unknown;
  specialties?: Record<string, unknown> | string[];
}
