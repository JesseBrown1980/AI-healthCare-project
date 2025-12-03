/**
 * Custom React Hooks
 * Reusable hooks for data fetching, state management, and common operations
 */

import { useCallback, useEffect, useRef, useState } from 'react';
// import { useNavigate } from 'react-router-dom';
import {
  getDashboardPatients,
  analyzePatient,
  queryMedical,
  submitFeedback,
  getHealthStatus,
  getAdaptersStatus,
  // getDashboardSummary,
  ApiError,
} from '../api';
import type { AnalysisResult } from '../api/types';
import { useAppStore, usePatientStore, useSystemStore, useQueryStore } from '../store';
// import { useAuth } from '../context/AuthContext';

// ============================================================================
// useNotification - Toast Notifications
// ============================================================================

export const useNotification = () => {
  const { addNotification, removeNotification, clearNotifications } = useAppStore();

  const notify = useCallback(
    (type: 'success' | 'error' | 'warning' | 'info', title: string, message?: string) => {
      addNotification({ type, title, message, duration: type === 'error' ? 8000 : 5000 });
    },
    [addNotification]
  );

  return {
    success: (title: string, message?: string) => notify('success', title, message),
    error: (title: string, message?: string) => notify('error', title, message),
    warning: (title: string, message?: string) => notify('warning', title, message),
    info: (title: string, message?: string) => notify('info', title, message),
    remove: removeNotification,
    clear: clearNotifications,
  };
};

// ============================================================================
// useDashboardPatients - Fetch and manage patient list
// ============================================================================

export const useDashboardPatients = () => {
  const {
    patients,
    patientsLoading,
    patientsError,
    setPatients,
    setPatientsLoading,
    setPatientsError,
    filters,
  } = usePatientStore();
  const { error: notifyError } = useNotification();

  const fetchPatients = useCallback(async () => {
    setPatientsLoading(true);
    setPatientsError(null);

    try {
      const data = await getDashboardPatients();
      setPatients(data);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to load patients';
      setPatientsError(message);
      notifyError('Failed to load patients', message);
    } finally {
      setPatientsLoading(false);
    }
  }, [setPatients, setPatientsLoading, setPatientsError, notifyError]);

  // Filter patients based on current filters
  const filteredPatients = patients.filter((patient) => {
    // Severity filter
    if (filters.severity !== 'all') {
      if (patient.highest_alert_severity?.toLowerCase() !== filters.severity) {
        return false;
      }
    }

    // Specialty filter
    if (filters.specialty !== 'all') {
      if (patient.specialty?.toLowerCase() !== filters.specialty.toLowerCase()) {
        return false;
      }
    }

    // Search query
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      const matchesName = patient.name?.toLowerCase().includes(query);
      const matchesId = patient.patient_id?.toLowerCase().includes(query);
      if (!matchesName && !matchesId) {
        return false;
      }
    }

    // Risk score range
    const riskScore = (patient.latest_risk_score ?? 0) * 100;
    if (riskScore < filters.riskScoreRange[0] || riskScore > filters.riskScoreRange[1]) {
      return false;
    }

    return true;
  });

  return {
    patients: filteredPatients,
    allPatients: patients,
    loading: patientsLoading,
    error: patientsError,
    refetch: fetchPatients,
  };
};

// ============================================================================
// usePatientAnalysis - Analyze a patient
// ============================================================================

interface AnalysisOptions {
  includeRecommendations?: boolean;
  specialty?: string;
  notify?: boolean;
  useCache?: boolean;
}

