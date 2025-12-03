# API Security Reference

## Overview

This document describes the security controls implemented in the AI Healthcare API.

---

## Authentication

### Bearer Token Authentication

All protected endpoints require a valid JWT bearer token:

```http
Authorization: Bearer <token>
```

### Token Requirements
| Requirement | Value |
|-------------|-------|
| Algorithm | RS256 (production), HS256 (demo) |
| Max lifetime | 1 hour |
| Issuer validation | ✅ Required |
| Audience validation | ✅ Required |

### SMART-on-FHIR Scopes

| Scope | Description |
|-------|-------------|
| `patient/*.read` | Read patient data |
| `patient/*.write` | Write patient data |
| `user/*.read` | Read user profile |
| `user/*.write` | Update user profile |
| `system/*.read` | Read system data |
| `system/*.manage` | Admin operations |

### Token Context

Authenticated requests have access to:
```python
{
    "access_token": "...",
    "scopes": ["patient/*.read", "user/*.read"],
    "clinician_roles": ["physician", "nurse"],
    "subject": "user-id-123",
    "patient": "patient-id-456"  # If patient-scoped
}
```

---

## Authorization

### Role-Based Access Control (RBAC)

| Role | Default Scopes | Description |
|------|----------------|-------------|
| Clinician | `patient/*.read`, `user/*.read` | View patient data |
| Provider | `patient/*.*` | Full patient access |
| Admin | `system/*.*` | System administration |
| Auditor | `system/*.read` | Read-only audit access |

### Endpoint Protection

```python
from backend.security import auth_dependency

@app.get("/api/v1/patient/{id}")
async def get_patient(
    id: str,
    token: TokenContext = Depends(auth_dependency({"patient/*.read"}))
):
    # Only accessible with patient/*.read scope
    ...
```

---

## Rate Limiting

### Default Limits

| Limit | Value | Configurable |
|-------|-------|--------------|
| Per minute | 60 | `RATE_LIMIT_PER_MINUTE` |
| Per hour | 1000 | `RATE_LIMIT_PER_HOUR` |
| Burst size | 10 | `RATE_LIMIT_BURST` |

### Response Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1234567890
```

### Rate Limit Exceeded

```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many requests",
    "retry_after": 30
}
```

---

## Security Headers

All responses include:

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `Content-Security-Policy` | `default-src 'self'...` | XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Privacy |
| `Permissions-Policy` | `geolocation=()...` | Feature restrictions |

---

## Input Validation

### Request Size Limits

| Limit | Value |
|-------|-------|
| Max request body | 10 MB |
| Max file upload | 50 MB |
| Max query length | 500 chars |
| Max path length | 2000 chars |

### Content Validation

- JSON schema validation via Pydantic
- SQL injection prevention via ORM
- XSS prevention via output encoding

---

## CORS Configuration

```python
allow_origins=["http://localhost:3000"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"]
```

Configure via: `CORS_ORIGINS` environment variable

---

## Audit Logging

### Logged Events

| Event | Logged Data |
|-------|-------------|
| Authentication | User, IP, success/failure |
| Authorization | User, resource, decision |
| PHI Access | User, patient ID, data type |
| Admin Actions | User, action, target |

### Log Format

```json
{
    "event_id": "uuid",
    "timestamp": "2026-01-08T12:00:00Z",
    "event_type": "data.phi.access",
    "actor": "user-123",
    "action": "GET /api/v1/patient/456",
    "outcome": "success"
}
```

---

## Error Handling

### Secure Error Responses

Production errors do not expose stack traces:

```json
{
    "error": "internal_error",
    "message": "An unexpected error occurred",
    "correlation_id": "abc123"
}
```

Debug mode (not for production):
```json
{
    "error": "ValueError",
    "message": "Invalid patient ID",
    "detail": "Patient ID must be alphanumeric",
    "correlation_id": "abc123"
}
```

---

## Best Practices

### For API Consumers

1. **Store tokens securely** - Use secure storage, not localStorage
2. **Refresh tokens** - Implement token refresh before expiry
3. **Handle 401/403** - Redirect to login on auth errors
4. **Use HTTPS** - Never send tokens over HTTP
5. **Validate responses** - Check for expected schema

### For Developers

1. **Use auth_dependency** - All protected endpoints
2. **Validate inputs** - Use Pydantic models
3. **Log securely** - Use SecureLogger for PHI
4. **Test security** - Run OWASP tests regularly
