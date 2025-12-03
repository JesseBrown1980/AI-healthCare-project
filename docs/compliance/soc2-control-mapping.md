# SOC 2 Control Mapping

## Overview

This document maps the AI Healthcare Project's security controls to SOC 2 Trust Service Criteria.

---

## Trust Service Categories

| Category | Description | Coverage |
|----------|-------------|----------|
| **CC** | Common Criteria (Security) | ✅ Implemented |
| **A** | Availability | ⚠️ Partial |
| **PI** | Processing Integrity | ⚠️ Partial |
| **C** | Confidentiality | ✅ Implemented |
| **P** | Privacy | ✅ Implemented |

---

## Common Criteria (Security)

### CC1: Control Environment

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC1.1 | Integrity and ethical values | Code of conduct | `CONTRIBUTING.md` |
| CC1.2 | Board oversight | N/A (startup) | - |
| CC1.3 | Management structure | Documented roles | `docs/security/` |
| CC1.4 | Commitment to competence | Hiring standards | - |
| CC1.5 | Accountability | Role definitions | RBAC implementation |

### CC2: Communication and Information

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC2.1 | Internal communication | Documentation | `docs/`, `README.md` |
| CC2.2 | External communication | Public docs | GitHub, API docs |
| CC2.3 | Third-party communication | Vendor agreements | `vendor-management-policy.md` |

### CC3: Risk Assessment

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC3.1 | Risk objectives | Security policies | `docs/security/` |
| CC3.2 | Risk identification | Security scanning | `security.yml` workflow |
| CC3.3 | Fraud risk | Access controls | RBAC, audit logging |
| CC3.4 | Change risk | Change management | `change-management-policy.md` |

### CC4: Monitoring Activities

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC4.1 | Ongoing evaluations | CI/CD, security scans | GitHub Actions |
| CC4.2 | Deficiency communication | Alerting | GitHub Issues, alerts |

### CC5: Control Activities

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC5.1 | Control selection | Security controls | `backend/security.py` |
| CC5.2 | Technology controls | Automated scanning | `security.yml` |
| CC5.3 | Policy deployment | Documentation | `docs/security/` |

### CC6: Logical and Physical Access

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC6.1 | Logical access | RBAC, JWT validation | `backend/security.py` |
| CC6.2 | Access provisioning | User management | Admin APIs |
| CC6.3 | Access removal | Token revocation | Session management |
| CC6.4 | Access review | Quarterly reviews | Policy documented |
| CC6.5 | Physical access | Cloud provider | AWS/Azure SOC 2 |
| CC6.6 | System boundaries | Network policies | VPC, firewall |
| CC6.7 | Transmission security | TLS 1.3, HSTS | `security_headers.py` |
| CC6.8 | Malware prevention | Dependency scanning | Dependabot, pip-audit |

### CC7: System Operations

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC7.1 | Change detection | Audit logging | `backend/audit/` |
| CC7.2 | Incident monitoring | Logging, alerting | Audit middleware |
| CC7.3 | Incident evaluation | IRP | `incident-response-plan.md` |
| CC7.4 | Incident response | Runbooks | `incident-response-plan.md` |
| CC7.5 | Incident recovery | DR procedures | Documented |

### CC8: Change Management

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC8.1 | Change authorization | PR reviews | GitHub branch protection |

### CC9: Risk Mitigation

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| CC9.1 | Risk identification | Security scanning | SAST, DAST |
| CC9.2 | Vendor risk | Vendor assessment | `vendor-management-policy.md` |

---

## Confidentiality (C)

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| C1.1 | Data classification | Policy documented | `data-protection-policy.md` |
| C1.2 | Data disposal | Retention policies | Compliance policies |

---

## Privacy (P)

| Control | Description | Implementation | Evidence |
|---------|-------------|----------------|----------|
| P1.1 | Privacy notice | Terms documented | Privacy policy |
| P2.1 | Consent | GDPR consent | Regional policies |
| P3.1 | Collection limitation | Minimum necessary | Data protection policy |
| P4.1 | Use limitation | Purpose specification | Compliance policies |
| P5.1 | Access | User data export | Delete/export APIs |
| P6.1 | Disclosure | Audit logging | Audit trail |
| P7.1 | Quality | Data validation | FHIR validation |
| P8.1 | Monitoring | Audit logs | Audit middleware |

---

## Implementation Files

| Component | Location |
|-----------|----------|
| JWT Validation | `backend/security.py` |
| Security Headers | `backend/middleware/security_headers.py` |
| Compliance Policies | `backend/config/compliance_policies.py` |
| Audit Logging | `backend/audit/` |
| Security Scanning | `.github/workflows/security.yml` |
| Dependency Updates | `.github/dependabot.yml` |

---

## Audit Evidence Collection

### Automated Evidence
- CI/CD logs (GitHub Actions)
- Audit logs (JSON files)
- Security scan reports
- Dependency vulnerability reports

### Manual Evidence
- Access review records
- Incident reports
- Vendor assessments
- Training records
