"""Database connection layer — supports Turso (libSQL) and local SQLite.

Uses Turso when TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are configured
in Streamlit secrets or environment variables. Falls back to local SQLite.
"""

import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

_USE_TURSO = False
_TURSO_URL = None
_TURSO_TOKEN = None


def _load_turso_config():
    """Load Turso config from Streamlit secrets or environment variables."""
    global _USE_TURSO, _TURSO_URL, _TURSO_TOKEN

    # Try Streamlit secrets first
    try:
        import streamlit as st
        _TURSO_URL = st.secrets.get("TURSO_DATABASE_URL")
        _TURSO_TOKEN = st.secrets.get("TURSO_AUTH_TOKEN")
    except Exception:
        pass

    # Fall back to environment variables
    if not _TURSO_URL:
        _TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
    if not _TURSO_TOKEN:
        _TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

    _USE_TURSO = bool(_TURSO_URL and _TURSO_TOKEN)

    if _USE_TURSO:
        logger.info("Using Turso database: %s", _TURSO_URL)
    else:
        logger.info("Turso not configured — using local SQLite")


# Load config on import
_load_turso_config()


def get_connection():
    """Get a database connection (Turso or local SQLite).

    Returns a dbapi2-compatible connection object.
    """
    if _USE_TURSO:
        import libsql_experimental as libsql
        return libsql.connect(
            database=_TURSO_URL,
            auth_token=_TURSO_TOKEN,
        )
    else:
        from src.utils.constants import DB_PATH
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        return sqlite3.connect(DB_PATH)


def is_turso() -> bool:
    """Return True if using Turso, False if local SQLite."""
    return _USE_TURSO
