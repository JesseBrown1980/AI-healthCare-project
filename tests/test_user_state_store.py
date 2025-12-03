from datetime import datetime, timedelta, timezone

from backend.state.user_store import UserStateStore


DEFAULT_PARAMS = dict(
    analysis_history_limit=5,
    analysis_history_ttl_seconds=10,
    analysis_cache_ttl_seconds=2,
)


def test_user_state_is_isolated_per_key():
    store = UserStateStore(**DEFAULT_PARAMS, state_ttl_seconds=1000, max_users=10)

    state_a = store.get_state("user-a")
    state_b = store.get_state("user-b")

    state_a.analysis_history["p1"] = [{"result": "a"}]
    state_a.patient_summary_cache["p1"] = {"summary": "a"}

    state_b.analysis_history["p2"] = [{"result": "b"}]
    state_b.patient_summary_cache["p2"] = {"summary": "b"}

    assert "p2" not in state_a.analysis_history
    assert "p2" not in state_a.patient_summary_cache
    assert state_a.analysis_job_manager is not state_b.analysis_job_manager


def test_user_state_store_evicts_oldest_user_when_over_capacity():
    store = UserStateStore(**DEFAULT_PARAMS, state_ttl_seconds=1000, max_users=1)

    first_state = store.get_state("first")
    first_state.last_access = datetime.now(timezone.utc) - timedelta(seconds=100)

    store.get_state("second")

    assert "second" in store._store
    assert "first" not in store._store


def test_user_state_ttl_prunes_stale_entries():
    store = UserStateStore(**DEFAULT_PARAMS, state_ttl_seconds=1, max_users=5)
    stale_state = store.get_state("stale")
    stale_state.last_access = datetime.now(timezone.utc) - timedelta(seconds=5)

    store.get_state("fresh")

    assert "stale" not in store._store
    assert "fresh" in store._store
