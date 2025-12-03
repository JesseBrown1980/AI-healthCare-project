export interface Alert {
  id?: string;
  message: string;
  severity?: string;
  code?: string;
  recommendation?: string;
  timestamp?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  patient?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Recommendation {
  id?: string;
  title?: string;
  recommendation?: string;
  rationale?: string;
  priority?: string;
  sources?: QuerySource[];
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
  dosage?: string;
  frequency?: string;
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

export type RiskScores = Record<string, number>;

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
  sources?: QuerySource[];
  confidence?: number;
  query_id?: string;
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
  message?: string;
  cpu_usage?: number;
  memory_usage?: number;
  disk_usage?: number;
  active_connections?: number;
  uptime?: number;
  services?: Record<string, string | boolean>;
}

export interface AdaptersStatus {
  status: string;
  active_adapters?: string[];
  available_adapters?: string[];
  memory_usage?: unknown;
  specialties?: Record<string, unknown> | string[];
  total_adapters?: number;
  adapters?: Record<string, AdapterInfo>;
  base_model?: string;
}

export interface AdapterInfo {
  name: string;
  specialty: string;
  description?: string;
  status: 'available' | 'loaded' | 'loading' | 'error';
  loaded: boolean;
  accuracy_score?: number;
  last_trained?: string;
  parameters?: number;
  rank?: number;
  lora_alpha?: number;
}

// ============================================================================
// Severity Type
// ============================================================================

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info' | 'unknown';

// ============================================================================
// Explainability Types
// ============================================================================

export interface ExplainResponse {
  status: string;
  patient_id: string;
  feature_names: string[];
  shap_values: number[];
  base_value?: number;
  risk_score?: number;
  model_type?: string;
  correlation_id?: string;
}

export interface FeatureImportance {
  feature: string;
  value: number;
  contribution: 'positive' | 'negative';
  description?: string;
}

// ============================================================================
// Chart Data Types (for visualizations)
// ============================================================================

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface RiskDistribution {
  severity: AlertSeverity;
  count: number;
  percentage: number;
}

// ============================================================================
// Query Source Types
// ============================================================================

export interface QuerySource {
  title?: string;
  url?: string;
  snippet?: string;
  relevance_score?: number;
  source_type?: 'guideline' | 'literature' | 'protocol' | 'drug_database';
}
