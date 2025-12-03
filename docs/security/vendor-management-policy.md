# Vendor Management Policy

**Document ID:** SEC-POL-005  
**Version:** 1.0  
**Last Updated:** January 2026  
**Classification:** Internal

---

## 1. Purpose

Establish requirements for assessing and managing third-party vendors with access to systems or data.

---

## 2. Vendor Categories

| Category | Data Access | Assessment Level | Examples |
|----------|-------------|------------------|----------|
| **Critical** | PHI/PII | Full assessment | FHIR servers, LLM providers |
| **High** | Sensitive | Security review | Cloud providers, auth services |
| **Medium** | Internal | Questionnaire | CI/CD tools, monitoring |
| **Low** | None | Terms review | Documentation tools |

---

## 3. Current Vendors

### 3.1 Critical Vendors
| Vendor | Purpose | Compliance |
|--------|---------|------------|
| OpenAI/Anthropic | LLM backbone | SOC 2 Type II |
| FHIR Server | Patient data | HIPAA BAA |
| Cloud Provider | Infrastructure | SOC 2, HIPAA |

### 3.2 High-Risk Vendors
| Vendor | Purpose | Compliance |
|--------|---------|------------|
| Auth0/Okta | Authentication | SOC 2 Type II |
| Redis Cloud | Caching | SOC 2 Type II |
| PostgreSQL (managed) | Database | SOC 2, HIPAA |

---

## 4. Assessment Requirements

### 4.1 Critical Vendors
- [ ] SOC 2 Type II report review
- [ ] HIPAA Business Associate Agreement
- [ ] Data Processing Agreement (GDPR)
- [ ] Penetration test results
- [ ] Incident response procedures
- [ ] Annual reassessment

### 4.2 High-Risk Vendors
- [ ] SOC 2 Type II or equivalent
- [ ] Security questionnaire
- [ ] Data handling review
- [ ] Biannual reassessment

### 4.3 Medium/Low Vendors
- [ ] Security questionnaire
- [ ] Terms of service review
- [ ] Annual reassessment

---

## 5. Contract Requirements

### 5.1 Required Clauses
| Clause | Critical | High | Medium |
|--------|----------|------|--------|
| Data protection | ✅ | ✅ | ✅ |
| Breach notification | ✅ | ✅ | ⚠️ |
| Audit rights | ✅ | ✅ | ❌ |
| BAA (if PHI) | ✅ | ✅ | ❌ |
| Data deletion | ✅ | ✅ | ✅ |
| Subprocessor approval | ✅ | ⚠️ | ❌ |

### 5.2 SLA Requirements
- Uptime: 99.9% minimum for critical
- Support response: 4 hours for critical issues
- Breach notification: 24 hours maximum

---

## 6. Ongoing Monitoring

### 6.1 Continuous Monitoring
- Vendor security news/alerts
- Dependency vulnerability scanning
- API availability monitoring
- Data access logging

### 6.2 Periodic Review
| Frequency | Activity |
|-----------|----------|
| Quarterly | Critical vendor status check |
| Annually | Full vendor reassessment |
| On renewal | Contract review |
| On incident | Immediate assessment |

---

## 7. Termination Procedures

### 7.1 Offboarding Steps
1. Data export and verification
2. Access credential revocation
3. Data deletion confirmation
4. Certificate of destruction
5. Documentation update

### 7.2 Data Return
- All data returned within 30 days
- Secure deletion of vendor copies
- Written confirmation required

---

## 8. Compliance

| Requirement | SOC 2 Control | Implementation |
|-------------|---------------|----------------|
| Vendor assessment | CC9.2 | Risk-based evaluation |
| Vendor monitoring | CC9.2 | Quarterly reviews |
| Data agreements | CC2.3 | BAA/DPA contracts |

---

## 9. Vendor Inventory

Maintained in `docs/compliance/vendor-inventory.md`:
- Vendor name and purpose
- Data access level
- Contract expiration
- Last assessment date
- Compliance certifications
