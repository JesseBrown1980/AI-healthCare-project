# Access Review Template

## Quarterly Access Review - Q[X] 20XX

**Review Period:** [Start Date] - [End Date]  
**Reviewer:** [Name]  
**Review Date:** [Date]

---

## 1. User Access Verification

### 1.1 Active Users
| User ID | Name | Role | Last Active | Access Appropriate? | Action |
|---------|------|------|-------------|---------------------|--------|
| | | | | ☐ Yes ☐ No | |
| | | | | ☐ Yes ☐ No | |
| | | | | ☐ Yes ☐ No | |

### 1.2 Terminated/Transferred Users
| User ID | Name | Termination Date | Access Revoked? | Verification |
|---------|------|------------------|-----------------|--------------|
| | | | ☐ Yes ☐ No | |

### 1.3 Privileged Accounts
| Account | Purpose | Owner | Still Required? | MFA Enabled? |
|---------|---------|-------|-----------------|--------------|
| | | | ☐ Yes ☐ No | ☐ Yes ☐ No |

---

## 2. Role Verification

### 2.1 Role Assignments
| Role | Users Assigned | Permissions | Appropriate? |
|------|----------------|-------------|--------------|
| Admin | | system/*.* | ☐ Yes ☐ No |
| Provider | | patient/*.* | ☐ Yes ☐ No |
| Clinician | | patient/*.read | ☐ Yes ☐ No |
| Auditor | | system/*.read | ☐ Yes ☐ No |

### 2.2 Scope Changes Since Last Review
| User | Previous Scopes | Current Scopes | Change Justified? |
|------|-----------------|----------------|-------------------|
| | | | ☐ Yes ☐ No |

---

## 3. Service Account Review

| Service Account | Purpose | Owner | Credentials Rotated? | Still Required? |
|-----------------|---------|-------|---------------------|-----------------|
| | | | ☐ Yes ☐ No | ☐ Yes ☐ No |

---

## 4. Third-Party Access

| Vendor | Access Type | Data Access | Contract Valid? | Review Status |
|--------|-------------|-------------|-----------------|---------------|
| | | | ☐ Yes ☐ No | ☐ Reviewed |

---

## 5. Findings and Actions

### 5.1 Issues Identified
| # | Issue | Severity | Action Required | Owner | Due Date |
|---|-------|----------|-----------------|-------|----------|
| 1 | | High/Med/Low | | | |

### 5.2 Remediation Tracking
| Issue # | Action Taken | Completed Date | Verified By |
|---------|--------------|----------------|-------------|
| | | | |

---

## 6. Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Reviewer | | | |
| Security Lead | | | |
| Manager | | | |

---

## Review Checklist

- [ ] All active users verified as current employees/contractors
- [ ] All terminated users have access revoked
- [ ] Privileged access justified with business need
- [ ] Service accounts reviewed and rotated
- [ ] Third-party access validated with contracts
- [ ] Excessive permissions identified and reduced
- [ ] MFA enabled for administrative accounts
- [ ] Findings documented and remediation assigned

---

**Next Review Date:** [Date + 3 months]
