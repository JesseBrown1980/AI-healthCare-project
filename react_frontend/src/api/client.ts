import API_BASE_URL from "../config";

export interface ApiClientOptions extends RequestInit {
  authToken?: string;
  skipJsonContentType?: boolean;
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

export const request = async <T = unknown>(path: string, options: ApiClientOptions = {}): Promise<T> => {
  const { authToken, skipJsonContentType, headers, body, ...rest } = options;

  const requestHeaders = mergeHeaders(headers);

  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  if (!skipJsonContentType && body && !isFormData) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (authToken) {
    requestHeaders.set("Authorization", `Bearer ${authToken}`);
  }

  const response = await fetch(buildUrl(path), {
    ...rest,
    headers: requestHeaders,
    body: body && !isFormData && typeof body !== "string" ? JSON.stringify(body) : (body as BodyInit | null | undefined),
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    const message =
      typeof data === "object" && data && "detail" in (data as Record<string, unknown>)
        ? String((data as Record<string, unknown>).detail)
        : response.statusText || "Request failed";
    throw new ApiError(message, response.status, response.statusText, data as T | null);
  }

  return data as T;
};

export default request;
