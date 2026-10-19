"""Stage 8: a logistic regression that flags activity-years likely to arrive under 70% of plan.

Same rules as the rule-of-thumb baseline (baseline/rule_of_thumb.py):
  * population: the view baseline_activity_years, only years with a disbursement row;
  * rows scored: test years (2020 to 2024) of activities with at least one earlier year;
  * the model is trained on years before 2020 only, and nothing is tuned on the test years.

Every feature uses information from EARLIER years, or the plan itself (which is known
before the year starts):
  prior_ratio              disbursed / planned over the activity's earlier years (capped at 3)
  prior_years              how many earlier years the activity has
  plan_size                log10 of the year's planned dollars
  publisher_prior_share    the publisher's share of activity-years under 70% in years BEFORE this
                           row's year (so a row never sees its own year or later). These publisher
                           features keep updating through the test years: a 2022 row uses the
                           outcomes of 2020 and 2021, strictly earlier years only, like prior_ratio.
  publisher_prior_rows     how many publisher rows came before this year (log)
  sector                   the sector group with the most planned money in the activity's budget
                           lines (a plan, not an outcome), top groups only
The coverage class is the same for every row (full-year annual plans), so it is not a feature.

Compared with the baseline on the same test rows: precision, recall, PR-AUC (area under the
precision-recall curve) and base rate. Accuracy is not reported.
"""
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "report"))
from rounding import round_numbers  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "aid_flows.duckdb"
OUTPUT_PATH = PROJECT_DIR / "outputs" / "model_results.json"

THRESHOLD = 0.7        # "under 70% of plan", same as the baseline
TEST_FIRST_YEAR = 2020
RATIO_CAP = 3.0        # a prior ratio above this is treated as 3
TOP_SECTORS = 8        # sector groups kept as their own column; the rest are "other"
DECISION_CUTOFF = 0.5  # model probability above this is a flag; fixed, not tuned


def load_population():
    """Rows the baseline scores, plus the publisher and the planned-money sector."""
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    population = connection.execute(
        """
        WITH planned_by_sector AS (
            SELECT aid, sector_group, SUM(budget_usd) AS usd,
                   ROW_NUMBER() OVER (PARTITION BY aid ORDER BY SUM(budget_usd) DESC, sector_group) AS rank_in_activity
            FROM stg_budget_lines
            GROUP BY aid, sector_group
        )
        SELECT b.aid, b.year, b.planned_usd, b.disbursed_usd, b.ratio_with_zero AS ratio,
               a.reporting_ref, COALESCE(s.sector_group, 'Unknown') AS sector_group
        FROM baseline_activity_years AS b
        INNER JOIN stg_activities AS a ON a.aid = b.aid
        LEFT JOIN planned_by_sector AS s ON s.aid = b.aid AND s.rank_in_activity = 1
        WHERE b.disbursement_rows > 0
        ORDER BY b.aid, b.year
        """
    ).df()
    connection.close()
    return population


def add_activity_history(rows):
    """prior_ratio and prior_years from the same activity's earlier rows."""
    prior_ratios = []
    prior_counts = []
    for aid, years in rows.groupby("aid", sort=False):
        planned_so_far = 0.0
        disbursed_so_far = 0.0
        count_so_far = 0
        for row in years.itertuples():
            if planned_so_far > 0:
                prior_ratios.append(min(disbursed_so_far / planned_so_far, RATIO_CAP))
            else:
                prior_ratios.append(np.nan)
            prior_counts.append(count_so_far)
            planned_so_far = planned_so_far + row.planned_usd
            disbursed_so_far = disbursed_so_far + row.disbursed_usd
            count_so_far = count_so_far + 1
    rows = rows.copy()
    rows["prior_ratio"] = prior_ratios
    rows["prior_years"] = prior_counts
    return rows


def add_publisher_history(rows):
    """For each row: the publisher's share under 70%, and its row count, from EARLIER years only.

    Rows of the same publisher in the same year are all counted at the end of that year, so
    two rows of one year never see each other.
    """
    rows = rows.copy()
    rows["under_70"] = rows["ratio"] < THRESHOLD

    per_year = rows.groupby(["reporting_ref", "year"])["under_70"].agg(["sum", "count"]).reset_index()
    prior_share = {}
    prior_rows = {}
    for reporting_ref, years in per_year.groupby("reporting_ref"):
        under_so_far = 0
        count_so_far = 0
        for row in years.sort_values("year").itertuples():
            prior_rows[(reporting_ref, row.year)] = count_so_far
            if count_so_far > 0:
                prior_share[(reporting_ref, row.year)] = under_so_far / count_so_far
            under_so_far = under_so_far + row.sum
            count_so_far = count_so_far + row.count

    shares = []
    counts = []
    for row in rows.itertuples():
        key = (row.reporting_ref, row.year)
        shares.append(prior_share.get(key, np.nan))
        counts.append(prior_rows[key])
    rows["publisher_prior_share"] = shares
    rows["publisher_prior_rows"] = counts
    return rows


