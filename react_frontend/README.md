# React Frontend

This Vite + React + TypeScript app provides the UI for the AI Healthcare project. All primary routes are protected by JWT auth and redirect to the login screen when no token is available.

## Authentication
- The frontend uses a simple `AuthContext` that stores the JWT and email in `localStorage`. The token is automatically attached to every API call.
- A demo login endpoint is available at `/api/v1/auth/login` when the backend is started with `ENABLE_DEMO_LOGIN=true` (optionally set `DEMO_LOGIN_EMAIL` and `DEMO_LOGIN_PASSWORD`).
- Default demo credentials are `demo@example.com` / `changeme`; adjust the login form as needed for your environment.
- After signing out, you are redirected to `/login`. Protected routes will bounce unauthenticated users to the same page with a redirect back to their original destination after login.

## Scripts
- `npm run dev` – start the Vite dev server
- `npm run build` – type-check and create a production build
- `npm run lint` – run ESLint against the project

## Environment
Set `VITE_API_BASE_URL` (or `REACT_APP_API_BASE_URL`) to point to the backend API if it differs from `http://localhost:8000/api/v1`.
