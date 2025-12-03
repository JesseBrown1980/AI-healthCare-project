"""Simple in-memory analysis cache to avoid repeated expensive runs.

The FastAPI endpoints perform full patient analyses on demand. This helper adds
an in-memory cache with a short TTL and de-duplicates concurrent requests for
the same workload, so multiple dashboard refreshes or API callers share the
same result instead of re-triggering FHIR and LLM calls.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple


class AnalysisJobManager:
    """Manage cached and in-flight patient analyses.

    The manager keeps a bounded TTL cache and reuses the same asyncio task when
    multiple callers request the identical analysis parameters at once. This
    keeps the system responsive under load without introducing a full job queue
    or persistent cache layer.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = max(ttl_seconds, 0)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._inflight: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def cache_key(
        *,
        patient_id: str,
        include_recommendations: bool,
        specialty: Optional[str],
        analysis_focus: Optional[str],
    ) -> str:
        """Create a stable cache key for a specific analysis workload."""

        return "|".join(
            [
                patient_id,
                "recs" if include_recommendations else "no-recs",
                specialty or "",
                analysis_focus or "",
            ]
        )

    def _is_fresh(self, key: str) -> bool:
        entry = self._cache.get(key)
        if not entry:
            return False

        cached_at: Optional[datetime] = entry.get("cached_at")
        if not cached_at:
            return False

        age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()
        return age_seconds <= self.ttl_seconds

    async def _run_and_store(
        self, key: str, runner: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        try:
            analysis = await runner()
            async with self._lock:
                self._cache[key] = {
                    "analysis": analysis,
                    "cached_at": datetime.now(timezone.utc),
                }
            return analysis
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    async def get_or_create(
        self,
        key: str,
        runner: Callable[[], Awaitable[Dict[str, Any]]],
        *,
        force_refresh: bool = False,
    ) -> Tuple[Dict[str, Any], bool]:
        """Return a cached analysis or run a new one.

        Returns:
            analysis: The completed analysis payload.
            from_cache: True if a fresh cached result was returned.
        """

        async with self._lock:
            if not force_refresh and self._is_fresh(key):
                cached = self._cache[key]["analysis"]
                return cached, True

            inflight = self._inflight.get(key)
            if not inflight:
                inflight = asyncio.create_task(self._run_and_store(key, runner))
                self._inflight[key] = inflight

        analysis = await inflight
        return analysis, False

    async def refresh_in_background(
        self, key: str, runner: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Kick off a background refresh if no task is already running."""

        async with self._lock:
            if key in self._inflight:
                return
            task = asyncio.create_task(self._run_and_store(key, runner))
            self._inflight[key] = task

    def invalidate_patient(self, patient_id: str) -> None:
        """Remove cached entries for a patient across all parameterizations."""

        keys_to_delete = [k for k in self._cache if k.startswith(patient_id + "|")]
        for key in keys_to_delete:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all cached analyses."""

        for task in self._inflight.values():
            task.cancel()
        self._inflight.clear()
        self._cache.clear()

