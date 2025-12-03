# SOC 2 Pre-Audit Readiness Checklist

## Overview

Use this checklist to assess SOC 2 Type II audit readiness before engaging an auditor.

---

## CC1: Control Environment

### Organizational Structure
- [ ] Organizational chart documented
- [ ] Roles and responsibilities defined
- [ ] Security team identified
- [ ] Management oversight established

### Policies
- [ ] Information security policy exists
- [ ] Acceptable use policy documented
- [ ] Code of conduct in place
- [ ] Policies reviewed within last year

---

## CC2: Communication

### Internal
- [ ] Security awareness training conducted
- [ ] Policy acknowledgments collected
- [ ] Incident reporting procedures communicated

### External
- [ ] Privacy policy published
- [ ] Terms of service documented
- [ ] Security contact information available

---

## CC3: Risk Assessment

### Risk Program
- [ ] Risk assessment completed (see `risk-assessment.md`)
- [ ] Risks documented with mitigations
- [ ] Risk register maintained
- [ ] Quarterly risk reviews scheduled

### Vulnerability Management
- [ ] Vulnerability scanning configured (`security.yml`)
- [ ] Penetration test scheduled/completed
- [ ] Remediation process defined
- [ ] Critical vulnerabilities addressed within SLA

---

## CC4: Monitoring

### Logging
- [ ] Audit logging enabled (`AuditMiddleware`)
- [ ] Logs retained per policy (7 years)
- [ ] Log review process defined
- [ ] Alerting configured for critical events

### Metrics
- [ ] Security metrics defined
- [ ] Dashboard/reporting available
- [ ] Trend analysis performed

---

## CC5: Control Activities

### Security Controls
- [ ] Access control implemented (`backend/security.py`)
- [ ] Encryption at rest enabled
- [ ] Encryption in transit (TLS) enforced
- [ ] Security headers configured (`security_headers.py`)

### Automated Controls
- [ ] CI/CD pipeline with security gates
- [ ] Static analysis (Bandit) integrated
- [ ] Dependency scanning (Dependabot/pip-audit)
- [ ] Secret scanning (Gitleaks)

---

## CC6: Logical Access

### Authentication
- [ ] Strong authentication (JWT/OAuth2)
- [ ] Token expiry enforced
- [ ] MFA available for admins
- [ ] Session management implemented

### Authorization
- [ ] RBAC implemented with scopes
- [ ] Least privilege enforced
- [ ] Access requests approved
- [ ] Access reviews conducted quarterly

### Access Removal
- [ ] Offboarding process documented
- [ ] Access removed within 24 hours of termination
- [ ] Quarterly access reviews (use `access-review-template.md`)

---

## CC7: System Operations

### Incident Response
- [ ] Incident response plan exists (`incident-response-plan.md`)
- [ ] IR team identified
- [ ] Runbooks documented
- [ ] Annual tabletop exercise conducted

### Business Continuity
- [ ] Backup procedures documented
- [ ] Recovery testing performed
- [ ] RTO/RPO defined

---

## CC8: Change Management

### Process
- [ ] Change management policy exists (`change-management-policy.md`)
- [ ] Code review required for all changes
- [ ] Testing before deployment
- [ ] Rollback procedures documented

### Evidence
- [ ] Git commit history maintained
- [ ] PR/MR approvals tracked
- [ ] Deployment logs retained

---

## CC9: Vendor Management

### Assessment
- [ ] Vendor inventory maintained
- [ ] Critical vendors assessed (`vendor-management-policy.md`)
- [ ] BAAs in place for PHI access
- [ ] Annual reassessment scheduled

---

## Evidence Collection

### Automated Evidence (Available Now)
- [ ] CI/CD logs (GitHub Actions)
- [ ] Audit logs (JSON files in `audit-logs/`)
- [ ] Security scan reports
- [ ] Git history

### Manual Evidence (Collect Before Audit)
- [ ] Access review records (3-6 months)
- [ ] Training records
- [ ] Incident reports
- [ ] Meeting minutes
- [ ] Policy acknowledgments

---

## Readiness Score

| Category | Ready | Partial | Not Ready |
|----------|-------|---------|-----------|
| CC1 Control Environment | ☐ | ☐ | ☐ |
| CC2 Communication | ☐ | ☐ | ☐ |
| CC3 Risk Assessment | ☐ | ☐ | ☐ |
| CC4 Monitoring | ☐ | ☐ | ☐ |
| CC5 Control Activities | ☐ | ☐ | ☐ |
| CC6 Logical Access | ☐ | ☐ | ☐ |
| CC7 System Operations | ☐ | ☐ | ☐ |
| CC8 Change Management | ☐ | ☐ | ☐ |
| CC9 Vendor Management | ☐ | ☐ | ☐ |

**Overall Readiness:** ____%

---

## Next Steps

1. [ ] Complete any "Not Ready" items
2. [ ] Collect 3-6 months of evidence
3. [ ] Schedule penetration test
4. [ ] Engage SOC 2 auditor
5. [ ] Conduct readiness assessment with auditor
