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

export { request, ApiError };

export const getDashboardPatients = async (): Promise<DashboardPatient[]> => {
  // TODO: Implement dashboard patients fetch
  throw new Error("Not implemented");
};

export const analyzePatient = async (
  patientId: string,
  options?: { includeRecommendations?: boolean; specialty?: string; notify?: boolean }
): Promise<AnalysisResult> => {
  void patientId;
  void options;
  // TODO: Implement patient analysis call
  throw new Error("Not implemented");
};

export const queryMedical = async (
  question: string,
  options?: { patientId?: string; includeReasoning?: boolean }
): Promise<QueryResult> => {
  void question;
  void options;
  // TODO: Implement medical query call
  throw new Error("Not implemented");
};

export const submitFeedback = async (
  queryId: string,
  feedbackType: string,
  correctedText?: string
): Promise<FeedbackResponse> => {
  void queryId;
  void feedbackType;
  void correctedText;
  // TODO: Implement feedback submission
  throw new Error("Not implemented");
};

export const getHealthStatus = async (): Promise<HealthStatus> => {
  // TODO: Implement health status fetch
  throw new Error("Not implemented");
};

export const getAdaptersStatus = async (): Promise<AdaptersStatus> => {
  // TODO: Implement adapters status fetch
  throw new Error("Not implemented");
};

export const getDashboardSummary = async (): Promise<DashboardSummary[]> => {
  // TODO: Implement dashboard summary fetch
  throw new Error("Not implemented");
};
