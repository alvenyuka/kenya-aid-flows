"""Stage 1: download Kenya's IATI data from the d-portal query API.

Writes one raw CSV per table to data/raw/<table>_<YYYY-MM-DD>.csv and a fetch log to
data/raw/fetch_log.json. Without --refresh the most recent download on disk is reused, whatever
its date, so a re-run does not hit the API again; fetch_log.json then carries that download's
date as the snapshot date. Pass --refresh to download again.
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

API_URL = "https://d-portal.org/q.json"
USER_AGENT = "kenya-aid-flows (learning project by Alven Yuka; monthly refresh)"
PAGE_SIZE = 5000
PAUSE_SECONDS = 1.0
MAX_TRIES = 4

# Each table: the d-portal "from", the Kenya filter, and the columns that give a
# stable page order (without an order, pages can repeat or skip rows).
TABLES = {
    "act": {
        "filter": {"country_code": "KE"},
        "orderby": "aid",
    },
    "trans": {
        "filter": {"trans_country": "KE"},
        "orderby": "aid,trans_id,trans_day,trans_code,trans_value",
    },
    "budget": {
        "filter": {"budget_country": "KE"},
        "orderby": "aid,budget_id,budget_day_start,budget_day_end,budget_value",
    },
}


def get_json(params):
    """One GET with retries. Waits longer after each failure."""
    headers = {"User-Agent": USER_AGENT}
    wait = 2
    for attempt in range(1, MAX_TRIES + 1):
        try:
            response = requests.get(API_URL, params=params, headers=headers, timeout=120)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            print(f"  attempt {attempt} failed: {error}")
            if attempt == MAX_TRIES:
                raise
            time.sleep(wait)
            wait = wait * 2


def latest_download(table_name):
    """The newest raw CSV for a table, or None if it was never downloaded."""
    files = sorted(RAW_DIR.glob(f"{table_name}_*.csv"))
    if len(files) == 0:
        return None
    return files[-1]


def count_rows(table_name):
    """Ask the API how many rows the filter matches, to check the download against."""
    params = {"from": table_name, "select": "count"}
    params.update(TABLES[table_name]["filter"])
    result = get_json(params)
    return int(result["rows"][0]["count"])


def fetch_table(table_name):
    """Page through one table and return (DataFrame, number of pages)."""
    all_rows = []
    offset = 0
    pages = 0
    while True:
        params = {
            "from": table_name,
            "limit": PAGE_SIZE,
            "offset": offset,
            "orderby": TABLES[table_name]["orderby"],
        }
        params.update(TABLES[table_name]["filter"])
        result = get_json(params)
        rows = result["rows"]
        pages = pages + 1
        all_rows.extend(rows)
        print(f"  {table_name}: page {pages}, {len(all_rows)} rows so far")
        if len(rows) < PAGE_SIZE:
            break
        offset = offset + PAGE_SIZE
        time.sleep(PAUSE_SECONDS)
    return pd.DataFrame(all_rows), pages


def main():
    refresh = "--refresh" in sys.argv
    today = date.today().isoformat()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    fetch_log = {"fetch_date": today, "source": "https://d-portal.org/q.json", "tables": {}}
    file_dates = []

    for table_name in TABLES:
        csv_path = RAW_DIR / f"{table_name}_{today}.csv"
        log_path = RAW_DIR / f"fetch_log_{table_name}_{today}.json"

        # Without --refresh, reuse the most recent download of this table, whatever
        # its date, so a re-run never fetches again by accident.
        latest_csv = latest_download(table_name)
        if latest_csv is not None and not refresh:
            csv_path = latest_csv
            file_date = latest_csv.stem.split("_")[-1]
            log_path = RAW_DIR / f"fetch_log_{table_name}_{file_date}.json"
            print(f"{table_name}: using cached {csv_path.name}")
            fetch_log["tables"][table_name] = json.loads(log_path.read_text())
            file_dates.append(file_date)
            continue

        print(f"{table_name}: downloading")
        expected = count_rows(table_name)
        table, pages = fetch_table(table_name)
        table.to_csv(csv_path, index=False)

        table_log = {
            "rows_fetched": len(table),
            "rows_expected_by_api_count": expected,
            "pages": pages,
            "file": csv_path.name,
        }
        log_path.write_text(json.dumps(table_log, indent=2))
        fetch_log["tables"][table_name] = table_log
        file_dates.append(today)

        if len(table) != expected:
            print(f"WARNING: {table_name} fetched {len(table)} rows but the API count says {expected}")

    # The snapshot date is the date of the data in use, which is older than today when
    # the cache is reused.
    fetch_log["fetch_date"] = max(file_dates)

    (RAW_DIR / "fetch_log.json").write_text(json.dumps(fetch_log, indent=2))
    print(json.dumps(fetch_log, indent=2))


if __name__ == "__main__":
    main()
