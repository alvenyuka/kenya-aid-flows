import pandas as pd

import clean_activities as ca
from common import LAST_VALID_DAY


def make_rows(rows):
    defaults = {
        "aid": "A1", "reporting": "Donor X", "reporting_ref": "XX-1", "funder_ref": "XX",
        "title": "t", "status_code": 2, "day_start": 18000.0, "day_end": 18400.0,
    }
    full_rows = []
    for row in rows:
        full_row = dict(defaults)
        full_row.update(row)
        full_rows.append(full_row)
    return pd.DataFrame(full_rows)


def test_drop_duplicate_activities():
    frame = make_rows([{"aid": "A1"}, {"aid": "A1"}, {"aid": "A2"}])
    result = ca.drop_duplicate_activities(frame)
    assert sorted(result["aid"]) == ["A1", "A2"]


def test_blank_bad_dates_keeps_the_row():
    frame = make_rows([{"day_start": 0.0, "day_end": LAST_VALID_DAY + 3000.0}])
    result = ca.blank_bad_dates(frame)
    assert len(result) == 1
    assert pd.isna(result["date_start"].iloc[0])
    assert pd.isna(result["date_end"].iloc[0])


def test_missing_reporting_org_is_labelled():
    frame = make_rows([{"reporting_ref": None, "reporting": None}])
    result = ca.fill_missing_reporting_org(frame)
    assert result["reporting_ref"].iloc[0] == "UNKNOWN"
