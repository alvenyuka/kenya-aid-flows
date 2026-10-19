import pandas as pd

import clean_budgets as cb
from common import LAST_VALID_DAY

START = 18000
END = 18364


def make_rows(rows):
    defaults = {
        "aid": "A1", "budget": "budget", "budget_priority": 1, "budget_type": 1.0, "budget_day_start": START, "budget_day_end": END,
        "budget_currency": "USD", "budget_usd": 1000.0,
        "budget_sector": "11110", "budget_sector_group": "111",
    }
    full_rows = []
    for row in rows:
        full_row = dict(defaults)
        full_row.update(row)
        full_rows.append(full_row)
    return pd.DataFrame(full_rows)


def test_drop_planned_disbursements_keeps_budgets():
    frame = make_rows([{"budget": "budget"}, {"budget": "plan"}])
    result = cb.drop_planned_disbursements(frame)
    assert list(result["budget"]) == ["budget"]


def test_drop_bad_days_catches_negative_start_and_end_before_start():
    frame = make_rows([
        {},
        {"budget_day_start": -300000},
        {"budget_day_end": START - 10},
        {"budget_day_start": LAST_VALID_DAY + 500, "budget_day_end": LAST_VALID_DAY + 900},
    ])
    result = cb.drop_bad_days(frame)
    assert len(result) == 1


def test_future_end_day_is_allowed():
    frame = make_rows([{"budget_day_end": LAST_VALID_DAY + 700}])
    result = cb.drop_bad_days(frame)
    assert len(result) == 1


def test_drop_negative_budgets():
    frame = make_rows([{"budget_usd": -1.0}, {"budget_usd": 0.0}, {"budget_usd": 5.0}])
    result = cb.drop_negative_budgets(frame)
    assert len(result) == 2


def test_duplicates_keep_different_types():
    frame = make_rows([{"budget_type": 1.0}, {"budget_type": 1.0}, {"budget_type": 2.0}])
    frame = cb.name_budget_types(frame)
    result = cb.drop_duplicate_budgets(frame)
    assert len(result) == 2


def test_untyped_line_equal_to_a_typed_original_counts_once():
    frame = make_rows([{"budget_type": 1.0}, {"budget_type": None}])
    frame = cb.name_budget_types(frame)
    result = cb.drop_duplicate_budgets(frame)
    assert len(result) == 1


def test_blank_budget_type_is_original():
    frame = make_rows([{"budget_type": 1.0}, {"budget_type": 2.0}, {"budget_type": None}])
    result = cb.name_budget_types(frame)
    assert list(result["budget_type_name"]) == ["original", "revised", "original"]
    assert list(result["type_was_blank"]) == [False, False, True]


def test_orphan_budgets_dropped():
    frame = make_rows([{"aid": "A1"}, {"aid": "NOPE"}])
    result = cb.drop_orphans(frame, {"A1"})
    assert len(result) == 1


def test_budget_days_counts_both_end_days():
    frame = make_rows([{"budget_day_start": 18000, "budget_day_end": 18000}])
    result = cb.add_date_columns(frame)
    assert result["budget_days"].iloc[0] == 1
