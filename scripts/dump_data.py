#!/usr/bin/env python3
"""Dump CFTC COT data from Turso to local CSV files.

Usage:
    export TURSO_DATABASE_URL="libsql://your-db.turso.io"
    export TURSO_AUTH_TOKEN="eyJ..."
    python scripts/dump_data.py

Outputs:
    data/cot_disaggregated.csv
    data/cot_tff.csv
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import csv

BATCH_SIZE = 5000


def get_turso_config():
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        print("ERROR: Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables")
        sys.exit(1)
    return url.replace("libsql://", "https://").rstrip("/"), token


def query_turso(base_url, token, sql, params=None):
    """Execute a query against Turso and return (columns, rows)."""
    stmt = {"sql": sql}
    if params:
        stmt["args"] = [
            {"type": "integer", "value": str(v)} if isinstance(v, int)
            else {"type": "text", "value": str(v)}
            for v in params
        ]

    resp = requests.post(
        f"{base_url}/v2/pipeline",
        json={"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    result = data["results"][0]
    if result.get("type") == "error":
        print(f"Query error: {result['error']}")
        sys.exit(1)

    response = result["response"]["result"]
    columns = [c["name"] for c in response["cols"]]
    rows = []
    for row in response["rows"]:
        rows.append([v.get("value") for v in row])
    return columns, rows


def dump_report(base_url, token, report_type, output_path):
    """Dump a single report type to CSV in paginated batches."""
    print(f"Querying {report_type} data...")

    # Get total count
    _, count_rows = query_turso(
        base_url, token,
        "SELECT COUNT(*) FROM cot_data WHERE report_type = ?",
        [report_type],
    )
    total = int(count_rows[0][0])
    print(f"  Total rows: {total}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    columns = None
    rows_written = 0

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        offset = 0
        while offset < total:
            sql = (
                "SELECT * FROM cot_data "
                "WHERE report_type = ? "
                "ORDER BY date, commodity "
                f"LIMIT {BATCH_SIZE} OFFSET {offset}"
            )
            cols, rows = query_turso(base_url, token, sql, [report_type])

            if columns is None:
                columns = cols
                writer.writerow(columns)

            writer.writerows(rows)
            rows_written += len(rows)
            offset += BATCH_SIZE
            print(f"  Fetched {rows_written}/{total} rows...")

    print(f"  Written to {output_path}")


def main():
    base_url, token = get_turso_config()

    # Check if table exists
    _, rows = query_turso(base_url, token,
        "SELECT COUNT(*) as cnt FROM cot_data")
    total = rows[0][0] if rows else 0
    print(f"Total rows in cot_data: {total}")

    if int(total) == 0:
        print("No data in database. Run the Streamlit app first to populate.")
        sys.exit(1)

    dump_report(base_url, token, "disaggregated", "data/cot_disaggregated.csv")
    dump_report(base_url, token, "tff", "data/cot_tff.csv")

    print("\nDone! CSV files written to data/")


if __name__ == "__main__":
    main()
