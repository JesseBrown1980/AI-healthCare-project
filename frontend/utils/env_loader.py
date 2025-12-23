import os
from dotenv import load_dotenv


def load_environment():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)


def get_api_url(default_base: str = "http://localhost:8000") -> str:
    """Resolve the API base URL, preferring API_BASE_URL when provided.

    Falls back to legacy variables for backward compatibility.
    """

    api_base = os.getenv("API_BASE_URL")
    if api_base:
        return f"{api_base.rstrip('/')}/api/v1"

    legacy_backend = os.getenv("BACKEND_API_URL")
    if legacy_backend:
        return legacy_backend.rstrip("/")

    return os.getenv("API_URL", f"{default_base.rstrip('/')}/api/v1")
