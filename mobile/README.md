# Clinician Alerts Mobile App

A cross-platform (iOS/Android) Expo application for clinicians to review patient analyses and receive critical alerts.

## Features
- Login with credentials or provide an existing API token
- Configure the API base URL per environment
- View assigned patients and recent alerts
- Trigger `/api/v1/analyze-patient` for a selected patient and view summary, alerts, risk scores, and recommendations
- Receive push notifications for new analyses and critical alerts using Expo push tokens

## Getting started
1. Install dependencies:
   ```bash
   cd mobile
   npm install
   # or
   yarn install
   ```
2. Start the Expo development server:
   ```bash
   npm start
   ```
3. Configure the API URL and token on first launch. The app persists these values securely for later sessions.

## Notes
- Push notifications require running on a physical device. The app automatically registers the Expo push token with the backend via `/api/v1/notifications/register` once authenticated.
- The base API URL defaults to `http://localhost:8000` (configurable via `app.json`).
