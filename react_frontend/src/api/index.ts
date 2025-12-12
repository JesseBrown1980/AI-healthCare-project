import { ApiError, request } from "./client";
import type {
  AdaptersStatus,
  AnalysisResult,
  DashboardPatient,
  DashboardSummary,
  FeedbackResponse,
  HealthStatus,
  QueryResult,
} from "./types";
import { getEndpointPath } from "./endpoints";

export { request, ApiError };

export const getDashboardPatients = async (): Promise<DashboardPatient[]> => {
  return request<DashboardPatient[]>(getEndpointPath("dashboardPatients"));
};

export const analyzePatient = async (
  patientId: string,
  options?: { includeRecommendations?: boolean; specialty?: string; notify?: boolean }
): Promise<AnalysisResult> => {
  const body = {
    fhir_patient_id: patientId,
    include_recommendations: options?.includeRecommendations ?? true,
    specialty: options?.specialty,
    notify: options?.notify,
  };

  return request<AnalysisResult>(getEndpointPath("analyzePatient"), {
    method: "POST",
    body,
  });
};

export const queryMedical = async (
  question: string,
  options?: { patientId?: string; includeReasoning?: boolean }
): Promise<QueryResult> => {
  const body = {
    question,
    patient_id: options?.patientId,
    include_reasoning: options?.includeReasoning ?? true,
  };

  return request<QueryResult>(getEndpointPath("queryMedical"), {
    method: "POST",
    body,
  });
};

export const submitFeedback = async (
  queryId: string,
  feedbackType: string,
  correctedText?: string
): Promise<FeedbackResponse> => {
  const body = {
    query_id: queryId,
    feedback_type: feedbackType,
    corrected_text: correctedText,
  };

  return request<FeedbackResponse>(getEndpointPath("submitFeedback"), {
    method: "POST",
    body,
  });
};

export const getHealthStatus = async (): Promise<HealthStatus> => {
  return request<HealthStatus>(getEndpointPath("healthStatus"));
};

export const getAdaptersStatus = async (): Promise<AdaptersStatus> => {
  return request<AdaptersStatus>(getEndpointPath("adaptersStatus"));
};

export const getDashboardSummary = async (): Promise<DashboardSummary[]> => {
  return request<DashboardSummary[]>(getEndpointPath("dashboardSummary"));
};
