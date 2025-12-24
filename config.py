import os
import streamlit as st
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()


def get_secret(key: str, default: str | None = None) -> str | None:
    """Return a secret value.

    Order of precedence:
    1) st.secrets[key] (for Streamlit Cloud deployment)
    2) os.getenv(key, default) (for local development, including .env file)
    """
    try:
        # Prefer Streamlit secrets for deployed environments
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # st.secrets may not be initialized in some contexts
        pass

    # Check environment variable (includes .env file if loaded)
    return os.getenv(key, default)


