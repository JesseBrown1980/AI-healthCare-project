# Security Architecture

## Overview

The AI Healthcare Project implements a defense-in-depth security architecture to protect Protected Health Information (PHI) and ensure HIPAA/SOC 2 compliance.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                              ┌─────▼─────┐
                              │   WAF     │  ← Rate limiting, DDoS protection
                              └─────┬─────┘
                                    │
                              ┌─────▼─────┐
                              │  HTTPS    │  ← TLS 1.3, HSTS
                              │ Termination│
                              └─────┬─────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                           AUTHENTICATION LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  • JWT Validation (JWKS)          • SMART-on-FHIR Scopes               │ │
│  │  • Token Expiry Enforcement       • Clinician Role Validation          │ │
│  │  • MFA Support                    • Session Management                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                           AUTHORIZATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  • RBAC with Scopes              • Endpoint-level Permissions          │ │
│  │  • Patient Context Validation    • Least Privilege Enforcement         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                           MIDDLEWARE LAYER                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │  Security   │ │   Audit     │ │    CORS     │ │   Request Validation   │ │
│  │  Headers    │ │  Logging    │ │  Controls   │ │   (Pydantic)           │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │  Patient    │ │    LLM      │ │    FHIR     │ │   Anomaly Detection    │ │
│  │  Analyzer   │ │   Engine    │ │  Connector  │ │   (GNN)                │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  • Encryption at Rest (AES-256) • Field-level Encryption (PHI)         │ │
│  │  • Database ACLs                • Backup Encryption                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ PostgreSQL  │ │   Redis     │ │  FHIR       │ │   Audit Logs           │ │
│  │ (Primary)   │ │  (Cache)    │ │  Server     │ │   (Immutable)          │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Controls by Layer

### 1. Network Layer
| Control | Implementation |
|---------|----------------|
| TLS 1.3 | Mandatory HTTPS |
| HSTS | 1-year max-age, includeSubDomains |
| Rate Limiting | Per-IP request limits |
| WAF | SQL injection, XSS prevention |

### 2. Authentication Layer
| Control | Implementation |
|---------|----------------|
| JWT Validation | JWKS signature verification |
| Token Expiry | 1-hour maximum |
| MFA | Required for sensitive operations |
| Session Management | Server-side invalidation |

### 3. Authorization Layer
| Control | Implementation |
|---------|----------------|
| RBAC | Scope-based permissions |
| Least Privilege | Minimum required access |
| Context Validation | Patient ID binding |

### 4. Application Layer
| Control | Implementation |
|---------|----------------|
| Input Validation | Pydantic schemas |
| Output Encoding | JSON serialization |
| Error Handling | No stack traces exposed |
| PHI Filtering | Log sanitization |

### 5. Data Layer
| Control | Implementation |
|---------|----------------|
| Encryption at Rest | AES-256 |
| Field Encryption | PHI columns |
| Access Logging | All data access audited |
| Backup Security | Encrypted off-site |

---

## Key Security Components

### backend/security.py
```python
# JWT validation with SMART-on-FHIR scopes
class JWTValidator:
    - JWKS key fetching
    - Signature verification (RS256, HS256)
    - Expiry validation
    - Scope extraction
    - Role validation
```

### backend/middleware/security_headers.py
```python
# OWASP recommended headers
- Strict-Transport-Security
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Content-Security-Policy
- Referrer-Policy
- Permissions-Policy
```

### backend/audit/
```python
# Comprehensive audit logging
- Authentication events
- Authorization decisions
- PHI access
- Admin actions
- Security events
```

---

## Threat Model

| Threat | Mitigation |
|--------|------------|
| Credential theft | JWT expiry, MFA, secure storage |
| Session hijacking | HTTPS, secure cookies, token binding |
| SQL injection | Parameterized queries, ORM |
| XSS | CSP, output encoding |
| CSRF | Token validation, SameSite cookies |
| Data breach | Encryption, access controls, audit |
| Insider threat | Least privilege, audit logging |
| DDoS | Rate limiting, CDN, WAF |

---

## Compliance Summary

| Standard | Requirement | Implementation |
|----------|-------------|----------------|
| HIPAA | Access controls | RBAC, audit logs |
| HIPAA | Encryption | TLS, AES-256 |
| HIPAA | Audit trail | Comprehensive logging |
| SOC 2 | Security | All CC controls |
| GDPR | Data protection | Regional policies |
