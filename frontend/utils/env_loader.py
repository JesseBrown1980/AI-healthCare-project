import os
from dotenv import load_dotenv


def load_environment():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
