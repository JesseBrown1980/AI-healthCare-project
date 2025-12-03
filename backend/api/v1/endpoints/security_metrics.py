"""
Security Metrics Endpoint
Provides security-related metrics for monitoring and compliance.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/security", tags=["Security"])


class SecurityMetricsResponse(BaseModel):
    """Response model for security metrics."""
    timestamp: str
    period_hours: int
    authentication: Dict[str, int]
    authorization: Dict[str, int]
    rate_limiting: Dict[str, int]
    data_access: Dict[str, int]
    security_events: Dict[str, int]
    active_sessions: int
    summary: Dict[str, Any]


@dataclass
class SecurityMetricsCollector:
    """
    Collects and aggregates security metrics.
    
    Thread-safe singleton for collecting security events.
    """
    
    # Event counters by type
    _auth_success: int = 0
    _auth_failure: int = 0
    _auth_mfa_success: int = 0
    _auth_mfa_failure: int = 0
    
    _access_granted: int = 0
    _access_denied: int = 0
    _privilege_escalation: int = 0
    
    _rate_limit_warnings: int = 0
    _rate_limit_blocks: int = 0
    
    _phi_access: int = 0
    _data_exports: int = 0
    
    _suspicious_activity: int = 0
    _brute_force_detected: int = 0
    _invalid_tokens: int = 0
    
    # Time-based tracking
    _failed_logins_by_ip: Dict[str, List[datetime]] = field(default_factory=lambda: defaultdict(list))
    _active_sessions: Dict[str, datetime] = field(default_factory=dict)
    
    # Thread lock
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    # Singleton instance
    _instance: Optional["SecurityMetricsCollector"] = None
    
    @classmethod
    def get_instance(cls) -> "SecurityMetricsCollector":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def record_auth_success(self) -> None:
        """Record successful authentication."""
        with self._lock:
            self._auth_success += 1
    
    def record_auth_failure(self, ip_address: Optional[str] = None) -> None:
        """Record failed authentication."""
        with self._lock:
            self._auth_failure += 1
            if ip_address:
                self._failed_logins_by_ip[ip_address].append(datetime.utcnow())
    
    def record_mfa_success(self) -> None:
        with self._lock:
            self._auth_mfa_success += 1
    
    def record_mfa_failure(self) -> None:
        with self._lock:
            self._auth_mfa_failure += 1
    
    def record_access_granted(self) -> None:
        with self._lock:
            self._access_granted += 1
    
    def record_access_denied(self) -> None:
        with self._lock:
            self._access_denied += 1
    
    def record_privilege_escalation(self) -> None:
        with self._lock:
            self._privilege_escalation += 1
    
    def record_rate_limit_warning(self) -> None:
        with self._lock:
            self._rate_limit_warnings += 1
    
    def record_rate_limit_block(self) -> None:
        with self._lock:
            self._rate_limit_blocks += 1
    
    def record_phi_access(self) -> None:
        with self._lock:
            self._phi_access += 1
    
    def record_data_export(self) -> None:
        with self._lock:
            self._data_exports += 1
    
    def record_suspicious_activity(self) -> None:
        with self._lock:
            self._suspicious_activity += 1
    
    def record_brute_force(self) -> None:
        with self._lock:
            self._brute_force_detected += 1
    
    def record_invalid_token(self) -> None:
        with self._lock:
            self._invalid_tokens += 1
    
    def record_session_start(self, session_id: str) -> None:
        with self._lock:
            self._active_sessions[session_id] = datetime.utcnow()
    
    def record_session_end(self, session_id: str) -> None:
        with self._lock:
            self._active_sessions.pop(session_id, None)
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        with self._lock:
            # Clean up stale sessions (older than 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self._active_sessions = {
                k: v for k, v in self._active_sessions.items()
                if v > cutoff
            }
            return len(self._active_sessions)
    
    def get_failed_logins_from_ip(self, ip_address: str, hours: int = 24) -> int:
        """Get count of failed logins from an IP in the last N hours."""
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            attempts = self._failed_logins_by_ip.get(ip_address, [])
            return sum(1 for t in attempts if t > cutoff)
    
    def is_brute_force_suspected(self, ip_address: str, threshold: int = 10) -> bool:
        """Check if IP shows signs of brute force attack."""
        return self.get_failed_logins_from_ip(ip_address, hours=1) >= threshold
    
    def get_metrics(self, period_hours: int = 24) -> Dict[str, Any]:
        """Get all security metrics."""
        with self._lock:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "period_hours": period_hours,
                "authentication": {
                    "successful_logins": self._auth_success,
                    "failed_logins": self._auth_failure,
                    "mfa_success": self._auth_mfa_success,
                    "mfa_failure": self._auth_mfa_failure,
                },
                "authorization": {
                    "access_granted": self._access_granted,
                    "access_denied": self._access_denied,
                    "privilege_escalation_attempts": self._privilege_escalation,
                },
                "rate_limiting": {
                    "warnings": self._rate_limit_warnings,
                    "blocks": self._rate_limit_blocks,
                },
                "data_access": {
                    "phi_access_events": self._phi_access,
                    "data_exports": self._data_exports,
                },
                "security_events": {
                    "suspicious_activity": self._suspicious_activity,
                    "brute_force_detected": self._brute_force_detected,
                    "invalid_tokens": self._invalid_tokens,
                },
                "active_sessions": self.get_active_session_count(),
                "summary": {
                    "auth_success_rate": (
                        self._auth_success / max(self._auth_success + self._auth_failure, 1)
                    ) * 100,
                    "security_score": self._calculate_security_score(),
                },
            }
    
    def _calculate_security_score(self) -> int:
        """Calculate a 0-100 security score."""
        score = 100
        
        # Deduct for failed logins
        if self._auth_failure > 100:
            score -= 20
        elif self._auth_failure > 50:
            score -= 10
        
        # Deduct for access denied
        if self._access_denied > 50:
            score -= 15
        elif self._access_denied > 20:
            score -= 5
        
        # Deduct for security events
        if self._brute_force_detected > 0:
            score -= 25
        if self._suspicious_activity > 10:
            score -= 15
        if self._invalid_tokens > 50:
            score -= 10
        
        return max(0, score)
    
    def reset(self) -> None:
        """Reset all counters (for testing)."""
        with self._lock:
            self._auth_success = 0
            self._auth_failure = 0
            self._auth_mfa_success = 0
            self._auth_mfa_failure = 0
            self._access_granted = 0
            self._access_denied = 0
            self._privilege_escalation = 0
            self._rate_limit_warnings = 0
            self._rate_limit_blocks = 0
            self._phi_access = 0
            self._data_exports = 0
            self._suspicious_activity = 0
            self._brute_force_detected = 0
            self._invalid_tokens = 0
            self._failed_logins_by_ip.clear()
            self._active_sessions.clear()


# Global metrics collector
metrics_collector = SecurityMetricsCollector()


def get_metrics_collector() -> SecurityMetricsCollector:
    """Dependency to get metrics collector."""
    return SecurityMetricsCollector.get_instance()


@router.get("/metrics", response_model=SecurityMetricsResponse)
async def get_security_metrics(
    period_hours: int = 24,
    collector: SecurityMetricsCollector = Depends(get_metrics_collector),
) -> SecurityMetricsResponse:
    """
    Get security metrics for monitoring and compliance.
    
    Requires system/*.read scope.
    
    Returns:
        Security metrics including auth, access, rate limiting, and security events.
    """
    metrics = collector.get_metrics(period_hours)
    return SecurityMetricsResponse(**metrics)


@router.get("/health")
async def security_health(
    collector: SecurityMetricsCollector = Depends(get_metrics_collector),
) -> Dict[str, Any]:
    """
    Quick security health check.
    
    Returns:
        Simple health status based on security score.
    """
    metrics = collector.get_metrics()
    score = metrics["summary"]["security_score"]
    
    status = "healthy" if score >= 80 else "warning" if score >= 50 else "critical"
    
    return {
        "status": status,
        "security_score": score,
        "active_sessions": metrics["active_sessions"],
        "recent_failed_logins": metrics["authentication"]["failed_logins"],
    }