def build_features(rows, top_sectors, train_share_fill):
    """Turn the history columns into the model's numeric columns."""
    features = pd.DataFrame(index=rows.index)
    features["prior_ratio"] = rows["prior_ratio"]
    features["prior_years"] = rows["prior_years"].apply(math.log1p)
    features["plan_size"] = rows["planned_usd"].apply(math.log10)
    # A publisher with no earlier rows gets the training average. (Every row here has an
    # activity history, and so a publisher history too, so no "has history" column is needed.)
    features["publisher_prior_share"] = rows["publisher_prior_share"].fillna(train_share_fill)
    features["publisher_prior_rows"] = rows["publisher_prior_rows"].apply(math.log1p)
    for sector in top_sectors:
        features["sector_" + sector] = (rows["sector_group"] == sector).astype(float)
    return features


def score_flags(actual, flagged):
    """Precision, recall for a yes/no flag against the outcome."""
    return {
        "flagged": int(flagged.sum()),
        "precision": float(precision_score(actual, flagged, zero_division=0)),
        "recall": float(recall_score(actual, flagged, zero_division=0)),
    }


def main():
    population = load_population()
    population = add_activity_history(population)
    population = add_publisher_history(population)

    has_history = population["prior_ratio"].notna()
    train = population[has_history & (population["year"] < TEST_FIRST_YEAR)]
    test = population[has_history & (population["year"] >= TEST_FIRST_YEAR)]

    top_sectors = list(train["sector_group"].value_counts().head(TOP_SECTORS).index)
    train_share_fill = float(train["publisher_prior_share"].mean())

    x_train = build_features(train, top_sectors, train_share_fill)
    x_test = build_features(test, top_sectors, train_share_fill)
    y_train = (train["ratio"] < THRESHOLD).astype(int)
    y_test = (test["ratio"] < THRESHOLD).astype(int)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = LogisticRegression(max_iter=1000)
    model.fit(x_train_scaled, y_train)
    test_probability = model.predict_proba(x_test_scaled)[:, 1]
    model_flags = test_probability > DECISION_CUTOFF

    # Baseline on the same rows: flag when the earlier-years ratio is under 70%.
    # (prior_ratio here is capped at 3, which does not change a "under 0.7" flag.)
    baseline_flags = test["prior_ratio"] < THRESHOLD
    baseline_score = -test["prior_ratio"]

    # The model flags at a fixed 0.5. To compare like with like, also show the model's
    # precision and recall when it flags the same NUMBER of rows as the baseline,
    # taking the highest probabilities. This uses the baseline's flag count, not the outcomes.
    flag_count = int(baseline_flags.sum())
    top_rows = np.argsort(-test_probability)[:flag_count]
    same_count_flags = np.zeros(len(test), dtype=bool)
    same_count_flags[top_rows] = True

    coefficients = {}
    for name, value in zip(x_train.columns, model.coef_[0]):
        coefficients[name] = float(value)

    results = {
        "rule": "logistic regression, trained on years before the test years, scored on the test years",
        "threshold": THRESHOLD,
        "test_first_year": TEST_FIRST_YEAR,
        "train_rows": int(len(train)),
        "train_base_rate_under_70": float(y_train.mean()),
        "test_rows": int(len(test)),
        "test_base_rate_under_70": float(y_test.mean()),
        "features": list(x_train.columns),
        "decision_cutoff": DECISION_CUTOFF,
        "model": {
            "pr_auc": float(average_precision_score(y_test, test_probability)),
            "at_cutoff": score_flags(y_test, model_flags),
            "same_number_of_flags_as_baseline": score_flags(y_test, same_count_flags),
        },
        "baseline": {
            "pr_auc": float(average_precision_score(y_test, baseline_score)),
            "flags": score_flags(y_test, baseline_flags),
        },
        "coefficients_standardised": coefficients,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = round_numbers(results)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
