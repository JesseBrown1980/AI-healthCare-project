"""
Data Retention Service
Automated cleanup of expired data for compliance.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Data retention policy configuration."""
    name: str
    retention_days: int
    enabled: bool = True
    description: str = ""


# Default retention policies
DEFAULT_POLICIES = {
    "audit_logs": RetentionPolicy(
        name="audit_logs",
        retention_days=2555,  # ~7 years (HIPAA requirement)
        description="Audit trail logs for compliance"
    ),
    "analysis_cache": RetentionPolicy(
        name="analysis_cache",
        retention_days=1,
        description="Temporary analysis cache"
    ),
    "session_data": RetentionPolicy(
        name="session_data",
        retention_days=1,
        description="User session data"
    ),
    "temp_files": RetentionPolicy(
        name="temp_files",
        retention_days=7,
        description="Temporary uploaded files"
    ),
    "error_logs": RetentionPolicy(
        name="error_logs",
        retention_days=90,
        description="Application error logs"
    ),
    "patient_data": RetentionPolicy(
        name="patient_data",
        retention_days=2555,  # ~7 years
        description="Patient health records (HIPAA)"
    ),
}


class DataRetentionService:
    """
    Manages data retention and automated cleanup.
    
    Implements configurable retention policies for different data types.
    
    Usage:
        service = DataRetentionService()
        await service.run_cleanup()
    """
    
    def __init__(
        self,
        policies: Optional[Dict[str, RetentionPolicy]] = None,
        dry_run: bool = False,
    ):
        """
        Initialize data retention service.
        
        Args:
            policies: Custom retention policies (default: use defaults)
            dry_run: If True, only log what would be deleted
        """
        self.policies = policies or DEFAULT_POLICIES.copy()
        self.dry_run = dry_run
        self._last_run: Optional[datetime] = None
        self._stats: Dict[str, int] = {}
    
    def get_policy(self, name: str) -> Optional[RetentionPolicy]:
        """Get a retention policy by name."""
        return self.policies.get(name)
    
    def set_policy(self, policy: RetentionPolicy) -> None:
        """Set or update a retention policy."""
        self.policies[policy.name] = policy
    
    def get_cutoff_date(self, policy_name: str) -> Optional[datetime]:
        """Get the cutoff date for a policy (data older than this should be deleted)."""
        policy = self.policies.get(policy_name)
        if policy and policy.enabled:
            return datetime.utcnow() - timedelta(days=policy.retention_days)
        return None
    
    async def cleanup_audit_logs(self) -> int:
        """
        Clean up old audit logs.
        
        Returns:
            Number of records cleaned up
        """
        import os
        from pathlib import Path
        
        log_dir = Path(os.getenv("AUDIT_LOG_DIR", "audit-logs"))
        if not log_dir.exists():
            return 0
        
        cutoff = self.get_cutoff_date("audit_logs")
        if cutoff is None:
            return 0
        
        deleted = 0
        for log_file in log_dir.glob("audit_*.jsonl"):
            try:
                # Parse date from filename (audit_YYYY-MM-DD.jsonl)
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff:
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would delete: {log_file}")
                    else:
                        log_file.unlink()
                        logger.info(f"Deleted expired audit log: {log_file}")
                    deleted += 1
            except (ValueError, OSError) as e:
                logger.warning(f"Error processing {log_file}: {e}")
        
        return deleted
    
    async def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files.
        
        Returns:
            Number of files cleaned up
        """
        import os
        from pathlib import Path
        
        temp_dirs = [
            Path("temp"),
            Path("uploads/temp"),
            Path("cache"),
        ]
        
        cutoff = self.get_cutoff_date("temp_files")
        if cutoff is None:
            return 0
        
        deleted = 0
        for temp_dir in temp_dirs:
            if not temp_dir.exists():
                continue
            
            for temp_file in temp_dir.rglob("*"):
                if temp_file.is_file():
                    try:
                        mtime = datetime.fromtimestamp(temp_file.stat().st_mtime)
                        if mtime < cutoff:
                            if self.dry_run:
                                logger.info(f"[DRY RUN] Would delete: {temp_file}")
                            else:
                                temp_file.unlink()
                                logger.info(f"Deleted temp file: {temp_file}")
                            deleted += 1
                    except (OSError, ValueError) as e:
                        logger.warning(f"Error processing {temp_file}: {e}")
        
        return deleted
    
    async def cleanup_analysis_cache(self) -> int:
        """
        Clean up expired analysis cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        # This would integrate with the AnalysisJobManager
        # For now, just log the intent
        cutoff = self.get_cutoff_date("analysis_cache")
        if cutoff is None:
            return 0
        
        logger.info(f"Would clean analysis cache older than {cutoff}")
        return 0
    
    async def cleanup_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            from backend.security_utils.session_manager import get_session_manager
            
            manager = get_session_manager()
            # The session manager handles its own cleanup
            # This just triggers it
            initial_count = manager.get_active_session_count()
            manager._cleanup_expired_sessions()
            final_count = manager.get_active_session_count()
            
            return initial_count - final_count
        except ImportError:
            return 0
    
    async def run_cleanup(self) -> Dict[str, int]:
        """
        Run all cleanup tasks.
        
        Returns:
            Dictionary of cleanup results by category
        """
        logger.info("Starting data retention cleanup...")
        start_time = datetime.utcnow()
        
        results = {}
        
        # Run cleanup tasks
        tasks = [
            ("audit_logs", self.cleanup_audit_logs()),
            ("temp_files", self.cleanup_temp_files()),
            ("analysis_cache", self.cleanup_analysis_cache()),
            ("sessions", self.cleanup_sessions()),
        ]
        
        for name, coro in tasks:
            try:
                count = await coro
                results[name] = count
                if count > 0:
                    logger.info(f"Cleaned up {count} {name}")
            except Exception as e:
                logger.error(f"Error cleaning up {name}: {e}")
                results[name] = -1
        
        self._last_run = datetime.utcnow()
        self._stats = results
        
        duration = (self._last_run - start_time).total_seconds()
        logger.info(f"Data retention cleanup completed in {duration:.2f}s")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        return {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_results": self._stats,
            "policies": {
                name: {
                    "retention_days": p.retention_days,
                    "enabled": p.enabled,
                }
                for name, p in self.policies.items()
            },
        }


# Background cleanup task
async def run_scheduled_cleanup(
    interval_hours: int = 24,
    service: Optional[DataRetentionService] = None,
) -> None:
    """
    Run cleanup on a schedule.
    
    Args:
        interval_hours: Hours between cleanup runs
        service: DataRetentionService instance (creates new if None)
    """
    if service is None:
        service = DataRetentionService()
    
    while True:
        try:
            await service.run_cleanup()
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")
        
        await asyncio.sleep(interval_hours * 3600)


# Global service instance
_retention_service: Optional[DataRetentionService] = None


def get_retention_service() -> DataRetentionService:
    """Get the global data retention service instance."""
    global _retention_service
    if _retention_service is None:
        _retention_service = DataRetentionService()
    return _retention_service
