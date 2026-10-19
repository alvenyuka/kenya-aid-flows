import pandas as pd

import rule_of_thumb as baseline
import slippage as model


def make_rows(rows):
    return pd.DataFrame(rows)


def test_activity_history_uses_only_earlier_years():
    rows = make_rows([
        {"aid": "A", "year": 2018, "planned_usd": 100.0, "disbursed_usd": 50.0},
        {"aid": "A", "year": 2019, "planned_usd": 100.0, "disbursed_usd": 150.0},
        {"aid": "A", "year": 2020, "planned_usd": 100.0, "disbursed_usd": 0.0},
    ])
    result = model.add_activity_history(rows)
    assert pd.isna(result["prior_ratio"].iloc[0])
    assert result["prior_ratio"].iloc[1] == 0.5          # 50 / 100
    assert result["prior_ratio"].iloc[2] == 1.0          # 200 / 200
    assert list(result["prior_years"]) == [0, 1, 2]


def test_prior_ratio_is_capped():
    rows = make_rows([
        {"aid": "A", "year": 2018, "planned_usd": 10.0, "disbursed_usd": 1000.0},
        {"aid": "A", "year": 2019, "planned_usd": 10.0, "disbursed_usd": 0.0},
    ])
    result = model.add_activity_history(rows)
    assert result["prior_ratio"].iloc[1] == model.RATIO_CAP


def test_model_and_baseline_agree_on_prior_ratio_flag():
    rows = make_rows([
        {"aid": "A", "year": 2018, "planned_usd": 100.0, "disbursed_usd": 10.0},
        {"aid": "A", "year": 2019, "planned_usd": 100.0, "disbursed_usd": 90.0},
    ])
    model_rows = model.add_activity_history(rows)
    baseline_rows = baseline.add_prior_ratio(rows)
    model_flag = model_rows["prior_ratio"].iloc[1] < 0.7
    baseline_flag = baseline_rows["prior_ratio"].iloc[1] < 0.7
    assert model_flag == baseline_flag


def test_publisher_history_ignores_the_rows_own_year():
    rows = make_rows([
        {"reporting_ref": "P", "year": 2018, "ratio": 0.2},
        {"reporting_ref": "P", "year": 2018, "ratio": 1.0},
        {"reporting_ref": "P", "year": 2019, "ratio": 0.5},
        {"reporting_ref": "Q", "year": 2019, "ratio": 0.9},
    ])
    result = model.add_publisher_history(rows)
    # Both 2018 rows of P see nothing; the 2019 row sees the two 2018 rows (one under 70%).
    assert pd.isna(result["publisher_prior_share"].iloc[0])
    assert pd.isna(result["publisher_prior_share"].iloc[1])
    assert result["publisher_prior_share"].iloc[2] == 0.5
    assert list(result["publisher_prior_rows"]) == [0, 0, 2, 0]
