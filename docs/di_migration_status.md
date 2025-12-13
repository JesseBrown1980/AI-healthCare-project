# DI migration status (backend/main.py)

## Endpoints using DI helpers
- `/api/v1/health` resolves the container via `Depends(get_container)`.【F:backend/main.py†L679-L698】
- `/api/v1/cache/clear` injects `analysis_job_manager` and `patient_analyzer` using DI providers and avoids globals for those dependencies.【F:backend/main.py†L700-L724】
- `/api/v1/analyze-patient` requests analyzer, FHIR connector, analysis job manager, and audit service via DI, but still falls back to globals when the dependency is a `Depends` placeholder.【F:backend/main.py†L890-L927】
- `/api/v1/query` injects `llm_engine`, `rag_fusion`, `aot_reasoner`, and `fhir_connector` via DI helpers.【F:backend/main.py†L1346-L1389】
- Adapter management endpoints (`/api/v1/adapters`, `/api/v1/adapters/activate`) rely on `Depends(get_s_lora_manager)`.【F:backend/main.py†L1477-L1528】

## Endpoints still tied to globals
- Device registration endpoints (`/api/v1/register-device`, `/api/v1/notifications/register`) call the module-level `notifier` directly inside `_register_device_token`.【F:backend/main.py†L727-L764】
- Patient roster and dashboard endpoints (`/api/v1/patients`, `/api/v1/patients/dashboard`, `/api/v1/alerts`, `/api/v1/dashboard-summary`) depend on module globals like `patient_analyzer`, `fhir_connector`, `audit_service`, and `patient_summary_cache` for request handling and caching.【F:backend/main.py†L767-L888】【F:backend/main.py†L1086-L1157】
- Patient FHIR fetch and explain routes (`/api/v1/patient/{patient_id}/fhir`, `/api/v1/patient/{patient_id}/explain`) directly reference global connectors, analyzer, and audit service instances.【F:backend/main.py†L1160-L1255】【F:backend/main.py†L1257-L1343】
- Feedback and system stats endpoints reach into globals for `mlc_learning`, model managers, and audit service rather than DI-injected resources.【F:backend/main.py†L1440-L1558】
- WebSocket handler `/ws/patient-updates` operates on module-level `active_websockets` without DI scoping.【F:backend/main.py†L1065-L1084】

## Shared mutable state
- Global service singletons (`fhir_connector`, `patient_analyzer`, `audit_service`, etc.) and caches (`analysis_job_manager`, `patient_summary_cache`) are created in the lifespan startup and stored at module scope.【F:backend/main.py†L65-L93】【F:backend/main.py†L137-L176】
- Analysis history and cache: `patient_analyzer` tracks analysis history, and `analysis_job_manager` caches analysis results with TTL settings populated from environment variables.【F:backend/main.py†L84-L93】【F:backend/main.py†L700-L724】【F:backend/main.py†L890-L1004】
- Dashboard summary cache: `patient_summary_cache` holds derived summaries keyed by patient ID and is mutated by `_get_patient_summary` and `analyze_patient` responses.【F:backend/main.py†L91-L93】【F:backend/main.py†L584-L606】【F:backend/main.py†L935-L967】
- Real-time channel state: `analysis_update_queue`, `active_websockets`, and `broadcast_task` manage update distribution for WebSocket clients and are initialized globally in `lifespan`.【F:backend/main.py†L77-L80】【F:backend/main.py†L172-L180】【F:backend/main.py†L1008-L1084】

## Recommended migration sequence (5–8 PRs)
1. **Stabilize real-time infra via DI**: move `analysis_update_queue`, `active_websockets`, and `_broadcast_analysis_updates` into container-managed state and inject into `/ws/patient-updates` and `_queue_analysis_update` helpers to avoid global mutations.【F:backend/main.py†L77-L80】【F:backend/main.py†L1008-L1084】
2. **Device notification endpoints**: refactor `_register_device_token` to resolve `Notifier` and `AuditService` from DI, eliminating global `notifier` usage in `/api/v1/register-device` and `/api/v1/notifications/register`.【F:backend/main.py†L727-L764】
3. **Dashboard caches**: inject analyzer, FHIR connector, and summary cache handles into `/api/v1/patients`, `/api/v1/patients/dashboard`, `/api/v1/alerts`, and `/api/v1/dashboard-summary`; ensure cache storage sits in the container instead of module globals.【F:backend/main.py†L767-L888】【F:backend/main.py†L1086-L1157】
4. **FHIR read & explain endpoints**: wire `/api/v1/patient/{patient_id}/fhir` and `/api/v1/patient/{patient_id}/explain` through DI for connector/analyzer/audit access and align with per-request scopes.【F:backend/main.py†L1160-L1255】【F:backend/main.py†L1257-L1343】
5. **MLC feedback & system stats**: inject `mlc_learning`, `rag_fusion`, `s_lora_manager`, and `audit_service` into `/api/v1/feedback` and `/api/v1/stats`, removing direct globals and clarifying state lifetimes.【F:backend/main.py†L1440-L1558】
6. **Finalize analyze/query endpoints**: drop global fallbacks in `/api/v1/analyze-patient` and `/api/v1/query`, ensuring dependencies come only from DI and any caching state (patient summaries, analysis_job_manager) is container-owned.【F:backend/main.py†L890-L1004】【F:backend/main.py†L1346-L1412】
