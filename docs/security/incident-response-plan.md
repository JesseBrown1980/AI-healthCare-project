# Incident Response Plan

**Document ID:** SEC-POL-003  
**Version:** 1.0  
**Last Updated:** January 2026  
**Classification:** Internal

---

## 1. Purpose

Define procedures for detecting, responding to, and recovering from security incidents affecting the AI Healthcare Project.

---

## 2. Incident Classification

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **Critical** | Active breach, data exfiltration | 15 minutes | Unauthorized PHI access, ransomware |
| **High** | Potential breach, system compromise | 1 hour | Suspicious activity, failed authentication surge |
| **Medium** | Security weakness identified | 4 hours | Vulnerability discovered, policy violation |
| **Low** | Minor security concern | 24 hours | Configuration drift, minor policy issue |

---

## 3. Incident Response Team

| Role | Responsibility | Contact |
|------|----------------|---------|
| Incident Commander | Overall coordination | On-call rotation |
| Security Lead | Technical investigation | Security team |
| Legal/Compliance | Regulatory notifications | Legal team |
| Communications | Internal/external comms | PR team |
| Engineering Lead | System remediation | Engineering team |

---

## 4. Detection

### 4.1 Automated Detection
- Failed authentication monitoring
- Unusual data access patterns
- System integrity checks
- Anomaly detection (GNN-based)

### 4.2 Manual Detection
- User reports
- Third-party notifications
- Audit log reviews
- Penetration testing results

### 4.3 Indicators of Compromise
- Multiple failed logins from same IP
- Access outside normal hours
- Large data exports
- Privilege escalation attempts

---

## 5. Response Phases

### Phase 1: Identification (0-30 min)
- [ ] Confirm incident is real (not false positive)
- [ ] Classify severity level
- [ ] Notify incident commander
- [ ] Begin incident documentation
- [ ] Preserve evidence (logs, screenshots)

### Phase 2: Containment (30 min - 2 hours)
- [ ] Isolate affected systems
- [ ] Block malicious IPs/accounts
- [ ] Revoke compromised credentials
- [ ] Preserve forensic evidence
- [ ] Prevent lateral movement

### Phase 3: Eradication (2-24 hours)
- [ ] Identify root cause
- [ ] Remove malicious artifacts
- [ ] Patch vulnerabilities
- [ ] Update security controls
- [ ] Verify clean system state

### Phase 4: Recovery (24-72 hours)
- [ ] Restore from clean backups
- [ ] Validate system integrity
- [ ] Monitor for recurrence
- [ ] Gradual service restoration
- [ ] User communication

### Phase 5: Lessons Learned (1-2 weeks)
- [ ] Post-incident review meeting
- [ ] Document timeline and actions
- [ ] Identify improvement areas
- [ ] Update runbooks and policies
- [ ] Training updates if needed

---

## 6. Communication

### 6.1 Internal Notifications
| Severity | Notify | Method |
|----------|--------|--------|
| Critical | Executive team, All engineering | Phone + Slack |
| High | Security team, Engineering leads | Slack |
| Medium | Security team | Slack |
| Low | Security team | Email |

### 6.2 External Notifications
| Requirement | Timeline | Recipient |
|-------------|----------|-----------|
| GDPR breach | 72 hours | Supervisory authority |
| HIPAA breach (500+) | 60 days | HHS, media |
| HIPAA breach (<500) | Annual | HHS |
| SOC 2 | Next audit | Auditor |

---

## 7. Runbooks

### 7.1 Credential Compromise
```
1. Revoke all sessions for user
2. Reset credentials
3. Review access logs for abuse
4. Notify user
5. Monitor for further activity
```

### 7.2 Data Breach
```
1. Identify affected data scope
2. Contain access
3. Document affected records
4. Legal notification assessment
5. User notification if required
```

### 7.3 DDoS Attack
```
1. Enable rate limiting
2. Activate CDN/WAF rules
3. Scale infrastructure
4. Block attack sources
5. Monitor and adjust
```

---

## 8. Evidence Preservation

### 8.1 What to Preserve
- System logs (30 days minimum)
- Access logs
- Network traffic captures
- Affected file hashes
- Screenshots of indicators

### 8.2 Chain of Custody
- Document who handled evidence
- Timestamp all actions
- Use write-blockers for disk images
- Secure storage with limited access

---

## 9. Compliance

| Regulation | Requirement | Our Commitment |
|------------|-------------|----------------|
| HIPAA | Document incidents | All incidents logged |
| GDPR | 72-hour notification | Automated alerting |
| SOC 2 | Incident response plan | This document |

---

## 10. Testing

- Annual tabletop exercises
- Quarterly runbook reviews
- Post-incident plan updates
