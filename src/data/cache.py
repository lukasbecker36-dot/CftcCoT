"""SQLite caching layer for CFTC COT data."""

import logging
import os
import sqlite3
from datetime import datetime, timedelta

import pandas as pd

from src.data.downloader import download_all_reports, download_report
from src.data.parser import parse_report
from src.utils.constants import (
    CURRENT_YEAR,
    DB_PATH,
    REFRESH_INTERVAL_DAYS,
    START_YEAR,
    YEARS,
)

logger = logging.getLogger(__name__)

TABLE_NAME = "cot_data"
META_TABLE = "metadata"


def _ensure_db_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    _ensure_db_dir()
    return sqlite3.connect(DB_PATH)


def _init_meta(conn: sqlite3.Connection):
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {META_TABLE} ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT"
        ")"
    )
    conn.commit()


def _get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    _init_meta(conn)
    row = conn.execute(
        f"SELECT value FROM {META_TABLE} WHERE key = ?", (key,)
    ).fetchone()
    return row[0] if row else None


def _set_meta(conn: sqlite3.Connection, key: str, value: str):
    _init_meta(conn)
    conn.execute(
        f"INSERT OR REPLACE INTO {META_TABLE} (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row[0] > 0


def _store_data(conn: sqlite3.Connection, df: pd.DataFrame, report_type: str):
    """Store parsed data in SQLite, replacing data for the given report type."""
    # Delete existing data for this report type
    if _table_exists(conn, TABLE_NAME):
        conn.execute(
            f"DELETE FROM {TABLE_NAME} WHERE report_type = ?", (report_type,)
        )

    df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.commit()


def _store_current_year(conn: sqlite3.Connection, report_type: str):
    """Download and store only the current year's data for a report type."""
    raw = download_report(report_type, CURRENT_YEAR)
    if raw is None:
        logger.warning("Failed to download current year %s data", report_type)
        return

    parsed = parse_report(raw, report_type)

    # Delete only current year data for this report type
    if _table_exists(conn, TABLE_NAME):
        year_start = f"{CURRENT_YEAR}-01-01"
        conn.execute(
            f"DELETE FROM {TABLE_NAME} WHERE report_type = ? AND date >= ?",
            (report_type, year_start),
        )

    parsed.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.commit()


def needs_refresh(conn: sqlite3.Connection) -> bool:
    """Check if data needs to be refreshed (older than REFRESH_INTERVAL_DAYS)."""
    last_update = _get_meta(conn, "last_update")
    if last_update is None:
        return True
    last_dt = datetime.fromisoformat(last_update)
    return datetime.now() - last_dt > timedelta(days=REFRESH_INTERVAL_DAYS)


def load_initial_data(progress_callback=None) -> pd.DataFrame:
    """Load all data, downloading if necessary.

    Args:
        progress_callback: Optional callable(message, progress_fraction)
            for reporting progress in the UI.

    Returns:
        Combined DataFrame with all COT data.
    """
    conn = _get_conn()

    if _table_exists(conn, TABLE_NAME) and not needs_refresh(conn):
        logger.info("Loading cached data from SQLite")
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
        df["date"] = pd.to_datetime(df["date"])
        conn.close()
        return df

    # Full download needed
    report_types = ["disaggregated", "tff"]
    total_steps = len(report_types) * len(YEARS)
    current_step = 0

    all_frames = []
    for report_type in report_types:
        for year in YEARS:
            if progress_callback:
                progress_callback(
                    f"Downloading {report_type} {year}...",
                    current_step / total_steps,
                )

            raw = download_report(report_type, year)
            if raw is not None:
                parsed = parse_report(raw, report_type)
                all_frames.append(parsed)

            current_step += 1

    if not all_frames:
        conn.close()
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)

    # Store everything
    if _table_exists(conn, TABLE_NAME):
        conn.execute(f"DROP TABLE {TABLE_NAME}")
    combined.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    _set_meta(conn, "last_update", datetime.now().isoformat())
    conn.commit()

    if progress_callback:
        progress_callback("Data loaded!", 1.0)

    conn.close()
    return combined


def refresh_current_year(progress_callback=None) -> pd.DataFrame:
    """Refresh only the current year's data and return the full dataset."""
    conn = _get_conn()

    for i, report_type in enumerate(["disaggregated", "tff"]):
        if progress_callback:
            progress_callback(
                f"Refreshing {report_type} {CURRENT_YEAR}...",
                i / 2,
            )
        _store_current_year(conn, report_type)

    _set_meta(conn, "last_update", datetime.now().isoformat())

    df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
    df["date"] = pd.to_datetime(df["date"])
    conn.close()

    if progress_callback:
        progress_callback("Refresh complete!", 1.0)

    return df


def get_last_update() -> str | None:
    """Return the last update timestamp, or None."""
    conn = _get_conn()
    val = _get_meta(conn, "last_update")
    conn.close()
    return val
