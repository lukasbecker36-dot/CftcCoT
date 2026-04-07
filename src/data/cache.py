"""Caching layer for CFTC COT data — supports Turso and local SQLite."""

import logging
import sqlite3
from datetime import datetime, timedelta

import pandas as pd

from src.data.db import get_connection, is_turso
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

# All columns in the cot_data table, in order
COT_COLUMNS = [
    "commodity", "cftc_code", "date", "commodity_short", "report_type",
    "open_interest",
    # Disaggregated
    "prod_merc_long", "prod_merc_short",
    "swap_long", "swap_short", "swap_spread",
    "managed_money_long", "managed_money_short", "managed_money_spread",
    "other_long", "other_short", "other_spread",
    "nonreportable_long", "nonreportable_short",
    "change_oi",
    "change_prod_merc_long", "change_prod_merc_short",
    "change_swap_long", "change_swap_short",
    "change_managed_money_long", "change_managed_money_short",
    "change_other_long", "change_other_short",
    "pct_prod_merc_long", "pct_prod_merc_short",
    "pct_swap_long", "pct_swap_short", "pct_swap_spread",
    "pct_managed_money_long", "pct_managed_money_short", "pct_managed_money_spread",
    "pct_other_long", "pct_other_short", "pct_other_spread",
    "pct_nonreportable_long", "pct_nonreportable_short",
    # TFF
    "dealer_long", "dealer_short", "dealer_spread",
    "asset_mgr_long", "asset_mgr_short", "asset_mgr_spread",
    "lev_money_long", "lev_money_short", "lev_money_spread",
    "change_dealer_long", "change_dealer_short",
    "change_asset_mgr_long", "change_asset_mgr_short",
    "change_lev_money_long", "change_lev_money_short",
    "pct_dealer_long", "pct_dealer_short", "pct_dealer_spread",
    "pct_asset_mgr_long", "pct_asset_mgr_short", "pct_asset_mgr_spread",
    "pct_lev_money_long", "pct_lev_money_short", "pct_lev_money_spread",
    # Concentration
    "conc4_long", "conc4_short",
    "conc8_long", "conc8_short",
    "conc4_net_long", "conc4_net_short",
    "conc8_net_long", "conc8_net_short",
]


TURSO_BATCH_SIZE = 5000


def _query_to_dataframe(conn, sql: str, params: tuple | None = None) -> pd.DataFrame:
    """Execute a SELECT query and return results as a DataFrame.

    Works with both sqlite3 and TursoConnection.
    For Turso, paginates large queries to avoid HTTP timeouts.
    """
    if isinstance(conn, sqlite3.Connection):
        return pd.read_sql(sql, conn, params=params)

    # Turso HTTP connection — paginate to avoid timeouts on large tables
    # Check if this is a simple SELECT * that can be paginated
    sql_upper = sql.strip().upper()
    if "LIMIT" not in sql_upper and "SELECT" in sql_upper:
        frames = []
        offset = 0
        columns = None
        while True:
            paged_sql = f"{sql} LIMIT {TURSO_BATCH_SIZE} OFFSET {offset}"
            cursor = conn.execute(paged_sql, params)
            rows = cursor.fetchall()
            if columns is None and cursor.description:
                columns = [desc[0] for desc in cursor.description]
            if not rows:
                break
            frames.append(pd.DataFrame(rows, columns=columns))
            if len(rows) < TURSO_BATCH_SIZE:
                break
            offset += TURSO_BATCH_SIZE

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    # Non-paginated query
    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return pd.DataFrame(rows, columns=columns)


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
    col_defs = []
    for col in COT_COLUMNS:
        if col in ("commodity", "cftc_code", "date", "commodity_short", "report_type"):
            col_defs.append(f"{col} TEXT")
        else:
            col_defs.append(f"{col} REAL")

    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} ({', '.join(col_defs)})"
    )
    conn.commit()


def _insert_dataframe(conn, df: pd.DataFrame):
    """Insert a DataFrame into the cot_data table."""
    _init_cot_table(conn)

    # Use only columns present in both the table schema and DataFrame
    common_cols = [c for c in COT_COLUMNS if c in df.columns]

    placeholders = ", ".join(["?"] * len(common_cols))
    col_names = ", ".join(common_cols)
    insert_sql = f"INSERT INTO {TABLE_NAME} ({col_names}) VALUES ({placeholders})"

    if isinstance(conn, sqlite3.Connection):
        # Use executemany for speed with local SQLite
        rows = []
        for _, row in df.iterrows():
            values = tuple(
                str(row[c]) if pd.notna(row[c]) and c == "date" else
                None if pd.isna(row[c]) else
                float(row[c]) if c not in ("commodity", "cftc_code", "date", "commodity_short", "report_type") and pd.notna(row[c]) else
                row[c]
                for c in common_cols
            )
            rows.append(values)
        conn.executemany(insert_sql, rows)
        conn.commit()
    else:
        # Turso HTTP — batch via executemany
        rows = []
        for _, row in df.iterrows():
            values = [
                str(row[c]) if pd.notna(row[c]) and c == "date" else
                None if pd.isna(row[c]) else
                float(row[c]) if c not in ("commodity", "cftc_code", "date", "commodity_short", "report_type") and pd.notna(row[c]) else
                row[c]
                for c in common_cols
            ]
            rows.append(values)
        conn.executemany(insert_sql, rows)


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
    """Check if data needs to be refreshed.

    Only triggers a full re-download if the most recent data point in the
    database is older than REFRESH_INTERVAL_DAYS. The metadata last_update
    is used as a fast-path cache; if missing or stale, we check the data.
    """
    # Fast path: check metadata
    last_update = _get_meta(conn, "last_update")
    print(f"[CACHE] last_update metadata = {last_update}", flush=True)
    if last_update is not None:
        last_dt = datetime.fromisoformat(last_update)
        age = datetime.now() - last_dt
        if age <= timedelta(days=REFRESH_INTERVAL_DAYS):
            return False

    # Metadata missing or stale — check actual data dates
    try:
        cursor = conn.execute(f"SELECT MAX(date) FROM {TABLE_NAME}")
        row = cursor.fetchone()
        if row and row[0]:
            max_date = datetime.fromisoformat(str(row[0])[:19])
            data_age = datetime.now() - max_date
            print(f"[CACHE] Latest data date: {max_date}, age: {data_age.days}d", flush=True)
            # COT data is weekly (released Fridays), so up to ~14 days old is normal
            if data_age < timedelta(days=14):
                # Data is fresh enough — update metadata timestamp
                _set_meta(conn, "last_update", datetime.now().isoformat())
                return False
    except Exception as e:
        print(f"[CACHE] Error checking max date: {e}", flush=True)

    return True


def load_initial_data(progress_callback=None) -> pd.DataFrame:
    """Load all data, downloading if necessary."""
    conn = get_connection()

    table_exists = _table_exists(conn, TABLE_NAME)
    refresh_needed = needs_refresh(conn) if table_exists else True
    print(f"[CACHE] table_exists={table_exists}, refresh_needed={refresh_needed}", flush=True)

    if table_exists and not refresh_needed:
        print("[CACHE] Loading from database...", flush=True)
        df = _query_to_dataframe(conn, f"SELECT * FROM {TABLE_NAME}")
        print(f"[CACHE] Loaded {len(df)} rows from database", flush=True)
        df["date"] = pd.to_datetime(df["date"])
        conn.close()
        return df

    print("[CACHE] Full download from CFTC needed", flush=True)
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

    df = _query_to_dataframe(conn, f"SELECT * FROM {TABLE_NAME}")
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