export const usePatientAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  
  const { setAnalysisResult, getAnalysisResult } = usePatientStore();
  const { success: notifySuccess, error: notifyError } = useNotification();

  const analyze = useCallback(
    async (patientId: string, options: AnalysisOptions = {}) => {
      const { useCache = true, ...apiOptions } = options;

      // Check cache first
      if (useCache) {
        const cached = getAnalysisResult(patientId);
        if (cached) {
          setResult(cached);
          return cached;
        }
      }

      setLoading(true);
      setError(null);

      try {
        const analysisResult = await analyzePatient(patientId, apiOptions);
        
        if (analysisResult?.status === 'error') {
          const errorMessage = (analysisResult as any).error ?? 'Analysis failed';
          setError(errorMessage);
          notifyError('Analysis Failed', errorMessage);
          return null;
        }

        setResult(analysisResult);
        setAnalysisResult(patientId, analysisResult);
        notifySuccess('Analysis Complete', `Successfully analyzed patient ${patientId}`);
        
        return analysisResult;
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Unable to analyze patient';
        setError(message);
        notifyError('Analysis Error', message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [getAnalysisResult, setAnalysisResult, notifySuccess, notifyError]
  );

  const clearResult = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    analyze,
    result,
    loading,
    error,
    clearResult,
  };
};

// ============================================================================
// useMedicalQuery - RAG-powered medical queries
// ============================================================================

export const useMedicalQuery = () => {
  const {
    queryHistory,
    currentQuery,
    queryLoading,
    queryError,
    setCurrentQuery,
    setQueryLoading,
    setQueryError,
    addToHistory,
    updateFeedback,
  } = useQueryStore();
  
  const { error: notifyError } = useNotification();

  const submitQuery = useCallback(
    async (question: string, options?: { patientId?: string; includeReasoning?: boolean }) => {
      setQueryLoading(true);
      setQueryError(null);

      try {
        const result = await queryMedical(question, options);
        
        addToHistory({
          question,
          answer: result.answer ?? '',
          reasoning: Array.isArray(result.reasoning) ? result.reasoning : result.reasoning ? [result.reasoning] : undefined,
          sources: result.sources as any,
          confidence: result.confidence,
          patientId: options?.patientId,
        });

        return result;
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Query failed';
        setQueryError(message);
        notifyError('Query Failed', message);
        return null;
      } finally {
        setQueryLoading(false);
      }
    },
    [setQueryLoading, setQueryError, addToHistory, notifyError]
  );

  const sendFeedback = useCallback(
    async (queryId: string, feedbackType: 'positive' | 'negative' | 'correction', correctedText?: string) => {
      try {
        await submitFeedback(queryId, feedbackType, correctedText);
        updateFeedback(queryId, feedbackType);
        return true;
      } catch (err) {
        notifyError('Feedback Failed', 'Unable to submit feedback');
        return false;
      }
    },
    [updateFeedback, notifyError]
  );

  return {
    submitQuery,
    sendFeedback,
    history: queryHistory,
    currentQuery,
    setCurrentQuery,
    loading: queryLoading,
    error: queryError,
  };
};

// ============================================================================
// useSystemHealth - System health monitoring
// ============================================================================

export const useSystemHealth = () => {
  const {
    healthStatus,
    healthLoading,
    healthError,
    lastHealthCheck,
    setHealthStatus,
    setHealthLoading,
    setHealthError,
    adaptersStatus,
    adaptersLoading,
    setAdaptersStatus,
    setAdaptersLoading,
  } = useSystemStore();
  
  const { error: notifyError } = useNotification();

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);

    try {
      const status = await getHealthStatus();
      setHealthStatus(status);
      return status;
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Health check failed';
      setHealthError(message);
      notifyError('Health Check Failed', message);
      return null;
    } finally {
      setHealthLoading(false);
    }
  }, [setHealthStatus, setHealthLoading, setHealthError, notifyError]);

  const fetchAdapters = useCallback(async () => {
    setAdaptersLoading(true);

    try {
      const status = await getAdaptersStatus();
      setAdaptersStatus(status);
      return status;
    } catch (err) {
      notifyError('Failed to load adapters', 'Unable to fetch adapter status');
      return null;
    } finally {
      setAdaptersLoading(false);
    }
  }, [setAdaptersStatus, setAdaptersLoading, notifyError]);

  return {
    healthStatus,
    healthLoading,
    healthError,
    lastHealthCheck,
    checkHealth,
    adaptersStatus,
    adaptersLoading,
    fetchAdapters,
  };
};

// ============================================================================
// useInterval - Polling hook
// ============================================================================

export const useInterval = (callback: () => void, delay: number | null) => {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    const tick = () => savedCallback.current();
    const id = setInterval(tick, delay);

    return () => clearInterval(id);
  }, [delay]);
};

// ============================================================================
// useAutoRefresh - Auto-refresh data with configurable interval
// ============================================================================

export const useAutoRefresh = (
  fetchFn: () => Promise<any>,
  options: { enabled?: boolean; interval?: number; immediate?: boolean } = {}
) => {
  const { enabled = true, interval = 60000, immediate = true } = options;
  const { preferences } = useAppStore();

  useEffect(() => {
    if (immediate && enabled && preferences.autoRefresh) {
      fetchFn();
    }
  }, []);

  useInterval(
    () => {
      if (enabled && preferences.autoRefresh) {
        fetchFn();
      }
    },
    enabled && preferences.autoRefresh ? interval : null
  );
};

// ============================================================================
// useDebounce - Debounce a value
// ============================================================================

export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};

// ============================================================================
// useLocalStorage - Persist state to localStorage
// ============================================================================

export const useLocalStorage = <T>(key: string, initialValue: T) => {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      } catch (error) {
        console.error('Error saving to localStorage:', error);
      }
    },
    [key, storedValue]
  );

  return [storedValue, setValue] as const;
};

// ============================================================================
// useMediaQuery - Responsive design hook
// ============================================================================

export const useMediaQuery = (query: string): boolean => {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches);

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);

  return matches;
};

// Convenience hooks for common breakpoints
export const useIsMobile = () => useMediaQuery('(max-width: 768px)');
export const useIsTablet = () => useMediaQuery('(min-width: 769px) and (max-width: 1024px)');
export const useIsDesktop = () => useMediaQuery('(min-width: 1025px)');
