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


def get_turso_config():
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        print("ERROR: Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables")
        sys.exit(1)
    return url.replace("libsql://", "https://").rstrip("/"), token


def query_turso(base_url, token, sql):
    """Execute a query against Turso and return (columns, rows)."""
    resp = requests.post(
        f"{base_url}/v2/pipeline",
        json={"requests": [{"type": "execute", "stmt": {"sql": sql}}, {"type": "close"}]},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60,
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
    """Dump a single report type to CSV."""
    print(f"Querying {report_type} data...")
    sql = f"SELECT * FROM cot_data WHERE report_type = '{report_type}' ORDER BY date"
    columns, rows = query_turso(base_url, token, sql)
    print(f"  Got {len(rows)} rows")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    print(f"  Written to {output_path}")


def main():
    base_url, token = get_turso_config()

    # Check if table exists
    columns, rows = query_turso(base_url, token,
        "SELECT COUNT(*) as cnt FROM cot_data")
    total = rows[0][0] if rows else 0
    print(f"Total rows in cot_data: {total}")

    if int(total) == 0:
        print("No data in database. Run the Streamlit app first to populate.")
        sys.exit(1)

    dump_report(base_url, token, "disaggregated", "data/cot_disaggregated.csv")
    dump_report(base_url, token, "tff", "data/cot_tff.csv")

    print("\nDone! Now commit and push the CSV files:")
    print("  git add data/*.csv")
    print("  git commit -m 'Update COT data dump'")
    print("  git push")


if __name__ == "__main__":
    main()
