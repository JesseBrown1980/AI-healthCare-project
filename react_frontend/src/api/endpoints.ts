export const ENDPOINTS = {
  dashboardPatients: "/patients/dashboard",
  analyzePatient: "/analyze-patient",
  queryMedical: "/query",
  submitFeedback: "/feedback",
  healthStatus: "/health",
  adaptersStatus: "/adapters",
};

export type EndpointKey = keyof typeof ENDPOINTS;

export const getEndpointPath = (key: EndpointKey): string => ENDPOINTS[key];
