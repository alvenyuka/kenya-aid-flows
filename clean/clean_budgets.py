"""Cleaning rules for the budgets table (one row per planned amount over a period)."""
import pandas as pd

from common import FIRST_DAY, LAST_VALID_DAY, day_number_to_date, drop_and_log, label_missing_sector
from rule_log import log_rule

TABLE = "budgets"
KEEP_COLUMNS = [
    "aid", "budget", "budget_priority", "budget_type", "budget_day_start", "budget_day_end", "budget_currency",
    "budget_usd", "budget_sector", "budget_sector_group",
]

# budget_id is only a row counter, so it is left out of the duplicate test.
DUPLICATE_KEY = [
    "aid", "budget", "budget_type_name", "budget_day_start", "budget_day_end",
    "budget_currency", "budget_usd", "budget_sector",
]

# IATI budget types: 1 = original, 2 = revised. The IATI standard says: "If the @type
# attribute is omitted, then BudgetType code 1 (Original) is assumed"
# (https://iatistandard.org/en/iati-standard/203/activity-standard/iati-activities/iati-activity/budget/).
# So a line with no type is treated as original.
BUDGET_TYPE_NAMES = {1: "original", 2: "revised"}
ASSUMED_ORIGINAL = "original"


def keep_needed_columns(budgets):
    return budgets[KEEP_COLUMNS].copy()


def drop_planned_disbursements(budgets):
    """d-portal keeps two kinds of rows in its budget table: IATI budgets ("budget")
    and planned disbursements ("plan"). This project measures budgets, so the
    planned-disbursement rows are removed."""
    is_plan = budgets["budget"] != "budget"
    return drop_and_log(budgets, is_plan, TABLE, "drop_planned_disbursements", "budget_usd",
                        note="rows from IATI planned-disbursement elements, not budgets")


def drop_bad_days(budgets):
    start = budgets["budget_day_start"]
    end = budgets["budget_day_end"]
    start_bad = start.isna() | (start < FIRST_DAY) | (start > LAST_VALID_DAY)
    # Budgets can run into the future, so the end day has no upper limit of "today".
    # It only has to be a real date and not before the start.
    end_bad = end.isna() | (end < FIRST_DAY) | (end < start)
    return drop_and_log(budgets, start_bad | end_bad, TABLE, "drop_bad_days", "budget_usd",
                        note="start outside 2000-01-01..2026-12-31, or end missing, before 2000 or before start")


def drop_missing_usd(budgets):
    is_missing = budgets["budget_usd"].isna()
    return drop_and_log(budgets, is_missing, TABLE, "drop_missing_usd", note="no USD value")


def drop_duplicate_budgets(budgets):
    is_duplicate = budgets.duplicated(subset=DUPLICATE_KEY, keep="first")
    return drop_and_log(budgets, is_duplicate, TABLE, "drop_duplicate_budgets", "budget_usd",
                        note="same activity, type, period, amount and sector")


def drop_negative_budgets(budgets):
    is_negative = budgets["budget_usd"] < 0
    return drop_and_log(budgets, is_negative, TABLE, "drop_negative_budgets", "budget_usd",
                        note="a planned amount below zero")


def drop_orphans(budgets, activity_ids):
    is_orphan = ~budgets["aid"].isin(activity_ids)
    return drop_and_log(budgets, is_orphan, TABLE, "drop_orphans", "budget_usd",
                        note="aid not in the cleaned activities table")


def name_budget_types(budgets):
    """Turn 1 / 2 / empty into words. Empty means original (see above). This runs before
    the duplicate rule so an untyped line and an identical typed line count once."""
    rows = len(budgets)
    names = budgets["budget_type"].map(BUDGET_TYPE_NAMES)
    budgets["type_was_blank"] = budgets["budget_type"].isna()
    budgets["budget_type_name"] = names.fillna(ASSUMED_ORIGINAL)
    blank_usd = budgets.loc[budgets["type_was_blank"], "budget_usd"].sum()
    log_rule(TABLE, "name_budget_types", rows, rows, note=f"{int(budgets['type_was_blank'].sum())} lines without a type treated as original, USD {blank_usd / 1e6:,.0f}m (kept)")
    return budgets


def add_date_columns(budgets):
    budgets["budget_start"] = day_number_to_date(budgets["budget_day_start"])
    budgets["budget_end"] = day_number_to_date(budgets["budget_day_end"])
    budgets["budget_days"] = budgets["budget_day_end"] - budgets["budget_day_start"] + 1
    return budgets


def clean_budgets(raw, activity_ids):
    budgets = keep_needed_columns(raw)
    budgets = name_budget_types(budgets)
    budgets = drop_planned_disbursements(budgets)
    budgets = drop_bad_days(budgets)
    budgets = drop_missing_usd(budgets)
    budgets = drop_duplicate_budgets(budgets)
    budgets = drop_negative_budgets(budgets)
    budgets = drop_orphans(budgets, activity_ids)
    budgets = label_missing_sector(budgets, TABLE, "budget_sector", "budget_sector_group")
    budgets = add_date_columns(budgets)
    return budgets
