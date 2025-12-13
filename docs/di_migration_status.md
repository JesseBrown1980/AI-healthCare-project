# DI Migration Status Report

## Endpoints using dependency injection container accessors
- `/api/v1/health` uses `Depends(get_container)` to inject `ServiceContainer` alongside auth context for vendor selection and health metadata. 【F:backend/main.py†L667-L685】

## Endpoints still referencing global singletons
The following routes rely on module-level globals instead of injected services:
- Cache maintenance: `/api/v1/cache/clear` directly clears `patient_summary_cache`, `analysis_job_manager`, and `patient_analyzer` history. 【F:backend/main.py†L688-L710】
- Notification registration: `/api/v1/register-device` and `/api/v1/notifications/register` call the global `notifier` via `_register_device_token`. 【F:backend/main.py†L713-L735】
- Patient roster and summaries: `/api/v1/patients`, `/api/v1/patients/dashboard`, `/api/v1/dashboard-summary`, and helper flows use `patient_analyzer`, `fhir_connector`, and `patient_summary_cache`. 【F:backend/main.py†L737-L847】【F:backend/main.py†L1005-L1067】
- Alerts and analysis execution: `/api/v1/alerts`, `/api/v1/analyze-patient`, and websocket `/ws/patient-updates` depend on `patient_analyzer`, `analysis_job_manager`, and the broadcast infrastructure. 【F:backend/main.py†L849-L992】【F:backend/main.py†L994-L1049】
- FHIR access and explainability: `/api/v1/patient/{patient_id}/fhir` and `/api/v1/patient/{patient_id}/explain` read from `fhir_connector`, `audit_service`, and `patient_analyzer`. 【F:backend/main.py†L1071-L1177】
- Model and tooling endpoints: `/api/v1/query`, `/api/v1/feedback`, `/api/v1/adapters`, `/api/v1/adapters/activate`, and `/api/v1/stats` reference `llm_engine`, `rag_fusion`, `aot_reasoner`, `mlc_learning`, and `s_lora_manager` globals. 【F:backend/main.py†L1179-L1291】【F:backend/main.py†L1293-L1378】

## Global mutable state to scope through DI
The module initializes several mutable globals that should be container-managed:
- Analysis history and cache: `analysis_job_manager`, `analysis_history_limit`, and associated queues for deduplicating analysis work. 【F:backend/main.py†L68-L80】【F:backend/main.py†L139-L159】【F:backend/main.py†L688-L710】
- Patient summary cache: `patient_summary_cache` stores derived dashboard summaries per patient. 【F:backend/main.py†L79-L80】【F:backend/main.py†L1027-L1049】
- Websocket registry: `analysis_update_queue`, `active_websockets`, and `broadcast_task` track connected clients and pending updates. 【F:backend/main.py†L65-L67】【F:backend/main.py†L160-L170】【F:backend/main.py†L994-L1049】
- Service singletons: connectors and engines (FHIR, LLM, RAG, S-LoRA, MLC, AoT, notifier, audit) are assigned from `ServiceContainer` into globals during startup and used directly afterward. 【F:backend/main.py†L53-L80】【F:backend/main.py†L139-L159】【F:backend/main.py†L737-L1378】

## Recommended migration order
1. **Websocket infrastructure first**: wrap `analysis_update_queue`, `active_websockets`, and `broadcast_task` in DI scopes to ensure clean startup/shutdown semantics and avoid lingering connections. 【F:backend/main.py†L65-L67】【F:backend/main.py†L160-L170】【F:backend/main.py†L994-L1049】
2. **Analysis caching layer**: migrate `analysis_job_manager` and analysis history handling to container-managed state so `/api/v1/analyze-patient` and cache-clearing flows stop mutating globals. 【F:backend/main.py†L68-L80】【F:backend/main.py†L688-L710】【F:backend/main.py†L849-L992】
3. **Patient summary cache**: move `patient_summary_cache` and dashboard helpers to DI to reduce shared mutable state across requests. 【F:backend/main.py†L79-L80】【F:backend/main.py†L1005-L1067】
4. **Service singletons**: gradually remove module-level globals for connectors/engines (FHIR, LLM, RAG, notifier, audit, etc.) and inject them per-request, ensuring health and auth middleware can consume the container without direct globals. 【F:backend/main.py†L53-L80】【F:backend/main.py†L139-L159】【F:backend/main.py†L667-L685】【F:backend/main.py†L737-L1378】
