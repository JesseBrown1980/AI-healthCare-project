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

export interface DashboardPatient {
  patient_id: string;
  name?: string;
  latest_risk_score?: number;
  highest_alert_severity?: string;
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
  patient_id: string;
  patient_data?: Record<string, unknown>;
  risk_scores?: Record<string, number>;
  overall_risk_score?: number;
  highest_alert_severity?: string;
  alerts?: Alert[];
  recommendations?: Recommendation[];
  summary?: Record<string, unknown>;
  analysis_timestamp?: string;
  last_analyzed_at?: string;
  notify_sent?: boolean;
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
