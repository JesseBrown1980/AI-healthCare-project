# Deployment Security Guide

## Overview

Security checklist and configuration guide for deploying the AI Healthcare application.

---

## Pre-Deployment Checklist

### Environment Configuration

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure `SECRET_KEY` (minimum 32 characters, random)
- [ ] Configure `DEMO_JWT_SECRET` (if using demo login)
- [ ] Set `TESTING=false`

### HTTPS/TLS

- [ ] TLS 1.3 enabled on load balancer
- [ ] Valid SSL certificate installed
- [ ] HSTS header enabled (`HSTS_ENABLED=true`)
- [ ] HTTP to HTTPS redirect configured

### Authentication

- [ ] Configure `IAM_JWKS_URL` for production IdP
- [ ] Set `SMART_CLIENT_ID` and `SMART_CLIENT_SECRET`
- [ ] Disable demo login (`ENABLE_DEMO_LOGIN=false`)
- [ ] Configure token expiry appropriately

### Database

- [ ] Use encrypted connection (SSL)
- [ ] Configure connection pooling
- [ ] Set up automated backups
- [ ] Enable audit logging

---

## Environment Variables

### Required for Production

```bash
# Core
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<random-32+-chars>

# Authentication
IAM_JWKS_URL=https://your-idp/.well-known/jwks.json
SMART_AUTHORIZATION_URL=https://your-idp/authorize
SMART_TOKEN_URL=https://your-idp/token

# Database
DATABASE_URL=postgresql://user:pass@host:5432/healthcare

# Security
HTTPS_ENFORCEMENT_ENABLED=true
HSTS_ENABLED=true
RATE_LIMIT_ENABLED=true
AUDIT_LOGGING_ENABLED=true
```

### Security Configuration

```bash
# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=10

# Timeouts
REQUEST_TIMEOUT_SECONDS=30

# CORS (restrict to your domains)
CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com

# Logging
AUDIT_LOG_DIR=/var/log/healthcare/audit
LOG_LEVEL=WARNING
```

---

## Infrastructure Security

### Network

```
┌─────────────────────────────────────────────┐
│           Internet                           │
└──────────────────┬──────────────────────────┘
                   │
            ┌──────▼──────┐
            │     WAF     │ ← AWS WAF / Cloudflare
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │ Load Balancer│ ← TLS termination
            └──────┬──────┘
                   │ (HTTPS only)
            ┌──────▼──────┐
            │   App VPC   │
            │ ┌─────────┐ │
            │ │   App   │ │
            │ └────┬────┘ │
            │      │      │
            │ ┌────▼────┐ │
            │ │   DB    │ │ ← Private subnet
            │ └─────────┘ │
            └─────────────┘
```

### Firewall Rules

| Rule | Source | Destination | Port | Action |
|------|--------|-------------|------|--------|
| HTTPS | 0.0.0.0/0 | Load Balancer | 443 | Allow |
| App | Load Balancer | App Servers | 8000 | Allow |
| DB | App Servers | Database | 5432 | Allow |
| SSH | Admin IPs | Bastion | 22 | Allow |
| Default | Any | Any | Any | Deny |

---

## Container Security

### Dockerfile Best Practices

```dockerfile
# Use specific version, not latest
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m appuser
USER appuser

# Don't store secrets in image
# Use environment variables or secrets manager

# Scan for vulnerabilities
# docker scan myimage:latest
```

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    readOnlyRootFilesystem: true
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
```

---

## Secrets Management

### DO NOT

- ❌ Store secrets in code
- ❌ Store secrets in Docker images
- ❌ Use plaintext config files
- ❌ Log secrets

### DO

- ✅ Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- ✅ Use environment variables
- ✅ Rotate secrets regularly
- ✅ Audit secret access

### Example: AWS Secrets Manager

```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Usage
db_password = get_secret('prod/healthcare/db-password')
```

---

## Monitoring & Alerting

### Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| Failed logins | >50/hour | Alert security team |
| Access denied | >100/hour | Investigate |
| Error rate | >5% | Page on-call |
| Latency P99 | >5s | Scale up |

### Log Aggregation

```yaml
# Recommended: Ship logs to SIEM
Logs → Fluentd/Filebeat → Elasticsearch/Splunk → Alerts
```

---

## Incident Response

### Immediate Actions

1. **Contain** - Isolate affected systems
2. **Preserve** - Capture logs and evidence
3. **Notify** - Alert security team
4. **Investigate** - Determine scope
5. **Remediate** - Fix and patch

### Contact Information

- Security Team: security@yourdomain.com
- On-Call: Use PagerDuty/Opsgenie
- Compliance: compliance@yourdomain.com

---

## Compliance Verification

### Pre-Deployment

- [ ] Security scan (Bandit) passed
- [ ] Dependency scan (pip-audit) passed
- [ ] No high/critical vulnerabilities
- [ ] Penetration test completed
- [ ] Security review approved

### Post-Deployment

- [ ] Verify HTTPS working
- [ ] Verify security headers present
- [ ] Verify audit logging active
- [ ] Verify rate limiting working
- [ ] Verify error handling (no stack traces)

---

## Regular Maintenance

| Task | Frequency |
|------|-----------|
| Dependency updates | Weekly |
| Security scans | Daily (CI) |
| Access reviews | Quarterly |
| Penetration tests | Annually |
| Incident response drill | Annually |
| Key rotation | Quarterly |
