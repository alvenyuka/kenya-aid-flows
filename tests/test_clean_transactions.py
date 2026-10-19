import pandas as pd

import clean_transactions as ct
from common import FIRST_DAY, LAST_VALID_DAY

GOOD_DAY = 18000  # 2019-04-14


def make_rows(rows):
    """Build a small transactions frame; anything not given gets a harmless default."""
    defaults = {
        "aid": "A1", "trans_ref": None, "trans_day": GOOD_DAY, "trans_currency": "USD",
        "trans_value": 100.0, "trans_usd": 100.0, "trans_code": "D", "trans_flow_code": "10",
        "trans_sector": "11110", "trans_sector_group": "111",
    }
    full_rows = []
    for row in rows:
        full_row = dict(defaults)
        full_row.update(row)
        full_rows.append(full_row)
    return pd.DataFrame(full_rows)


def test_drop_incoming_funds_removes_if_and_11_only():
    frame = make_rows([{"trans_code": "D"}, {"trans_code": "IF"}, {"trans_code": "11"}, {"trans_code": "C"}])
    result = ct.drop_incoming_funds(frame)
    assert sorted(result["trans_code"]) == ["C", "D"]


def test_drop_non_oda_flows_keeps_10_and_blank():
    frame = make_rows([
        {"trans_flow_code": "10"},
        {"trans_flow_code": None},
        {"trans_flow_code": "35", "aid": "XM-DAC-903-X"},
        {"trans_flow_code": "20"},
    ])
    result = ct.drop_non_oda_flows(frame)
    assert len(result) == 2


def test_drop_bad_days_removes_zero_future_and_missing():
    frame = make_rows([
        {"trans_day": GOOD_DAY},
        {"trans_day": 0},
        {"trans_day": LAST_VALID_DAY + 400},
        {"trans_day": FIRST_DAY - 1},
        {"trans_day": None},
    ])
    result = ct.drop_bad_days(frame)
    assert len(result) == 1
    assert result["trans_day"].iloc[0] == GOOD_DAY


def test_drop_missing_usd():
    frame = make_rows([{"trans_usd": 50.0}, {"trans_usd": None}])
    result = ct.drop_missing_usd(frame)
    assert len(result) == 1


def test_drop_duplicates_ignores_row_counter_but_keeps_different_sectors():
    frame = make_rows([
        {"trans_sector": "11110"},
        {"trans_sector": "11110"},   # exact repeat
        {"trans_sector": "12220"},   # same money, other sector: a real row
    ])
    result = ct.drop_duplicate_transactions(frame)
    assert len(result) == 2


def test_drop_negative_money_only_touches_c_and_d():
    frame = make_rows([
        {"trans_code": "D", "trans_usd": -5.0},
        {"trans_code": "C", "trans_usd": -5.0},
        {"trans_code": "E", "trans_usd": -5.0},
        {"trans_code": "D", "trans_usd": 5.0},
    ])
    result = ct.drop_negative_money(frame)
    assert len(result) == 2
    assert sorted(result["trans_code"]) == ["D", "E"]


def test_drop_orphans_keeps_only_known_activities():
    frame = make_rows([{"aid": "A1"}, {"aid": "ZZZ"}])
    result = ct.drop_orphans(frame, {"A1", "A2"})
    assert list(result["aid"]) == ["A1"]


def test_missing_sector_is_labelled_not_dropped():
    frame = make_rows([
        {"trans_sector": None, "trans_sector_group": None},
        {"trans_sector": "", "trans_sector_group": " "},
    ])
    result = ct.label_missing_sector(frame, "transactions", "trans_sector", "trans_sector_group")
    assert len(result) == 2
    assert set(result["trans_sector_group"]) == {"Unknown"}


def test_clean_transactions_end_to_end_adds_year():
    frame = make_rows([{"trans_day": GOOD_DAY}, {"trans_code": "IF"}])
    result = ct.clean_transactions(frame, {"A1"})
    assert len(result) == 1
    assert result["trans_year"].iloc[0] == 2019
