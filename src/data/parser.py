"""Parse and normalize raw CFTC COT data."""

import logging

import pandas as pd

from src.utils.constants import COLUMN_MAPS

logger = logging.getLogger(__name__)


def normalize_columns(df: pd.DataFrame, report_type: str) -> pd.DataFrame:
    """Rename columns to standardized names and select only needed columns.

    Args:
        df: Raw DataFrame from CFTC CSV.
        report_type: 'disaggregated' or 'tff'

    Returns:
        DataFrame with renamed and filtered columns.
    """
    col_map = COLUMN_MAPS.get(report_type)
    if col_map is None:
        raise ValueError(f"Unknown report type: {report_type}")

    # Strip whitespace from column names (CFTC files sometimes have trailing spaces)
    df.columns = df.columns.str.strip()

    # Only rename columns that exist in the data
    available = {k: v for k, v in col_map.items() if k in df.columns}
    missing = set(col_map.keys()) - set(available.keys())
    if missing:
        logger.warning("Missing columns in %s data: %s", report_type, missing)

    df = df.rename(columns=available)

    # Keep only the renamed columns
    keep = [v for v in available.values()]
    df = df[keep].copy()

    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date columns into proper datetime objects."""
    if "report_date" in df.columns:
        df["date"] = pd.to_datetime(df["report_date"], errors="coerce")
        df = df.drop(columns=["report_date"], errors="ignore")
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], format="%y%m%d", errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def clean_commodity_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize commodity names."""
    if "commodity" in df.columns:
        # Strip whitespace and standardize
        df["commodity"] = df["commodity"].str.strip()
        # Extract just the commodity name (before the dash with exchange info)
        df["commodity_short"] = df["commodity"].str.split(" - ").str[0].str.strip()
    return df


def convert_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Convert position columns to numeric types."""
    exclude = {"commodity", "commodity_short", "cftc_code", "date", "report_type"}
    for col in df.columns:
        if col not in exclude:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def parse_report(df: pd.DataFrame, report_type: str) -> pd.DataFrame:
    """Full parsing pipeline for a raw CFTC DataFrame.

    Args:
        df: Raw DataFrame from CFTC CSV.
        report_type: 'disaggregated' or 'tff'

    Returns:
        Cleaned, normalized DataFrame ready for storage.
    """
    df = normalize_columns(df, report_type)
    df = parse_dates(df)
    df = clean_commodity_names(df)
    df = convert_numeric(df)
    df["report_type"] = report_type
    return df
