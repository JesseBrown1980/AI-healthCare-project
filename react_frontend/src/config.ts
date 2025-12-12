const envBaseUrl =
  (import.meta as { env?: Record<string, string | undefined> }).env?.VITE_API_BASE_URL ||
  (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.
    REACT_APP_API_BASE_URL;

export const API_BASE_URL = envBaseUrl || "http://localhost:8000/api/v1";

export default API_BASE_URL;
