import Constants from 'expo-constants';

const defaultBaseUrl = Constants.expoConfig?.extra?.apiBaseUrl || '';

export class ApiClient {
  constructor(token, baseUrl = defaultBaseUrl) {
    this.token = token;
    this.baseUrl = baseUrl?.replace(/\/$/, '') || '';
  }

  async request(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed with ${response.status}`);
    }
    return response.json();
  }

  login(credentials) {
    return this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  fetchPatients() {
    return this.request('/api/v1/patients');
  }

  fetchAlerts() {
    return this.request('/api/v1/alerts?limit=25');
  }

  analyzePatient(patientId) {
    return this.request('/api/v1/analyze-patient', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId }),
    });
  }

  registerPushToken(pushToken) {
    return this.request('/api/v1/notifications/register', {
      method: 'POST',
      body: JSON.stringify({ push_token: pushToken }),
    });
  }
}
