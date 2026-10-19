"""Stage 2: clean the three raw tables and write parquet files plus the rule log."""
from pathlib import Path

import pandas as pd

from clean_activities import clean_activities
from clean_budgets import clean_budgets
from clean_transactions import clean_transactions
from rule_log import clear_log, save_log

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEAN_DIR = PROJECT_DIR / "data" / "clean"


def latest_raw_file(table_name):
    """The raw file with the newest fetch date in its name."""
    files = sorted(RAW_DIR.glob(f"{table_name}_*.csv"))
    return files[-1]


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    clear_log()

    # Codes and refs are read as text: a sector like 01010 must keep its zero.
    text_columns = {
        "reporting_ref": str, "funder_ref": str, "trans_sector": str, "trans_sector_group": str,
        "trans_code": str, "trans_flow_code": str, "budget_sector": str, "budget_sector_group": str,
        "trans_ref": str, "trans_currency": str, "budget_currency": str,
    }
    raw_activities = pd.read_csv(latest_raw_file("act"), dtype=text_columns)
    raw_transactions = pd.read_csv(latest_raw_file("trans"), dtype=text_columns, low_memory=False)
    raw_budgets = pd.read_csv(latest_raw_file("budget"), dtype=text_columns)
    print(f"raw rows: activities {len(raw_activities)}, transactions {len(raw_transactions)}, budgets {len(raw_budgets)}")

    print("activities")
    activities = clean_activities(raw_activities)
    activity_ids = set(activities["aid"])

    print("transactions")
    transactions = clean_transactions(raw_transactions, activity_ids)

    print("budgets")
    budgets = clean_budgets(raw_budgets, activity_ids)

    activities.to_parquet(CLEAN_DIR / "activities.parquet", index=False)
    transactions.to_parquet(CLEAN_DIR / "transactions.parquet", index=False)
    budgets.to_parquet(CLEAN_DIR / "budgets.parquet", index=False)
    save_log(CLEAN_DIR / "rule_log.csv")

    print(f"clean rows: activities {len(activities)}, transactions {len(transactions)}, budgets {len(budgets)}")


if __name__ == "__main__":
    main()
