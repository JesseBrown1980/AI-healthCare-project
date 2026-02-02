# Risk Management File
**Project**: AI Healthcare Assistant
**Compliance Standard**: ISO 14971:2019
**Date**: 2026-02-01

## 1. Scope
This document identifies potential hazards associated with the use of the AI Healthcare Assistant, estimates the associated risks, and defines risk control measures.

## 2. Risk Acceptance Matrix

| Severity \ Probability | Frequent (5) | Probable (4) | Occasional (3) | Remote (2) | Improbable (1) |
|:---|:---|:---|:---|:---|:---|
| **Catastrophic (5)** | Unacceptable | Unacceptable | Unacceptable | ALARP | ALARP |
| **Critical (4)** | Unacceptable | Unacceptable | ALARP | ALARP | Acceptable |
| **Serious (3)** | Unacceptable | ALARP | ALARP | Acceptable | Acceptable |
| **Minor (2)** | ALARP | Acceptable | Acceptable | Acceptable | Acceptable |
| **Negligible (1)** | Acceptable | Acceptable | Acceptable | Acceptable | Acceptable |

*ALARP = As Low As Reasonably Practicable*

## 3. Hazard Analysis

| ID | Hazard | Cause | Effect | Initial Risk (S x P) | Risk Control Measure | Residual Risk |
|:---|:---|:---|:---|:---|:---|:---|
| **H-01** | Incorrect Medication Recommendation | LLM "Hallucination" or outdated training data | Patient receives wrong dosage or contraindicated drug | Critical (4) x Occasional (3) = **High** | 1. RAG-Fusion to ground answers in current guidelines.<br>2. Mandatory disclaimer.<br>3. Human-in-the-loop verification required. | Minor (2) x Remote (2) = **Acceptable** |
| **H-02** | Missed Critical Alert | System downtime or API failure | Delayed treatment for critical condition | Critical (4) x Remote (2) = **ALARP** | 1. Redundant monitoring.<br>2. Fallback to raw EHR data if AI fails.<br>3. 99.9% Uptime SLA. | Critical (4) x Improbable (1) = **Acceptable** |
| **H-03** | Data Leakage | Unencrypted logs or weak auth | PHI exposure (HIPAA violation) | Serious (3) x Remote (2) = **Acceptable** | 1. Crypto-shredding for logs.<br>2. Strict OAuth2 RBAC.<br>3. Anomaly detection system. | Serious (3) x Improbable (1) = **Acceptable** |
| **H-04** | Bias in Risk Scoring | Training data bias against certain demographics | Unequal care recommendations | Serious (3) x Occasional (3) = **ALARP** | 1. Diverse dataset validation.<br>2. Demographic parity testing.<br>3. Model transparency reports. | Serious (3) x Remote (2) = **Acceptable** |
| **H-05** | Injection Attacks (XSS/SQLi) | Improperly sanitized inputs (query, path, body) | System compromise or data theft | Critical (4) x Occasional (3) = **ALARP** | 1. Automated input sanitization in middleware.<br>2. Strict mode validation.<br>3. Body buffering and scanning. | Minor (2) x Remote (2) = **Acceptable** |
| **H-06** | Browser-Side Attacks | Missing or weak security headers (CSP, HSTS) | Clickjacking, MIME-sniffing, script injection | Serious (3) x Occasional (3) = **ALARP** | 1. Enforced security headers middleware.<br>2. Tightened CSP in production.<br>3. Removed 'unsafe-inline'. | Negligible (1) x Remote (2) = **Acceptable** |

## 4. Risk Control Verification
All risk control measures are verified through the Traceability Matrix (see `TRACEABILITY_MATRIX.md`).

## 5. Conclusion
The residual risks are considered acceptable given the benefits of the system and the robust mitigation strategies in place.
