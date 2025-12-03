import API_BASE_URL from "../config";

export interface ApiClientOptions extends Omit<RequestInit, "body"> {
  authToken?: string;
  skipJsonContentType?: boolean;
  body?: unknown;
}

export class ApiError<T = unknown> extends Error {
  public status: number;
  public data: T | null;
  public statusText: string;

  constructor(message: string, status: number, statusText: string, data: T | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

const ensureLeadingSlash = (path: string): string => (path.startsWith("/") ? path : `/${path}`);

const buildUrl = (path: string): string => `${API_BASE_URL}${ensureLeadingSlash(path)}`;

const parseResponse = async (response: Response): Promise<unknown> => {
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
};

const mergeHeaders = (headers?: HeadersInit): Headers => {
  const merged = new Headers({ Accept: "application/json" });

  if (!headers) {
    return merged;
  }

  if (headers instanceof Headers) {
    headers.forEach((value, key) => merged.set(key, value));
    return merged;
  }

  if (Array.isArray(headers)) {
    headers.forEach(([key, value]) => merged.set(key, value));
    return merged;
  }

  Object.entries(headers).forEach(([key, value]) => merged.set(key, value));
  return merged;
};

const getStoredAuthToken = (): string | null => {
  if (typeof window === "undefined" || !window.localStorage) {
    return null;
  }

  return window.localStorage.getItem("authToken");
};

// ============================================================================
// Retry Configuration
// ============================================================================

interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
  retryableStatuses: number[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
  retryableStatuses: [429, 500, 502, 503, 504],
};

/**
 * Calculate delay with exponential backoff and jitter
 */
const calculateBackoffDelay = (attempt: number, config: RetryConfig): number => {
  const exponentialDelay = config.baseDelayMs * Math.pow(2, attempt);
  const jitter = Math.random() * 0.3 * exponentialDelay; // Add up to 30% jitter
  return Math.min(exponentialDelay + jitter, config.maxDelayMs);
};

/**
 * Sleep for a given number of milliseconds
 */
const sleep = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Check if a response status is retryable
 */
const isRetryableStatus = (status: number, config: RetryConfig): boolean => {
  return config.retryableStatuses.includes(status);
};

export const request = async <T = unknown>(path: string, options: ApiClientOptions = {}): Promise<T> => {
  const { authToken, skipJsonContentType, headers, body, ...rest } = options;

  const requestHeaders = mergeHeaders(headers);

  const resolvedAuthToken = authToken ?? getStoredAuthToken();

  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  if (!skipJsonContentType && body && !isFormData) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (resolvedAuthToken) {
    requestHeaders.set("Authorization", `Bearer ${resolvedAuthToken}`);
  }

  const url = buildUrl(path);
  const fetchOptions: RequestInit = {
    ...rest,
    headers: requestHeaders,
    body: body && !isFormData && typeof body !== "string" ? JSON.stringify(body) : (body as BodyInit | null | undefined),
  };

  // Retry logic with exponential backoff
  const config = DEFAULT_RETRY_CONFIG;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      const response = await fetch(url, fetchOptions);

      // If response is retryable and we have retries left, wait and retry
      if (!response.ok && isRetryableStatus(response.status, config) && attempt < config.maxRetries) {
        const delay = calculateBackoffDelay(attempt, config);
        console.warn(`[API] Request to ${path} failed with ${response.status}, retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${config.maxRetries})`);
        await sleep(delay);
        continue;
      }

      const data = await parseResponse(response);

      if (!response.ok) {
        const message =
          typeof data === "object" && data && "detail" in (data as Record<string, unknown>)
            ? String((data as Record<string, unknown>).detail)
            : response.statusText || "Request failed";
        throw new ApiError(message, response.status, response.statusText, data as T | null);
      }

      return data as T;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // If it's an ApiError that's not retryable, throw immediately
      if (error instanceof ApiError && !isRetryableStatus(error.status, config)) {
        throw error;
      }

      // Network errors - retry if we have attempts left
      if (!(error instanceof ApiError) && attempt < config.maxRetries) {
        const delay = calculateBackoffDelay(attempt, config);
        console.warn(`[API] Network error on ${path}, retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${config.maxRetries})`);
        await sleep(delay);
        continue;
      }

      throw error;
    }
  }

  // Should never reach here, but TypeScript needs this
  throw lastError ?? new Error("Request failed after retries");
};

export default request;

