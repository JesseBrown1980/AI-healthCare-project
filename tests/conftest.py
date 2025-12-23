import pytest

from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    """Restrict anyio tests to the asyncio backend."""

    yield "asyncio"


@pytest.fixture
def dependency_overrides_guard():
    """Save and restore FastAPI dependency overrides for each test."""

    original_overrides = dict(app.dependency_overrides)

    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides = original_overrides
