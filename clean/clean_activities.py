"""Cleaning rules for the activities table (one row per project)."""
import pandas as pd

from common import FIRST_DAY, LAST_VALID_DAY, day_number_to_date
from rule_log import log_rule

TABLE = "activities"
KEEP_COLUMNS = [
    "aid", "reporting", "reporting_ref", "funder_ref", "title",
    "status_code", "day_start", "day_end",
]


def keep_needed_columns(activities):
    """The description and the other-currency columns are not used downstream."""
    return activities[KEEP_COLUMNS].copy()


def drop_duplicate_activities(activities):
    """An activity listed under Kenya twice comes back as two identical rows."""
    rows_in = len(activities)
    activities = activities.drop_duplicates(subset=["aid"], keep="first").copy()
    log_rule(TABLE, "drop_duplicate_activities", rows_in, len(activities))
    return activities


def blank_bad_dates(activities):
    """Impossible start or end days become empty. The activity is kept because
    its money rows still belong to it."""
    rows = len(activities)
    blanked = 0
    for column in ["day_start", "day_end"]:
        too_early = activities[column] < FIRST_DAY
        too_late = activities[column] > LAST_VALID_DAY
        blanked = blanked + int((too_early | too_late).sum())
        activities[column] = activities[column].where(~(too_early | too_late))
    log_rule(TABLE, "blank_bad_dates", rows, rows, note=f"{blanked} start/end days outside 2000-01-01..2026-12-31 set to empty (rows kept)")
    activities["date_start"] = day_number_to_date(activities["day_start"])
    activities["date_end"] = day_number_to_date(activities["day_end"])
    return activities


def fill_missing_reporting_org(activities):
    """A handful of activities have no reporting organisation. Label them UNKNOWN
    so they stay in the donor table as one group."""
    rows = len(activities)
    missing = activities["reporting_ref"].isna()
    activities["reporting_ref"] = activities["reporting_ref"].astype("string")
    activities["reporting"] = activities["reporting"].astype("string")
    activities["reporting_ref"] = activities["reporting_ref"].where(~missing, "UNKNOWN")
    activities["reporting"] = activities["reporting"].where(~missing, "Unknown reporting organisation")
    log_rule(TABLE, "fill_missing_reporting_org", rows, rows, note=f"{int(missing.sum())} rows labelled UNKNOWN (kept)")
    return activities


def clean_activities(raw):
    activities = keep_needed_columns(raw)
    activities = drop_duplicate_activities(activities)
    activities = blank_bad_dates(activities)
    activities = fill_missing_reporting_org(activities)
    return activities
