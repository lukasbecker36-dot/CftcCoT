"""Caching layer for CFTC COT data — supports Turso and local SQLite."""

import logging
from datetime import datetime, timedelta

import pandas as pd

from src.data.db import get_connection
from src.data.downloader import download_report
from src.data.parser import parse_report
from src.utils.constants import (
    CURRENT_YEAR,
    REFRESH_INTERVAL_DAYS,
    YEARS,
)

logger = logging.getLogger(__name__)

TABLE_NAME = "cot_data"
META_TABLE = "metadata"


def _init_meta(conn):
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {META_TABLE} ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT"
        ")"
    )
    conn.commit()


def _get_meta(conn, key: str) -> str | None:
    _init_meta(conn)
    row = conn.execute(
        f"SELECT value FROM {META_TABLE} WHERE key = ?", (key,)
    ).fetchone()
    return row[0] if row else None


def _set_meta(conn, key: str, value: str):
    _init_meta(conn)
    conn.execute(
        f"INSERT OR REPLACE INTO {META_TABLE} (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row[0] > 0


def _init_cot_table(conn):
    """Create the cot_data table if it doesn't exist."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            commodity TEXT,
            cftc_code TEXT,
            date TEXT,
            commodity_short TEXT,
            report_type TEXT,
            open_interest REAL,
            -- Disaggregated columns
            prod_merc_long REAL, prod_merc_short REAL,
            swap_long REAL, swap_short REAL, swap_spread REAL,
            managed_money_long REAL, managed_money_short REAL, managed_money_spread REAL,
            other_long REAL, other_short REAL, other_spread REAL,
            nonreportable_long REAL, nonreportable_short REAL,
            change_oi REAL,
            change_prod_merc_long REAL, change_prod_merc_short REAL,
            change_swap_long REAL, change_swap_short REAL,
            change_managed_money_long REAL, change_managed_money_short REAL,
            change_other_long REAL, change_other_short REAL,
            pct_prod_merc_long REAL, pct_prod_merc_short REAL,
            pct_swap_long REAL, pct_swap_short REAL, pct_swap_spread REAL,
            pct_managed_money_long REAL, pct_managed_money_short REAL, pct_managed_money_spread REAL,
            pct_other_long REAL, pct_other_short REAL, pct_other_spread REAL,
            pct_nonreportable_long REAL, pct_nonreportable_short REAL,
            -- TFF columns
            dealer_long REAL, dealer_short REAL, dealer_spread REAL,
            asset_mgr_long REAL, asset_mgr_short REAL, asset_mgr_spread REAL,
            lev_money_long REAL, lev_money_short REAL, lev_money_spread REAL,
            change_dealer_long REAL, change_dealer_short REAL,
            change_asset_mgr_long REAL, change_asset_mgr_short REAL,
            change_lev_money_long REAL, change_lev_money_short REAL,
            pct_dealer_long REAL, pct_dealer_short REAL, pct_dealer_spread REAL,
            pct_asset_mgr_long REAL, pct_asset_mgr_short REAL, pct_asset_mgr_spread REAL,
            pct_lev_money_long REAL, pct_lev_money_short REAL, pct_lev_money_spread REAL,
            -- Concentration ratios
            conc4_long REAL, conc4_short REAL,
            conc8_long REAL, conc8_short REAL,
            conc4_net_long REAL, conc4_net_short REAL,
            conc8_net_long REAL, conc8_net_short REAL
        )
    """)
    conn.commit()


def _insert_dataframe(conn, df: pd.DataFrame):
    """Insert a DataFrame into the cot_data table row by row.

    Uses parameterized INSERT to work with both sqlite3 and libsql.
    """
    _init_cot_table(conn)

    # Get the columns that exist in both the table and the DataFrame
    cursor = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
    table_cols = [row[1] for row in cursor.fetchall()]
    common_cols = [c for c in table_cols if c in df.columns]

    placeholders = ", ".join(["?"] * len(common_cols))
    col_names = ", ".join(common_cols)
    insert_sql = f"INSERT INTO {TABLE_NAME} ({col_names}) VALUES ({placeholders})"

    for _, row in df.iterrows():
        values = [
            str(row[c]) if pd.notna(row[c]) and c == "date" else
            None if pd.isna(row[c]) else
            row[c]
            for c in common_cols
        ]
        conn.execute(insert_sql, values)

    conn.commit()


def _store_current_year(conn, report_type: str):
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
        conn.commit()

    _insert_dataframe(conn, parsed)


def needs_refresh(conn) -> bool:
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
    conn = get_connection()

    if _table_exists(conn, TABLE_NAME) and not needs_refresh(conn):
        logger.info("Loading cached data from database")
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

    # Clear existing data and insert fresh
    if _table_exists(conn, TABLE_NAME):
        conn.execute(f"DELETE FROM {TABLE_NAME}")
        conn.commit()
    _insert_dataframe(conn, combined)

    _set_meta(conn, "last_update", datetime.now().isoformat())

    if progress_callback:
        progress_callback("Data loaded!", 1.0)

    conn.close()
    return combined


def refresh_current_year(progress_callback=None) -> pd.DataFrame:
    """Refresh only the current year's data and return the full dataset."""
    conn = get_connection()

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
    conn = get_connection()
    try:
        val = _get_meta(conn, "last_update")
    except Exception:
        val = None
    conn.close()
    return val
