import os
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()


def get_secret(key: str, default: str | None = None) -> str | None:
    """Return a secret value.

    Order of precedence:
    1) os.getenv(key, default) (for local development, including .env file)
    """
    return os.getenv(key, default)
