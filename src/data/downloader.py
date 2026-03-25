"""Download CFTC COT data files from the CFTC website."""

import io
import zipfile
import logging

import pandas as pd
import requests

from src.utils.constants import URLS, YEARS

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3


def download_zip(url: str) -> io.BytesIO | None:
    """Download a ZIP file and return it as a BytesIO object."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return io.BytesIO(resp.content)
        except requests.RequestException as e:
            logger.warning("Attempt %d failed for %s: %s", attempt + 1, url, e)
    logger.error("Failed to download %s after %d attempts", url, MAX_RETRIES)
    return None


def extract_csv_from_zip(zip_bytes: io.BytesIO) -> pd.DataFrame | None:
    """Extract the first CSV/text file from a ZIP archive into a DataFrame."""
    try:
        with zipfile.ZipFile(zip_bytes) as zf:
            csv_files = [f for f in zf.namelist() if f.endswith((".csv", ".txt"))]
            if not csv_files:
                logger.error("No CSV/TXT file found in ZIP")
                return None
            with zf.open(csv_files[0]) as f:
                return pd.read_csv(f, low_memory=False)
    except (zipfile.BadZipFile, Exception) as e:
        logger.error("Error extracting ZIP: %s", e)
        return None


def download_report(report_type: str, year: int) -> pd.DataFrame | None:
    """Download a single report for a given year.

    Args:
        report_type: 'disaggregated' or 'tff'
        year: e.g. 2024

    Returns:
        DataFrame with raw CFTC data, or None on failure.
    """
    url_template = URLS.get(report_type)
    if not url_template:
        logger.error("Unknown report type: %s", report_type)
        return None

    url = url_template.format(year=year)
    logger.info("Downloading %s %d from %s", report_type, year, url)

    zip_bytes = download_zip(url)
    if zip_bytes is None:
        return None

    return extract_csv_from_zip(zip_bytes)


def download_all_reports(report_type: str, years: list[int] | None = None) -> pd.DataFrame | None:
    """Download and concatenate reports for multiple years.

    Args:
        report_type: 'disaggregated' or 'tff'
        years: List of years to download. Defaults to YEARS from constants.

    Returns:
        Combined DataFrame, or None if all downloads failed.
    """
    if years is None:
        years = YEARS

    frames = []
    for year in years:
        df = download_report(report_type, year)
        if df is not None:
            frames.append(df)

    if not frames:
        return None

    return pd.concat(frames, ignore_index=True)
