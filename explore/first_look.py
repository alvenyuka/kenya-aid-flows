"""A first look at the raw data, and the simplest possible planned-vs-actual table.

No cleaning rules here. This is the starting point the cleaning and SQL stages improve on.
Prints a few facts about the raw files and writes outputs/first_look.json.
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_PATH = PROJECT_DIR / "outputs" / "first_look.json"

FIRST_YEAR = 2010
LAST_YEAR = 2024


def latest_raw_file(table_name):
    files = sorted(RAW_DIR.glob(f"{table_name}_*.csv"))
    return files[-1]


def year_from_day(day_numbers):
    """Days since 1970 -> calendar year, using the average year length (good enough here)."""
    return (1970 + day_numbers / 365.25).astype("float").round(0)


def main():
    activities = pd.read_csv(latest_raw_file("act"), low_memory=False)
    transactions = pd.read_csv(latest_raw_file("trans"), low_memory=False, dtype={"trans_code": str, "trans_flow_code": str})
    budgets = pd.read_csv(latest_raw_file("budget"), low_memory=False)

    print("rows:", len(activities), len(transactions), len(budgets))
    print("\ntransaction codes:")
    print(transactions["trans_code"].value_counts(dropna=False))
    print("\ndisbursement flow types:")
    print(transactions.loc[transactions["trans_code"] == "D", "trans_flow_code"].value_counts(dropna=False))
    print("\nbudget types (blank is common):")
    print(budgets["budget_type"].value_counts(dropna=False))
    print("\nmissing sector on transactions:", int(transactions["trans_sector"].isna().sum()))
    print("trans_day outside 2000..2026:", int(((transactions["trans_day"] < 10957) | (transactions["trans_day"] > 20819)).sum()))

    # The simplest table: original budgets (type 1) by the year the budget STARTS,
    # against disbursements (code D) by the year they happened. No other rule.
    original = budgets[budgets["budget_type"] == 1].copy()
    original["year"] = year_from_day(original["budget_day_start"])
    planned = original.groupby("year")["budget_usd"].sum()

    disbursed_rows = transactions[transactions["trans_code"] == "D"].copy()
    disbursed_rows["year"] = year_from_day(disbursed_rows["trans_day"])
    disbursed = disbursed_rows.groupby("year")["trans_usd"].sum()

    table = pd.DataFrame({"planned_usd": planned, "disbursed_usd": disbursed}).dropna()
    table = table[(table.index >= FIRST_YEAR) & (table.index <= LAST_YEAR)]
    table["ratio"] = table["disbursed_usd"] / table["planned_usd"]
    print("\nfirst planned vs disbursed table (no cleaning):")
    print(table.round(2))

    summary = {
        "years": f"{FIRST_YEAR} to {LAST_YEAR}",
        "planned_usd": float(table["planned_usd"].sum()),
        "disbursed_usd": float(table["disbursed_usd"].sum()),
        "ratio": float(table["disbursed_usd"].sum() / table["planned_usd"].sum()),
        "lowest_yearly_ratio": float(table["ratio"].min()),
        "highest_yearly_ratio": float(table["ratio"].max()),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
