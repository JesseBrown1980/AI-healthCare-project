/**
 * Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore, usePatientStore, useSystemStore, useQueryStore } from '../../store';

describe('useAppStore', () => {
  beforeEach(() => {
    useAppStore.setState({
      sidebarOpen: true,
      notifications: [],
      globalLoading: false,
    });
  });

  it('toggles sidebar', () => {
    const { toggleSidebar } = useAppStore.getState();
    expect(useAppStore.getState().sidebarOpen).toBe(true);
    toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(false);
    toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(true);
  });

  it('sets sidebar state', () => {
    const { setSidebarOpen } = useAppStore.getState();
    setSidebarOpen(false);
    expect(useAppStore.getState().sidebarOpen).toBe(false);
    setSidebarOpen(true);
    expect(useAppStore.getState().sidebarOpen).toBe(true);
  });

  it('adds notifications', () => {
    const { addNotification } = useAppStore.getState();
    addNotification({
      type: 'success',
      title: 'Test',
      message: 'Test message',
    });
    const notifications = useAppStore.getState().notifications;
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe('success');
    expect(notifications[0].title).toBe('Test');
  });

  it('removes notifications', () => {
    const { addNotification, removeNotification } = useAppStore.getState();
    addNotification({ type: 'info', title: 'Test' });
    const id = useAppStore.getState().notifications[0].id;
    removeNotification(id);
    expect(useAppStore.getState().notifications).toHaveLength(0);
  });

  it('clears all notifications', () => {
    const { addNotification, clearNotifications } = useAppStore.getState();
    addNotification({ type: 'info', title: 'Test 1' });
    addNotification({ type: 'info', title: 'Test 2' });
    expect(useAppStore.getState().notifications).toHaveLength(2);
    clearNotifications();
    expect(useAppStore.getState().notifications).toHaveLength(0);
  });

  it('sets global loading', () => {
    const { setGlobalLoading } = useAppStore.getState();
    setGlobalLoading(true);
    expect(useAppStore.getState().globalLoading).toBe(true);
    setGlobalLoading(false);
    expect(useAppStore.getState().globalLoading).toBe(false);
  });

  it('updates preferences', () => {
    const { updatePreferences } = useAppStore.getState();
    updatePreferences({ theme: 'dark' });
    expect(useAppStore.getState().preferences.theme).toBe('dark');
    updatePreferences({ language: 'es' });
    expect(useAppStore.getState().preferences.language).toBe('es');
  });
});

describe('usePatientStore', () => {
  beforeEach(() => {
    usePatientStore.setState({
      analysisCache: {},
      selectedPatientId: null,
      patients: [],
      patientsLoading: false,
      patientsError: null,
    });
  });

  it('sets analysis result', () => {
    const { setAnalysisResult } = usePatientStore.getState();
    const result = {
      patient_id: 'test-123',
      status: 'completed',
      risk_scores: { cardiovascular: 0.75 },
    };
    setAnalysisResult('test-123', result);
    expect(usePatientStore.getState().analysisCache['test-123']).toEqual(result);
  });

  it('gets analysis result', () => {
    const { setAnalysisResult, getAnalysisResult } = usePatientStore.getState();
    const result = { patient_id: 'test-456', status: 'completed' };
    setAnalysisResult('test-456', result);
    expect(getAnalysisResult('test-456')).toEqual(result);
    expect(getAnalysisResult('nonexistent')).toBeUndefined();
  });

  it('sets selected patient', () => {
    const { setSelectedPatientId } = usePatientStore.getState();
    setSelectedPatientId('patient-789');
    expect(usePatientStore.getState().selectedPatientId).toBe('patient-789');
  });

  it('clears analysis cache', () => {
    const { setAnalysisResult, clearAnalysisCache } = usePatientStore.getState();
    setAnalysisResult('p1', { patient_id: 'p1' });
    setAnalysisResult('p2', { patient_id: 'p2' });
    clearAnalysisCache();
    expect(usePatientStore.getState().analysisCache).toEqual({});
  });
});

describe('useSystemStore', () => {
  beforeEach(() => {
    useSystemStore.setState({
      healthStatus: null,
      adaptersStatus: null,
      lastHealthCheck: null,
    });
  });

  it('sets health status', () => {
    const { setHealthStatus } = useSystemStore.getState();
    const status = { status: 'healthy', service: 'api', version: '1.0.0' };
    setHealthStatus(status);
    expect(useSystemStore.getState().healthStatus).toEqual(status);
  });

  it('sets adapters status', () => {
    const { setAdaptersStatus } = useSystemStore.getState();
    const status = { status: 'ok', active_adapters: ['cardiology'] };
    setAdaptersStatus(status);
    expect(useSystemStore.getState().adaptersStatus).toEqual(status);
  });

  it('updates last health check', () => {
    const { setHealthStatus } = useSystemStore.getState();
    setHealthStatus({ status: 'healthy', service: 'api', version: '1.0.0' });
    expect(useSystemStore.getState().lastHealthCheck).not.toBeNull();
  });
});

describe('useQueryStore', () => {
  beforeEach(() => {
    useQueryStore.setState({
      queryHistory: [],
      queryLoading: false,
      queryError: null,
    });
  });

  it('adds to query history', () => {
    const { addToHistory } = useQueryStore.getState();
    addToHistory({
      question: 'What is the diagnosis?',
      answer: 'Based on the symptoms...',
    });
    const history = useQueryStore.getState().queryHistory;
    expect(history).toHaveLength(1);
    expect(history[0].question).toBe('What is the diagnosis?');
  });

  it('limits history size', () => {
    const { addToHistory } = useQueryStore.getState();
    for (let i = 0; i < 60; i++) {
      addToHistory({ question: `Q${i}`, answer: `A${i}` });
    }
    expect(useQueryStore.getState().queryHistory.length).toBeLessThanOrEqual(50);
  });

  it('clears history', () => {
    const { addToHistory, clearHistory } = useQueryStore.getState();
    addToHistory({ question: 'Q1', answer: 'A1' });
    addToHistory({ question: 'Q2', answer: 'A2' });
    clearHistory();
    expect(useQueryStore.getState().queryHistory).toHaveLength(0);
  });
});
