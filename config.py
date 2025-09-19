import os
import streamlit as st


def get_secret(key: str, default: str | None = None) -> str | None:
    """Return a secret value.

    Order of precedence:
    1) st.secrets[key]
    2) os.getenv(key, default) for local development
    """
    try:
        # Prefer Streamlit secrets for deployed environments
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # st.secrets may not be initialized in some contexts
        pass

    return os.getenv(key, default)


