import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.database.service import DatabaseService

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 200
DEFAULT_HISTORY_TTL_SECONDS = 60 * 60 * 24

class HistoryService:
    """
    Manages analysis history, including in-memory storage, database persistence,
    TTL enforcement, and pruning.
    """

    def __init__(
        self,
        database_service: Optional["DatabaseService"] = None,
        history_limit: Optional[int] = None,
        history_ttl_seconds: Optional[int] = None,
    ):
        self.database_service = database_service
        self.history_limit = self._validated_positive_value(
            history_limit, DEFAULT_HISTORY_LIMIT, "history_limit"
        )
        self.history_ttl_seconds = self._validated_positive_value(
            history_ttl_seconds, DEFAULT_HISTORY_TTL_SECONDS, "history_ttl_seconds"
        )
        self.analysis_history: Dict[str, List[Dict]] = {}
        
        if self.database_service:
            logger.info("HistoryService initialized with database service")
        else:
            logger.info("HistoryService initialized with in-memory storage")

    @staticmethod
    def _validated_positive_value(
        value: Optional[int], default_value: int, name: str
    ) -> int:
        if value is None:
            return default_value
        if value <= 0:
            logger.warning(
                "%s must be positive; falling back to default %s", name, default_value
            )
            return default_value
        return value

    async def add_to_history(self, analysis: Dict[str, Any]) -> None:
        """Add an analysis result to history while enforcing limits and TTL."""

        patient_id = analysis.get("patient_id") or "unknown"
        
        # Try to save to database first (if available)
        if self.database_service:
            try:
                # Extract correlation_id and user_id from analysis if available
                correlation_id = analysis.get("correlation_id")
                user_id = analysis.get("user_id")
                
                # Prepare analysis data for database
                analysis_data = {
                    "analysis_data": analysis,
                    "risk_scores": analysis.get("risk_scores", {}),
                    "alerts": analysis.get("alerts", []),
                    "recommendations": analysis.get("recommendations", []),
                }
                
                # Save to database
                await self.database_service.save_analysis(
                    patient_id=patient_id,
                    analysis_data=analysis_data,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
            except Exception as e:
                logger.warning("Failed to save analysis to database, falling back to in-memory: %s", str(e))
        
        # Also keep in-memory for backward compatibility and fast access
        bucket = self.analysis_history.setdefault(patient_id, [])
        bucket.append(analysis)

        removed = self._prune_history_for_patient(patient_id)
        if removed:
            logger.debug(
                "Pruned %s expired analyses for %s after adding new result",
                removed,
                patient_id,
            )

        stale_removed = self.prune_stale_history()
        if stale_removed:
            logger.debug("Pruned %s expired analyses across all patients (periodic)", stale_removed)

    def clear_history(self) -> None:
        """Remove all cached analyses to reclaim memory."""
        self.analysis_history.clear()

    def get_history(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return a copy of the analysis history for a patient or all patients."""

        if patient_id is not None:
            return list(self.analysis_history.get(patient_id, []))

        all_entries: List[Dict[str, Any]] = []
        for bucket in self.analysis_history.values():
            all_entries.extend(bucket)

        return sorted(all_entries, key=self._timestamp_sort_key)

    async def get_latest_analysis(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest analysis for a specific patient."""
        
        # Try database first (if available)
        if self.database_service:
            try:
                db_result = await self.database_service.get_latest_analysis(patient_id)
                if db_result:
                    return db_result
            except Exception as e:
                logger.debug("Failed to get analysis from database, using in-memory: %s", str(e))
        
        # Fall back to in-memory
        bucket = self.analysis_history.get(patient_id) or []
        if not bucket:
            return None
        return bucket[-1]

    def total_history_count(self) -> int:
        """Return the total number of cached analyses across all patients."""
        return sum(len(bucket) for bucket in self.analysis_history.values())

    def prune_stale_history(self) -> int:
        """Prune TTL-expired analyses across all patients."""
        total_removed = 0
        for patient_id in list(self.analysis_history.keys()):
            total_removed += self._prune_history_for_patient(patient_id)
        return total_removed

    def _prune_history_for_patient(self, patient_id: str) -> int:
        bucket = self.analysis_history.get(patient_id, [])
        if not bucket:
            return 0

        removed = self._prune_by_limit(bucket)
        removed += self._prune_by_ttl(bucket)
        return removed

    def _prune_by_limit(self, bucket: List[Dict[str, Any]]) -> int:
        if self.history_limit is None or self.history_limit <= 0:
            return 0
        excess = len(bucket) - self.history_limit
        if excess > 0:
            del bucket[:excess]
        return max(excess, 0)

    def _prune_by_ttl(self, bucket: List[Dict[str, Any]]) -> int:
        if not self.history_ttl_seconds:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.history_ttl_seconds)
        retained: List[Dict[str, Any]] = []
        removed = 0
        for entry in bucket:
            timestamp = self._parse_timestamp(entry)
            if timestamp and timestamp < cutoff:
                removed += 1
                continue
            retained.append(entry)

        if removed:
            bucket[:] = retained
        return removed

    @staticmethod
    def _parse_timestamp(entry: Dict[str, Any]) -> Optional[datetime]:
        timestamp_value = entry.get("analysis_timestamp") or entry.get("timestamp")
        if not timestamp_value:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            return None

    def _timestamp_sort_key(self, entry: Dict[str, Any]) -> datetime:
        return self._parse_timestamp(entry) or datetime.min.replace(tzinfo=timezone.utc)
