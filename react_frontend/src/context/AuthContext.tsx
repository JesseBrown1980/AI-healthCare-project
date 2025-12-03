import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { login as loginRequest } from "../api";
import type { LoginRequest, LoginResponse } from "../api/types";

interface AuthContextValue {
  token: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginRequest) => Promise<LoginResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_STORAGE_KEY = "authToken";
const EMAIL_STORAGE_KEY = "authEmail";

const isBrowser = typeof window !== "undefined" && typeof window.localStorage !== "undefined";

const persistAuth = (token: string | null, email: string | null) => {
  if (!isBrowser) return;

  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }

  if (email) {
    window.localStorage.setItem(EMAIL_STORAGE_KEY, email);
  } else {
    window.localStorage.removeItem(EMAIL_STORAGE_KEY);
  }
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isBrowser) {
      setIsLoading(false);
      return;
    }

    const storedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    const storedEmail = window.localStorage.getItem(EMAIL_STORAGE_KEY);

    setToken(storedToken);
    setUserEmail(storedEmail);
    setIsLoading(false);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUserEmail(null);
    persistAuth(null, null);
  }, []);

  const login = useCallback(async (payload: LoginRequest): Promise<LoginResponse> => {
    setIsLoading(true);
    try {
      const response = await loginRequest(payload);
      setToken(response.access_token);
      setUserEmail(payload.email);
      persistAuth(response.access_token, payload.email);
      return response;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      token,
      userEmail,
      isAuthenticated: Boolean(token),
      isLoading,
      login,
      logout,
    }),
    [token, userEmail, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

  // eslint-disable-next-line react-refresh/only-export-components
  export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}
