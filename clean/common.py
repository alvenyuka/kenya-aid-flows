"""Rules shared by the three tables."""
from datetime import date

import pandas as pd

from rule_log import log_rule

# The analysis covers 2010 to END_YEAR. It is a fixed number, not today's date, so the
# README figures do not change when the calendar year turns. sql/01_staging.sql repeats
# these two years, and tests/test_settings.py checks that the two files agree.
FIRST_YEAR = 2010
END_YEAR = 2024

# d-portal stores dates as days since 1970-01-01. A few publishers send 0 or dates
# in the 2030s and beyond. Dates from 2000 to the end of 2026 (two years after
# END_YEAR, which leaves room for budgets and late reports) are kept.
EPOCH = date(1970, 1, 1)
FIRST_DAY = (date(2000, 1, 1) - EPOCH).days
LAST_VALID_DAY = (date(END_YEAR + 2, 12, 31) - EPOCH).days

MISSING_SECTOR = "Unknown"


def day_number_to_date(day_numbers):
    """Days since 1970 -> calendar dates. Call this only after the bad days are gone."""
    return pd.to_datetime(day_numbers, unit="D", origin="1970-01-01")


def label_missing_sector(table, name, sector_column, group_column):
    """Fill empty sector codes with 'Unknown' so the money is kept, not dropped."""
    rows = len(table)
    sector_empty = table[sector_column].isna() | (table[sector_column].astype(str).str.strip() == "")
    group_empty = table[group_column].isna() | (table[group_column].astype(str).str.strip() == "")
    table[sector_column] = table[sector_column].astype("string").where(~sector_empty, MISSING_SECTOR)
    table[group_column] = table[group_column].astype("string").where(~group_empty, MISSING_SECTOR)
    log_rule(name, "label_missing_sector", rows, rows, note=f"{int(group_empty.sum())} rows relabelled Unknown (kept)")
    return table


def drop_and_log(table, drop_mask, table_name, rule, amount_column=None, note=""):
    """Remove the rows where drop_mask is True and record how many rows (and USD) went."""
    rows_in = len(table)
    usd_removed = 0.0
    if amount_column is not None:
        usd_removed = table.loc[drop_mask, amount_column].sum()
    kept = table.loc[~drop_mask].copy()
    log_rule(table_name, rule, rows_in, len(kept), usd_removed, note)
    return kept
