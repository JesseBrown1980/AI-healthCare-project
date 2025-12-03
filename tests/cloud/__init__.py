"""
Cloud Testing Utilities
Helpers for running tests against different cloud providers.
"""

import os
from typing import Optional
import pytest


def is_firebase_available() -> bool:
    """Check if Firebase emulator is available."""
    return "FIRESTORE_EMULATOR_HOST" in os.environ


def is_aws_available() -> bool:
    """Check if AWS (LocalStack) is available."""
    return "AWS_ENDPOINT_URL" in os.environ or os.environ.get("AWS_ACCESS_KEY_ID") == "test"


def is_azure_available() -> bool:
    """Check if Azure (Azurite) is available."""
    return "AZURE_STORAGE_CONNECTION_STRING" in os.environ


def get_database_url() -> str:
    """Get the current database URL."""
    return os.environ.get("DATABASE_URL", "sqlite:///:memory:")


def is_postgres() -> bool:
    """Check if PostgreSQL is configured."""
    return "postgresql" in get_database_url().lower()


def is_sqlite() -> bool:
    """Check if SQLite is configured."""
    return "sqlite" in get_database_url().lower()


# Skip decorators for cloud-specific tests
skip_if_no_firebase = pytest.mark.skipif(
    not is_firebase_available(),
    reason="Firebase emulator not available"
)

skip_if_no_aws = pytest.mark.skipif(
    not is_aws_available(),
    reason="AWS/LocalStack not available"
)

skip_if_no_azure = pytest.mark.skipif(
    not is_azure_available(),
    reason="Azure/Azurite not available"
)

skip_if_no_postgres = pytest.mark.skipif(
    not is_postgres(),
    reason="PostgreSQL not configured"
)


# Markers for cloud tests
firebase = pytest.mark.firebase
aws = pytest.mark.aws
azure = pytest.mark.azure
database = pytest.mark.database
