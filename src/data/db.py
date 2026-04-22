"""Database connection layer — supports Turso (HTTP API) and local SQLite.

Uses Turso when TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are configured
in Streamlit secrets or environment variables. Falls back to local SQLite.

The Turso connection uses the HTTP pipeline API directly via requests,
avoiding native dependencies that can't build on Streamlit Cloud.
"""

import logging
import os
import sqlite3

import requests

logger = logging.getLogger(__name__)

_config_loaded = False
_USE_TURSO = False
_TURSO_URL = None
_TURSO_TOKEN = None


def _ensure_config():
    """Load Turso config lazily on first use (not at import time).

    Streamlit secrets are only available after the Streamlit runtime
    initializes, so we defer config loading until get_connection() is called.
    """
    global _config_loaded, _USE_TURSO, _TURSO_URL, _TURSO_TOKEN

    if _config_loaded:
        return

    # Try Streamlit secrets first
    try:
        import streamlit as st
        secrets = st.secrets
        print(f"[DB] Streamlit secrets available. Keys: {list(secrets.keys())}", flush=True)
        if "TURSO_DATABASE_URL" in secrets:
            _TURSO_URL = secrets["TURSO_DATABASE_URL"]
            print(f"[DB] Got URL from secrets: {_TURSO_URL[:30]}...", flush=True)
        if "TURSO_AUTH_TOKEN" in secrets:
            _TURSO_TOKEN = secrets["TURSO_AUTH_TOKEN"]
            print("[DB] Got token from secrets", flush=True)
    except Exception as e:
        print(f"[DB] Failed to read Streamlit secrets: {type(e).__name__}: {e}", flush=True)

    # Fall back to environment variables
    if not _TURSO_URL:
        _TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
        if _TURSO_URL:
            print("[DB] Got TURSO_DATABASE_URL from environment")
    if not _TURSO_TOKEN:
        _TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
        if _TURSO_TOKEN:
            print("[DB] Got TURSO_AUTH_TOKEN from environment")

    _USE_TURSO = bool(_TURSO_URL and _TURSO_TOKEN)
    _config_loaded = True

    if _USE_TURSO:
        print(f"[DB] Using Turso database: {_TURSO_URL}")
    else:
        print(f"[DB] Turso NOT configured — using local SQLite. URL={bool(_TURSO_URL)}, Token={bool(_TURSO_TOKEN)}")


class TursoConnection:
    """A minimal DB-API-like connection wrapper over Turso's HTTP pipeline API."""

    def __init__(self, url: str, token: str):
        # Convert libsql:// to https://
        self._base_url = url.replace("libsql://", "https://").rstrip("/")
        self._api_url = f"{self._base_url}/v2/pipeline"
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def execute(self, sql: str, params: tuple | list | None = None):
        """Execute a single SQL statement and return a cursor-like object."""
        stmt = {"type": "execute", "stmt": {"sql": sql}}
        if params:
            stmt["stmt"]["args"] = [
                self._serialize_value(v) for v in params
            ]

        body = {"requests": [stmt, {"type": "close"}]}
        resp = requests.post(
            self._api_url, json=body, headers=self._headers, timeout=120
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if results and results[0].get("type") == "error":
            error = results[0]["error"]
            raise Exception(f"Turso error: {error.get('message', error)}")

        if results and results[0].get("type") == "ok":
            return TursoCursor(results[0]["response"]["result"])
        return TursoCursor(None)

    def executemany(self, sql: str, param_list: list):
        """Execute a SQL statement with multiple parameter sets."""
        reqs = []
        for params in param_list:
            stmt = {"type": "execute", "stmt": {"sql": sql}}
            if params:
                stmt["stmt"]["args"] = [
                    self._serialize_value(v) for v in params
                ]
            reqs.append(stmt)
        reqs.append({"type": "close"})

        # Turso has a limit on pipeline size, batch in chunks
        chunk_size = 500
        for i in range(0, len(reqs), chunk_size):
            chunk = reqs[i : i + chunk_size]
            if chunk[-1].get("type") != "close":
                chunk.append({"type": "close"})
            body = {"requests": chunk}
            resp = requests.post(
                self._api_url, json=body, headers=self._headers, timeout=120
            )
            resp.raise_for_status()

    def commit(self):
        """No-op — Turso auto-commits."""
        pass

    def close(self):
        """No-op — HTTP is stateless."""
        pass

    @staticmethod
    def _serialize_value(v):
        """Convert a Python value to a Turso API value object."""
        if v is None:
            return {"type": "null", "value": None}
        elif isinstance(v, int):
            return {"type": "integer", "value": str(v)}
        elif isinstance(v, float):
            return {"type": "float", "value": v}
        else:
            return {"type": "text", "value": str(v)}


class TursoCursor:
    """Minimal cursor-like object wrapping Turso query results."""

    def __init__(self, result):
        self._rows = []
        self._columns = []
        if result:
            self._columns = [c["name"] for c in result.get("cols", [])]
            for row in result.get("rows", []):
                self._rows.append(
                    tuple(self._deserialize_value(v) for v in row)
                )

    def fetchone(self):
        if self._rows:
            return self._rows[0]
        return None

    def fetchall(self):
        return self._rows

    @property
    def description(self):
        """Return column descriptions (name only, rest None)."""
        return [(c, None, None, None, None, None, None) for c in self._columns]

    @staticmethod
    def _deserialize_value(v):
        """Convert a Turso API value to a Python value."""
        if v.get("type") == "null":
            return None
        elif v.get("type") == "integer":
            return int(v["value"])
        elif v.get("type") == "float":
            return float(v["value"])
        else:
            return v.get("value")


def get_connection():
    """Get a database connection (Turso or local SQLite).

    Returns a connection object with execute/commit/close methods.
    """
    _ensure_config()
    if _USE_TURSO:
        return TursoConnection(_TURSO_URL, _TURSO_TOKEN)
    else:
        from src.utils.constants import DB_PATH
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        return sqlite3.connect(DB_PATH)


def is_turso() -> bool:
    """Return True if using Turso, False if local SQLite."""
    _ensure_config()
    return _USE_TURSO
