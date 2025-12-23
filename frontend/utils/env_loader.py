import os
from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from .env file without overriding existing ones."""
    load_dotenv(override=False)


def get_api_url() -> str:
    url = (
        os.getenv("API_BASE_URL")
        or os.getenv("API_URL")
        or os.getenv("BACKEND_API_URL")
        or "http://localhost:8000"
    )
    return url.rstrip("/")
