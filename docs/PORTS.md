# Port Conventions

The stack uses the following port assignments by default:

| Component | Port | Notes |
| --- | --- | --- |
| Streamlit frontend | 3000 | Default Streamlit UI served from `frontend/app.py`; also the target for the desktop wrapper (`DESKTOP_APP_URL`). |
| Backend API | 8000 | FastAPI service exposed at `/api/v1`; matches the default `PORT` in `backend/main.py` and Docker mappings. |
| FHIR test server | 8080 | Optional HAPI FHIR container for local testing; aligns with the default `FHIR_SERVER_URL` (`http://localhost:8080/fhir`). |

Use these defaults across local runs, Docker, and the desktop wrapper to keep the stack aligned. If a port is already in use, adjust the affected service and update any dependent URLs (e.g., `CORS_ORIGINS` or `DESKTOP_APP_URL`) accordingly.

- The React dev server also binds to port 3000 (`npm run dev` in `react_frontend/`). Run only one frontend at a time so Vite and Streamlit do not clash on the same port.
