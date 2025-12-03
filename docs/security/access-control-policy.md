# Access Control Policy

**Document ID:** SEC-POL-001  
**Version:** 1.0  
**Last Updated:** January 2026  
**Classification:** Internal

---

## 1. Purpose

This policy establishes access control requirements for the AI Healthcare Project to protect patient data, ensure HIPAA compliance, and maintain SOC 2 security standards.

---

## 2. Scope

Applies to all users, systems, and services accessing the AI Healthcare platform, including:
- Backend API services
- Frontend applications
- Database systems
- Third-party integrations (FHIR servers, LLM providers)

---

## 3. Authentication Requirements

### 3.1 SMART-on-FHIR Authentication
- All API access requires OAuth 2.0 bearer tokens
- Tokens validated against IAM JWKS endpoint
- Token expiry enforced (max 1 hour)

### 3.2 Multi-Factor Authentication
- Required for administrative access
- Required for EU region deployments (GDPR)
- Configurable via `require_2fa` policy flag

### 3.3 Session Management
- Session tokens expire after configurable timeout
- Concurrent session limits enforced
- Session invalidation on logout

---

## 4. Authorization Model

### 4.1 Role-Based Access Control (RBAC)
| Role | Scopes | Description |
|------|--------|-------------|
| Clinician | `patient/*.read`, `user/*.read` | View patient data |
| Provider | `patient/*.*`, `user/*.read` | Full patient access |
| Admin | `system/*.*` | System administration |
| Auditor | `system/*.read` | Read-only audit access |

### 4.2 Scope Enforcement
```python
# Required scopes defined per endpoint
SCOPE_PATIENT_READ = "patient/*.read"
SCOPE_PATIENT_WRITE = "patient/*.write"
SCOPE_SYSTEM_MANAGE = "system/*.manage"
```

### 4.3 Least Privilege
- Users receive minimum required permissions
- Elevated access requires explicit approval
- Temporary access expires automatically

---

## 5. Access Reviews

### 5.1 Periodic Reviews
- Quarterly access reviews for all users
- Immediate review upon role change
- Annual recertification required

### 5.2 Revocation
- Access revoked within 24 hours of termination
- Emergency revocation within 1 hour
- All sessions invalidated on revocation

---

## 6. Technical Controls

### 6.1 Implementation
- JWT validation via `backend/security.py`
- Token context includes scopes, roles, and claims
- Failed authentication logged to audit trail

### 6.2 Monitoring
- Failed login attempts monitored
- Rate limiting on authentication endpoints
- Alerts on suspicious patterns

---

## 7. Compliance

| Regulation | Requirement | Implementation |
|------------|-------------|----------------|
| HIPAA | Unique user identification | JWT `sub` claim |
| HIPAA | Emergency access procedure | Admin override with audit |
| SOC 2 | Logical access controls | RBAC with scopes |
| GDPR | Access limitation | Region-based policies |

---

## 8. References

- `backend/security.py` - JWT validation implementation
- `backend/config/compliance_policies.py` - Regional policies
- SOC 2 CC6.1-CC6.8 - Logical and Physical Access Controls
