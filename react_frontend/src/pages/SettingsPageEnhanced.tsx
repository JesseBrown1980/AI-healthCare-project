/**
 * Enhanced Settings Page
 * User preferences and application settings with full configuration options
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useAppStore } from '../store';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../hooks';
import { getHealthStatus, getAdaptersStatus } from '../api';
import type { HealthStatus, AdaptersStatus, AdapterInfo } from '../api/types';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Input,
  Select,
  Badge,
  Spinner,
  Tabs,
  TabPanel,
} from '../components/ui';
import './SettingsPageEnhanced.css';

// ============================================================================
// Settings Page Component
// ============================================================================

const SettingsPageEnhanced: React.FC = () => {
  const { userEmail, isAuthenticated } = useAuth();
  const { preferences, updatePreferences } = useAppStore();
  const { success, error: notifyError } = useNotification();

  // Local state
  const [activeTab, setActiveTab] = useState('profile');
  const [localPrefs, setLocalPrefs] = useState(preferences);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [adapters, setAdapters] = useState<AdaptersStatus | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch system status
  useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      try {
        const [health, adapterList] = await Promise.all([
          getHealthStatus().catch(() => null),
          getAdaptersStatus().catch(() => null),
        ]);
        setHealthStatus(health);
        setAdapters(adapterList);
      } catch (err) {
        notifyError('Error', 'Failed to load system status');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, [notifyError]);

  const isHealthy = useMemo(() => {
    const status = healthStatus?.status?.toLowerCase();
    return status === 'healthy' || status === 'ok' || status === 'operational';
  }, [healthStatus]);

  const handleSave = () => {
    updatePreferences(localPrefs);
    success('Settings Saved', 'Your preferences have been updated');
  };

  const handleReset = () => {
    const defaultPrefs = {
      theme: 'system' as const,
      language: 'en',
      dashboardLayout: 'grid' as const,
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
    };
    updatePreferences(defaultPrefs);
    setLocalPrefs(defaultPrefs);
    success('Settings Reset', 'Preferences have been reset to defaults');
  };

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'display', label: 'Display' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'clinical', label: 'Clinical' },
    { id: 'system', label: 'System Status' },
  ];

  // Get adapters as array for display
  const adaptersList: AdapterInfo[] = useMemo(() => {
    if (!adapters?.adapters) return [];
    return Object.values(adapters.adapters);
  }, [adapters]);

  return (
    <div className="settings-page">
      <header className="settings-page__header">
        <h1 className="settings-page__title">Settings</h1>
        <p className="settings-page__subtitle">
          Manage your account, preferences, and system configuration
        </p>
      </header>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      <div className="settings-page__content">
        {/* Profile Tab */}
        <TabPanel tabId="profile" activeTab={activeTab}>
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Your account details and authentication status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="settings-form">
                <div className="settings-form__field">
                  <label>Email</label>
                  <Input value={userEmail ?? 'Not logged in'} disabled />
                </div>
                <div className="settings-form__field">
                  <label>Account Status</label>
                  <Badge variant={isAuthenticated ? 'success' : 'default'}>
                    {isAuthenticated ? 'Authenticated' : 'Not Authenticated'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabPanel>

        {/* Display Tab */}
        <TabPanel tabId="display" activeTab={activeTab}>
          <Card>
            <CardHeader>
              <CardTitle>Display Preferences</CardTitle>
              <CardDescription>Customize the appearance of the application</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="settings-form">
                <div className="settings-form__field">
                  <label>Theme</label>
                  <Select
                    options={[
                      { value: 'light', label: 'Light' },
                      { value: 'dark', label: 'Dark' },
                      { value: 'system', label: 'System Default' },
                    ]}
                    value={localPrefs.theme}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, theme: v as 'light' | 'dark' | 'system' })}
                  />
                  <span className="settings-form__hint">Choose your preferred color scheme</span>
                </div>
                <div className="settings-form__field">
                  <label>Language</label>
                  <Select
                    options={[
                      { value: 'en', label: 'English' },
                      { value: 'es', label: 'Spanish' },
                      { value: 'fr', label: 'French' },
                      { value: 'de', label: 'German' },
                    ]}
                    value={localPrefs.language}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, language: v })}
                  />
                </div>
                <div className="settings-form__field">
                  <label>Date Format</label>
                  <Select
                    options={[
                      { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (US)' },
                      { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (EU)' },
                      { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (ISO)' },
                    ]}
                    value={localPrefs.dateFormat}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, dateFormat: v })}
                  />
                </div>
                <div className="settings-form__field">
                  <label>Time Format</label>
                  <Select
                    options={[
                      { value: '12h', label: '12-hour (AM/PM)' },
                      { value: '24h', label: '24-hour' },
                    ]}
                    value={localPrefs.timeFormat ?? '12h'}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, timeFormat: v })}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabPanel>

        {/* Dashboard Tab */}
        <TabPanel tabId="dashboard" activeTab={activeTab}>
          <Card>
            <CardHeader>
              <CardTitle>Dashboard Preferences</CardTitle>
              <CardDescription>Configure how the dashboard displays and updates</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="settings-form">
                <div className="settings-form__field settings-form__field--checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={localPrefs.autoRefresh}
                      onChange={(e) => setLocalPrefs({ ...localPrefs, autoRefresh: e.target.checked })}
                    />
                    Enable auto-refresh
                  </label>
                  <span className="settings-form__hint">
                    Automatically refresh dashboard data at regular intervals
                  </span>
                </div>
                {localPrefs.autoRefresh && (
                  <div className="settings-form__field">
                    <label>Refresh Interval (seconds)</label>
                    <Input
                      type="number"
                      min={30}
                      max={300}
                      value={localPrefs.refreshInterval}
                      onChange={(e) =>
                        setLocalPrefs({ ...localPrefs, refreshInterval: parseInt(e.target.value) || 60 })
                      }
                    />
                    <span className="settings-form__hint">Between 30 and 300 seconds</span>
                  </div>
                )}
                <div className="settings-form__field settings-form__field--checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={localPrefs.showNotifications}
                      onChange={(e) =>
                        setLocalPrefs({ ...localPrefs, showNotifications: e.target.checked })
                      }
                    />
                    Show notifications
                  </label>
                </div>
                <div className="settings-form__field settings-form__field--checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={localPrefs.compactView}
                      onChange={(e) => setLocalPrefs({ ...localPrefs, compactView: e.target.checked })}
                    />
                    Compact view
                  </label>
                </div>
                <div className="settings-form__field">
                  <label>Default View</label>
                  <Select
                    options={[
                      { value: 'grid', label: 'Grid View' },
                      { value: 'list', label: 'List View' },
                    ]}
                    value={localPrefs.defaultView ?? 'grid'}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, defaultView: v })}
                  />
                </div>
                <div className="settings-form__field">
                  <label>Items Per Page</label>
                  <Select
                    options={[
                      { value: '10', label: '10' },
                      { value: '25', label: '25' },
                      { value: '50', label: '50' },
                      { value: '100', label: '100' },
                    ]}
                    value={String(localPrefs.itemsPerPage ?? 25)}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, itemsPerPage: parseInt(v) })}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabPanel>

        {/* Clinical Tab */}
        <TabPanel tabId="clinical" activeTab={activeTab}>
          <Card>
            <CardHeader>
              <CardTitle>Clinical Analysis Preferences</CardTitle>
              <CardDescription>Configure default settings for patient analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="settings-form">
                <div className="settings-form__field">
                  <label>Default Specialty</label>
                  <Select
                    options={[
                      { value: 'auto', label: 'Auto-detect' },
                      { value: 'cardiology', label: 'Cardiology' },
                      { value: 'oncology', label: 'Oncology' },
                      { value: 'neurology', label: 'Neurology' },
                      { value: 'endocrinology', label: 'Endocrinology' },
                      { value: 'pulmonology', label: 'Pulmonology' },
                    ]}
                    value={localPrefs.defaultSpecialty}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, defaultSpecialty: v })}
                  />
                </div>
                <div className="settings-form__field settings-form__field--checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={localPrefs.includeReasoningByDefault}
                      onChange={(e) =>
                        setLocalPrefs({ ...localPrefs, includeReasoningByDefault: e.target.checked })
                      }
                    />
                    Include reasoning by default
                  </label>
                </div>
                <div className="settings-form__field settings-form__field--checkbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={localPrefs.showConfidenceScores ?? true}
                      onChange={(e) =>
                        setLocalPrefs({ ...localPrefs, showConfidenceScores: e.target.checked })
                      }
                    />
                    Show confidence scores
                  </label>
                </div>
                <div className="settings-form__field">
                  <label>Risk Threshold for Alerts</label>
                  <Select
                    options={[
                      { value: '0.5', label: 'Medium (50%+)' },
                      { value: '0.7', label: 'High (70%+)' },
                      { value: '0.9', label: 'Critical (90%+)' },
                    ]}
                    value={String(localPrefs.riskAlertThreshold ?? 0.7)}
                    onChange={(v) => setLocalPrefs({ ...localPrefs, riskAlertThreshold: parseFloat(v) })}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabPanel>

        {/* System Status Tab */}
        <TabPanel tabId="system" activeTab={activeTab}>
          {loading ? (
            <div className="settings-loading">
              <Spinner size="lg" />
              <p>Loading system status...</p>
            </div>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>API Connection</CardTitle>
                  <Badge variant={isHealthy ? 'success' : 'critical'}>
                    {isHealthy ? 'Healthy' : 'Unavailable'}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="settings-form">
                    <div className="settings-form__field">
                      <label>Service</label>
                      <span>{healthStatus?.service ?? 'Unknown'}</span>
                    </div>
                    <div className="settings-form__field">
                      <label>Version</label>
                      <span>{healthStatus?.version ?? 'Unknown'}</span>
                    </div>
                    {healthStatus?.uptime !== undefined && (
                      <div className="settings-form__field">
                        <label>Uptime</label>
                        <span>{formatUptime(healthStatus.uptime)}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="settings-card--mt">
                <CardHeader>
                  <CardTitle>AI Adapters</CardTitle>
                  <CardDescription>
                    {adaptersList.filter((a) => a.loaded).length} / {adaptersList.length} loaded
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {adaptersList.length === 0 ? (
                    <p>No adapters available</p>
                  ) : (
                    <div className="adapters-list">
                      {adaptersList.map((adapter) => (
                        <div key={adapter.name} className="adapter-item">
                          <span className="adapter-item__name">{adapter.name}</span>
                          <Badge variant={adapter.loaded ? 'success' : 'default'} size="sm">
                            {adapter.loaded ? 'Loaded' : 'Not Loaded'}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabPanel>
      </div>

      {/* Save/Reset Buttons */}
      {activeTab !== 'system' && (
        <div className="settings-page__actions">
          <Button variant="outline" onClick={handleReset}>
            Reset to Defaults
          </Button>
          <Button variant="primary" onClick={handleSave}>
            Save Changes
          </Button>
        </div>
      )}
    </div>
  );
};

// Helper function
function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  return parts.join(' ') || '< 1m';
}

export default SettingsPageEnhanced;
