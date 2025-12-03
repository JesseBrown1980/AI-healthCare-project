/**
 * Global State Management using Zustand
 * Lightweight, TypeScript-first state management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { DashboardPatient, AnalysisResult, HealthStatus } from '../api/types';

// ============================================================================
// Types
// ============================================================================

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  timestamp: number;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  dashboardLayout: 'grid' | 'list';
  autoRefresh: boolean;
  refreshInterval: number; // in seconds
  // Display preferences
  dateFormat: string;
  timeFormat: string;
  // Dashboard preferences
  showNotifications: boolean;
  compactView: boolean;
  defaultView: string;
  itemsPerPage: number;
  // Clinical preferences
  defaultSpecialty: string;
  includeReasoningByDefault: boolean;
  showConfidenceScores: boolean;
  riskAlertThreshold: number;
}

// ============================================================================
// App Store - Global UI State
// ============================================================================

interface AppState {
  // Sidebar & Navigation
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Notifications
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Loading States
  globalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;

  // User Preferences
  preferences: UserPreferences;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        // Sidebar
        sidebarOpen: true,
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

        // Notifications
        notifications: [],
        addNotification: (notification) =>
          set((state) => ({
            notifications: [
              ...state.notifications,
              {
                ...notification,
                id: crypto.randomUUID(),
                timestamp: Date.now(),
              },
            ],
          })),
        removeNotification: (id) =>
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          })),
        clearNotifications: () => set({ notifications: [] }),

        // Loading
        globalLoading: false,
        setGlobalLoading: (loading) => set({ globalLoading: loading }),

        // Preferences
        preferences: {
          theme: 'system',
          language: 'en',
          dashboardLayout: 'grid',
          autoRefresh: true,
          refreshInterval: 60,
          dateFormat: 'MM/DD/YYYY',
          timeFormat: '12h',
          showNotifications: true,
          compactView: false,
          defaultView: 'grid',
          itemsPerPage: 25,
          defaultSpecialty: 'auto',
          includeReasoningByDefault: true,
          showConfidenceScores: true,
          riskAlertThreshold: 0.7,
        },
        updatePreferences: (prefs) =>
          set((state) => ({
            preferences: { ...state.preferences, ...prefs },
          })),
      }),
      {
        name: 'healthcare-app-storage',
        partialize: (state) => ({ preferences: state.preferences }),
      }
    ),
    { name: 'AppStore' }
  )
);

// ============================================================================
// Patient Store - Patient Data & Analysis
// ============================================================================

interface PatientState {
  // Dashboard Patients
  patients: DashboardPatient[];
  patientsLoading: boolean;
  patientsError: string | null;
  setPatients: (patients: DashboardPatient[]) => void;
  setPatientsLoading: (loading: boolean) => void;
  setPatientsError: (error: string | null) => void;

  // Selected Patient
  selectedPatientId: string | null;
  setSelectedPatientId: (id: string | null) => void;

  // Analysis Results Cache
  analysisCache: Record<string, AnalysisResult>;
  setAnalysisResult: (patientId: string, result: AnalysisResult) => void;
  getAnalysisResult: (patientId: string) => AnalysisResult | undefined;
  clearAnalysisCache: () => void;

  // Filters
  filters: {
    severity: string;
    specialty: string;
    searchQuery: string;
    riskScoreRange: [number, number];
  };
  setFilter: (key: keyof PatientState['filters'], value: any) => void;
  resetFilters: () => void;
}

const defaultFilters = {
  severity: 'all',
  specialty: 'all',
  searchQuery: '',
  riskScoreRange: [0, 100] as [number, number],
};

export const usePatientStore = create<PatientState>()(
  devtools(
    (set, get) => ({
      // Dashboard Patients
      patients: [],
      patientsLoading: false,
      patientsError: null,
      setPatients: (patients) => set({ patients, patientsError: null }),
      setPatientsLoading: (loading) => set({ patientsLoading: loading }),
      setPatientsError: (error) => set({ patientsError: error }),

      // Selected Patient
      selectedPatientId: null,
      setSelectedPatientId: (id) => set({ selectedPatientId: id }),

      // Analysis Cache
      analysisCache: {},
      setAnalysisResult: (patientId, result) =>
        set((state) => ({
          analysisCache: { ...state.analysisCache, [patientId]: result },
        })),
      getAnalysisResult: (patientId) => get().analysisCache[patientId],
      clearAnalysisCache: () => set({ analysisCache: {} }),

      // Filters
      filters: defaultFilters,
      setFilter: (key, value) =>
        set((state) => ({
          filters: { ...state.filters, [key]: value },
        })),
      resetFilters: () => set({ filters: defaultFilters }),
    }),
    { name: 'PatientStore' }
  )
);

// ============================================================================
// System Store - System Health & Status
// ============================================================================

interface SystemState {
  healthStatus: HealthStatus | null;
  healthLoading: boolean;
  healthError: string | null;
  lastHealthCheck: number | null;
  
  setHealthStatus: (status: HealthStatus) => void;
  setHealthLoading: (loading: boolean) => void;
  setHealthError: (error: string | null) => void;
  
  // Adapters
  adaptersStatus: any | null;
  adaptersLoading: boolean;
  setAdaptersStatus: (status: any) => void;
  setAdaptersLoading: (loading: boolean) => void;
}

export const useSystemStore = create<SystemState>()(
  devtools(
    (set) => ({
      healthStatus: null,
      healthLoading: false,
      healthError: null,
      lastHealthCheck: null,
      
      setHealthStatus: (status) =>
        set({ healthStatus: status, healthError: null, lastHealthCheck: Date.now() }),
      setHealthLoading: (loading) => set({ healthLoading: loading }),
      setHealthError: (error) => set({ healthError: error }),
      
      adaptersStatus: null,
      adaptersLoading: false,
      setAdaptersStatus: (status) => set({ adaptersStatus: status }),
      setAdaptersLoading: (loading) => set({ adaptersLoading: loading }),
    }),
    { name: 'SystemStore' }
  )
);

// ============================================================================
// Query Store - Medical Queries & Feedback
// ============================================================================

interface QueryHistoryItem {
  id: string;
  question: string;
  answer: string;
  reasoning?: string[];
  sources?: any[];
  confidence?: number;
  patientId?: string;
  timestamp: number;
  feedbackGiven?: 'positive' | 'negative' | 'correction';
}

interface QueryState {
  queryHistory: QueryHistoryItem[];
  currentQuery: string;
  queryLoading: boolean;
  queryError: string | null;
  
  setCurrentQuery: (query: string) => void;
  setQueryLoading: (loading: boolean) => void;
  setQueryError: (error: string | null) => void;
  addToHistory: (item: Omit<QueryHistoryItem, 'id' | 'timestamp'>) => void;
  updateFeedback: (id: string, feedback: QueryHistoryItem['feedbackGiven']) => void;
  clearHistory: () => void;
}

export const useQueryStore = create<QueryState>()(
  devtools(
    persist(
      (set) => ({
        queryHistory: [],
        currentQuery: '',
        queryLoading: false,
        queryError: null,
        
        setCurrentQuery: (query) => set({ currentQuery: query }),
        setQueryLoading: (loading) => set({ queryLoading: loading }),
        setQueryError: (error) => set({ queryError: error }),
        addToHistory: (item) =>
          set((state) => ({
            queryHistory: [
              { ...item, id: crypto.randomUUID(), timestamp: Date.now() },
              ...state.queryHistory,
            ].slice(0, 50), // Keep last 50 queries
          })),
        updateFeedback: (id, feedback) =>
          set((state) => ({
            queryHistory: state.queryHistory.map((item) =>
              item.id === id ? { ...item, feedbackGiven: feedback } : item
            ),
          })),
        clearHistory: () => set({ queryHistory: [] }),
      }),
      {
        name: 'healthcare-query-history',
        partialize: (state) => ({ queryHistory: state.queryHistory }),
      }
    ),
    { name: 'QueryStore' }
  )
);
