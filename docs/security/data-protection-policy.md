# Data Protection Policy

**Document ID:** SEC-POL-002  
**Version:** 1.0  
**Last Updated:** January 2026  
**Classification:** Internal

---

## 1. Purpose

Establish data protection standards for Protected Health Information (PHI) and Personally Identifiable Information (PII) in compliance with HIPAA, GDPR, and SOC 2.

---

## 2. Data Classification

| Level | Description | Examples | Controls |
|-------|-------------|----------|----------|
| **Critical** | PHI/PII requiring highest protection | Patient records, SSN, diagnoses | Encryption, access logging, anonymization |
| **Confidential** | Sensitive business data | API keys, credentials, audit logs | Encryption, access control |
| **Internal** | Non-public business data | System configs, documentation | Access control |
| **Public** | Published information | Product documentation | None required |

---

## 3. Encryption Requirements

### 3.1 Data at Rest
- AES-256 encryption for all databases
- Field-level encryption for PHI (configurable)
- Encrypted backups with separate key management

### 3.2 Data in Transit
- TLS 1.3 for all API communications
- HTTPS enforced via HSTS
- Certificate pinning for mobile apps

### 3.3 Key Management
- Keys stored in secure vault (AWS KMS, Azure Key Vault)
- Key rotation every 90 days
- Separate keys per environment

---

## 4. PHI Handling

### 4.1 Collection
- Minimum necessary data collected
- Explicit consent required (GDPR regions)
- Purpose limitation enforced

### 4.2 Processing
- PHI processed only within approved systems
- No PHI in logs (configurable by region)
- Anonymization for analytics

### 4.3 Storage
- PHI stored in compliant data centers
- Geographic restrictions by region
- No PHI in development environments

---

## 5. Data Retention

| Data Type | Retention Period | Justification |
|-----------|------------------|---------------|
| Patient analysis | 7 years | HIPAA requirement |
| Audit logs | 7 years | Compliance |
| Session data | 24 hours | Operational |
| Cached data | 5 minutes | Performance |

### 5.1 Deletion
- Right to deletion (GDPR Article 17)
- Secure deletion with verification
- Cascade deletion for related records

---

## 6. Regional Compliance

### 6.1 US (HIPAA)
```python
US_POLICY = CompliancePolicy(
    region="US",
    allow_phi_in_logs=False,
    data_retention_days=2555,  # 7 years
    require_anonymization=True,
)
```

### 6.2 EU (GDPR)
```python
EU_POLICY = CompliancePolicy(
    region="EU",
    require_consent=True,
    allow_data_deletion=True,
    require_local_llm=True,
)
```

---

## 7. Incident Response

Data breach procedures:
1. Contain and assess breach scope
2. Notify security team within 1 hour
3. Document affected records
4. Notify regulators within 72 hours (GDPR)
5. Notify affected individuals
6. Conduct post-incident review

---

## 8. Technical Controls

| Control | Implementation | Location |
|---------|----------------|----------|
| PHI filtering | Log sanitization | `backend/logging/` |
| Encryption | Field-level AES | `backend/encryption.py` |
| Access logging | Audit trail | `backend/audit/` |
| Anonymization | Data masking | `backend/anonymizer.py` |

---

## 9. Compliance Mapping

| Requirement | SOC 2 | HIPAA | GDPR |
|-------------|-------|-------|------|
| Encryption at rest | CC6.1 | §164.312(a)(2)(iv) | Art. 32 |
| Encryption in transit | CC6.7 | §164.312(e)(1) | Art. 32 |
| Access controls | CC6.1 | §164.312(a)(1) | Art. 25 |
| Data retention | CC7.1 | §164.530(j) | Art. 5(1)(e) |

---

## 10. References

- `backend/config/compliance_policies.py`
- `backend/middleware/security_headers.py`
- NIST SP 800-122 (PII Protection)
- HIPAA Security Rule
