"""Per-user state isolation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from backend.analysis_cache import AnalysisJobManager


@dataclass
class UserState:
    analysis_history: Dict[str, Any]
    patient_summary_cache: Dict[str, Any]
    analysis_job_manager: AnalysisJobManager
    last_access: datetime


class UserStateStore:
    """Manage per-user caches and analysis artifacts."""

    def __init__(
        self,
        *,
        analysis_history_limit: int,
        analysis_history_ttl_seconds: int,
        analysis_cache_ttl_seconds: int,
        state_ttl_seconds: int = 3600,
        max_users: int = 1000,
    ) -> None:
        self.analysis_history_limit = max(analysis_history_limit, 1)
        self.analysis_history_ttl_seconds = max(analysis_history_ttl_seconds, 0)
        self.analysis_cache_ttl_seconds = max(analysis_cache_ttl_seconds, 0)
        self.state_ttl_seconds = max(state_ttl_seconds, 0)
        self.max_users = max(max_users, 1)
        self._store: Dict[str, UserState] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _prune_stale_users(self) -> None:
        if self.state_ttl_seconds <= 0:
            return

        cutoff = self._now() - timedelta(seconds=self.state_ttl_seconds)
        for key, state in list(self._store.items()):
            if state.last_access < cutoff:
                state.analysis_job_manager.clear()
                self._store.pop(key, None)

    def _evict_if_needed(self, preserved_key: str) -> None:
        if len(self._store) <= self.max_users:
            return

        sorted_items = sorted(self._store.items(), key=lambda item: item[1].last_access)
        for key, state in sorted_items:
            if len(self._store) <= self.max_users:
                break
            if key == preserved_key:
                continue
            state.analysis_job_manager.clear()
            self._store.pop(key, None)

        if len(self._store) > self.max_users:
            # Fallback: evict the oldest entry even if it's the preserved key.
            oldest_key, oldest_state = sorted_items[0]
            oldest_state.analysis_job_manager.clear()
            self._store.pop(oldest_key, None)

    def get_state(self, user_key: str) -> UserState:
        """Return isolated state for the given user key."""

        self._prune_stale_users()
        state = self._store.get(user_key)
        if not state:
            state = UserState(
                analysis_history={},
                patient_summary_cache={},
                analysis_job_manager=AnalysisJobManager(
                    ttl_seconds=self.analysis_cache_ttl_seconds
                ),
                last_access=self._now(),
            )
            self._store[user_key] = state
            self._evict_if_needed(user_key)

        state.last_access = self._now()
        return state

    def __len__(self) -> int:  # pragma: no cover - convenience
        return len(self._store)
