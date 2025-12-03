"""
Session Management
Secure session handling with timeout, concurrent limits, and invalidation.
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import secrets


@dataclass
class Session:
    """Represents an active user session."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if session has expired."""
        expiry_time = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry_time
    
    def touch(self) -> None:
        """Update last activity time."""
        self.last_activity = datetime.utcnow()


class SessionManager:
    """
    Manages user sessions with security features.
    
    Features:
    - Session timeout (configurable)
    - Concurrent session limits
    - Session invalidation
    - IP binding (optional)
    
    Usage:
        manager = SessionManager()
        session_id = manager.create_session("user123")
        session = manager.get_session(session_id)
        manager.invalidate_session(session_id)
    """
    
    def __init__(
        self,
        timeout_minutes: int = None,
        max_concurrent_sessions: int = None,
        bind_to_ip: bool = False,
    ):
        """
        Initialize session manager.
        
        Args:
            timeout_minutes: Session timeout (default: from env or 60)
            max_concurrent_sessions: Max sessions per user (default: from env or 5)
            bind_to_ip: If True, sessions are bound to IP address
        """
        self.timeout_minutes = timeout_minutes or int(
            os.getenv("SESSION_TIMEOUT_MINUTES", "60")
        )
        self.max_concurrent_sessions = max_concurrent_sessions or int(
            os.getenv("MAX_CONCURRENT_SESSIONS", "5")
        )
        self.bind_to_ip = bind_to_ip
        
        # Session storage
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()
        
        # Cleanup interval
        self._last_cleanup = datetime.utcnow()
        self._cleanup_interval_minutes = 5
    
    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed."""
        now = datetime.utcnow()
        if now - self._last_cleanup > timedelta(minutes=self._cleanup_interval_minutes):
            self._cleanup_expired_sessions()
            self._last_cleanup = now
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired(self.timeout_minutes)
            ]
            
            for sid in expired:
                session = self._sessions.pop(sid, None)
                if session:
                    self._user_sessions[session.user_id].discard(sid)
    
    def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional session data
        
        Returns:
            Session ID
        
        Raises:
            ValueError: If max concurrent sessions exceeded
        """
        self._maybe_cleanup()
        
        with self._lock:
            # Check concurrent session limit
            user_session_ids = self._user_sessions[user_id]
            active_sessions = [
                sid for sid in user_session_ids
                if sid in self._sessions and not self._sessions[sid].is_expired(self.timeout_minutes)
            ]
            
            if len(active_sessions) >= self.max_concurrent_sessions:
                # Remove oldest session
                oldest_sid = min(
                    active_sessions,
                    key=lambda sid: self._sessions[sid].created_at
                )
                self._invalidate_session_internal(oldest_sid)
            
            # Create new session
            session_id = self._generate_session_id()
            now = datetime.utcnow()
            
            session = Session(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                last_activity=now,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
            )
            
            self._sessions[session_id] = session
            self._user_sessions[user_id].add(session_id)
            
            return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.
        
        Returns None if session doesn't exist or is expired.
        """
        self._maybe_cleanup()
        
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                return None
            
            if session.is_expired(self.timeout_minutes):
                self._invalidate_session_internal(session_id)
                return None
            
            # Update last activity
            session.touch()
            return session
    
    def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Validate a session.
        
        Args:
            session_id: Session to validate
            ip_address: Client IP (for IP binding check)
        
        Returns:
            True if session is valid
        """
        session = self.get_session(session_id)
        
        if session is None:
            return False
        
        # Check IP binding
        if self.bind_to_ip and ip_address:
            if session.ip_address and session.ip_address != ip_address:
                # IP mismatch - potential session hijacking
                self.invalidate_session(session_id)
                return False
        
        return True
    
    def _invalidate_session_internal(self, session_id: str) -> None:
        """Internal session invalidation (assumes lock is held)."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._user_sessions[session.user_id].discard(session_id)
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.
        
        Returns:
            True if session was invalidated
        """
        with self._lock:
            if session_id in self._sessions:
                self._invalidate_session_internal(session_id)
                return True
            return False
    
    def invalidate_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user.
        
        Returns:
            Number of sessions invalidated
        """
        with self._lock:
            session_ids = list(self._user_sessions.get(user_id, set()))
            
            for sid in session_ids:
                self._invalidate_session_internal(sid)
            
            return len(session_ids)
    
    def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        self._maybe_cleanup()
        
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            return [
                self._sessions[sid]
                for sid in session_ids
                if sid in self._sessions and not self._sessions[sid].is_expired(self.timeout_minutes)
            ]
    
    def get_active_session_count(self) -> int:
        """Get total number of active sessions."""
        self._maybe_cleanup()
        
        with self._lock:
            return sum(
                1 for session in self._sessions.values()
                if not session.is_expired(self.timeout_minutes)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        self._maybe_cleanup()
        
        with self._lock:
            active = [
                s for s in self._sessions.values()
                if not s.is_expired(self.timeout_minutes)
            ]
            
            return {
                "total_active_sessions": len(active),
                "unique_users": len(set(s.user_id for s in active)),
                "timeout_minutes": self.timeout_minutes,
                "max_concurrent_sessions": self.max_concurrent_sessions,
            }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
