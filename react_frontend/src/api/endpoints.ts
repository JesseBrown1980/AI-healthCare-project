export const ENDPOINTS = {
  dashboardPatients: "/patients/dashboard",
  dashboardSummary: "/dashboard-summary",
  analyzePatient: "/analyze-patient",
  queryMedical: "/query",
  submitFeedback: "/feedback",
  healthStatus: "/health",
  adaptersStatus: "/adapters",
  authLogin: "/auth/login",
};

export type EndpointKey = keyof typeof ENDPOINTS;

export const getEndpointPath = (key: EndpointKey): string => ENDPOINTS[key];
