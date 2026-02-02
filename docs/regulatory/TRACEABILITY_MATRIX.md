# Traceability Matrix
**Project**: AI Healthcare Assistant
**Version**: 1.0.0
**Date**: 2026-02-01

## Purpose
This document maps high-level product requirements to software components and verification tests, ensuring complete coverage and traceability as required by IEC 62304 and FDA guidance for Software as a Medical Device (SaMD).

## Traceability Table

| Req ID | Requirement Description | Component | Source File | Test Case ID | Test File |
|:---|:---|:---|:---|:---|:---|
| **REQ-01** | System shall retrieve patient demographics from FHIR server | FHIR Connector | `backend/fhir_connector.py` | `test_get_patient_data` | `tests/test_fhir_resource_service.py` |
| **REQ-02** | System shall identify potential drug-drug interactions | Patient Analyzer | `backend/patient_analyzer.py` | `test_analyze_patient_interactions` | `tests/test_patient_analyzer_unit.py` |
| **REQ-03** | System shall calculate aggregate risk score based on vitals and history | Risk Engine | `backend/patient_analyzer.py` | `test_risk_score_calculation` | `tests/test_risk_scoring_service.py` |
| **REQ-04** | AI recommendations shall be grounded in provided medical context | LLM Engine | `backend/llm_engine.py` | `test_recommendation_grounding` | `tests/test_llm_engine.py` |
| **REQ-05** | Audit logs must be encrypted at rest (Crypto-shredding) | Audit Service | `backend/audit/audit_logger.py` | `test_audit_log_encryption` | `tests/test_crypto_shredding.py` |
| **REQ-06** | System shall allow user to delete all personal data (Right to be Forgotten) | Compliance Service | `backend/audit/crypto_shredder.py` | `test_data_deletion` | `tests/test_data_deletion.py` |
| **REQ-07** | Admin users must authenticate via secure token | Auth Service | `backend/security.py` | `test_admin_auth` | `tests/test_security_compliance.py` |
| **REQ-08** | System shall detect and alert on anomalous API access patterns | Anomaly Detector | `backend/anomaly_detector/` | `test_anomaly_detection_logic` | `tests/test_clinical_gnn.py` |
| **REQ-09** | All API responses must include a regulatory disclaimer | Response Formatter | `backend/patient_analyzer.py` | `test_disclaimer_presence` | `tests/test_compliance_phase4.py` |
| **REQ-10** | System shall sanitize all inputs (query, path, body) for XSS and SQLi | Security Middleware | `backend/middleware/input_validation.py` | `test_input_sanitization` | `tests/test_security_hardening.py` |
| **REQ-11** | System shall enforce secure headers (CSP, HSTS) in production | Security Middleware | `backend/middleware/security_headers.py` | `test_security_headers` | `tests/test_security_hardening.py` |

## Verification Status
- **Total Requirements**: 11
- **Implemented**: 11
- **Verified**: 11

## Approval
**Prepared By**: Antigravity Agent
**Reviewed By**: User (Final Approved)
