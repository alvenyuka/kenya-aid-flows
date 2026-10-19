"""Stage 7: a rule-of-thumb baseline for a later model.

Rule: flag an activity-year when the same activity, in the years BEFORE it, disbursed
less than 70% of what it planned (all earlier years in the population added together).
The flag is then checked against what happened in that year (actual ratio under 70%).
Only years from TEST_FIRST_YEAR on are scored, so the rule is judged on later years.

Population (the view baseline_activity_years): full-year annual plans above zero, for
publishers not excluded under the baseline rules. The Gates copy rule uses all years
(a copied budget is a property of the budget); the CGIAR and UNHCR rules use only years
before 2020. Sector is not used.

Two versions are scored:
  headline  only activity-years with at least one disbursement row. Earlier years come
            from the same population.
  zero_fill also activity-years with no disbursement row, counted as zero disbursed, when
            the activity had a disbursement in an EARLIER year. Nothing about later years
            decides who is in, so years after an activity's last disbursement are scored
            as zeros. Part of what this version finds is activities that stop reporting.

Accuracy is not reported, because a rule that flags nothing (or everything) can score
well on it. Precision and recall are compared with the flag-everything line instead.
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "report"))
from rounding import round_numbers  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "aid_flows.duckdb"
OUTPUT_PATH = PROJECT_DIR / "outputs" / "baseline_results.json"

THRESHOLD = 0.7
TEST_FIRST_YEAR = 2020


def load_population():
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    population = connection.execute(
        """
        SELECT aid, year, planned_usd, disbursed_usd, disbursement_rows,
               ratio_with_zero AS ratio, had_earlier_disbursement
        FROM baseline_activity_years
        ORDER BY aid, year
        """
    ).df()
    connection.close()
    return population


def add_prior_ratio(rows):
    """For each activity-year, the disbursed/planned ratio of that activity's earlier years."""
    prior_ratios = []
    for aid, years in rows.groupby("aid", sort=False):
        planned_so_far = 0.0
        disbursed_so_far = 0.0
        for row in years.itertuples():
            if planned_so_far > 0:
                prior_ratios.append(disbursed_so_far / planned_so_far)
            else:
                prior_ratios.append(None)
            planned_so_far = planned_so_far + row.planned_usd
            disbursed_so_far = disbursed_so_far + row.disbursed_usd
    rows = rows.copy()
    rows["prior_ratio"] = prior_ratios
    return rows


def score_rule(scored):
    """Precision, recall and base rate for the flag against the actual outcome."""
    actual = scored["ratio"] < THRESHOLD
    flagged = scored["prior_ratio"] < THRESHOLD

    true_positive = int((flagged & actual).sum())
    false_positive = int((flagged & ~actual).sum())
    false_negative = int((~flagged & actual).sum())
    true_positive_without_disbursement = int((flagged & actual & (scored["disbursement_rows"] == 0)).sum())

    precision = None
    if true_positive + false_positive > 0:
        precision = true_positive / (true_positive + false_positive)
    recall = None
    if true_positive + false_negative > 0:
        recall = true_positive / (true_positive + false_negative)
    base_rate = float(actual.mean())

    return {
        "activity_years_scored": int(len(scored)),
        "base_rate_under_70": base_rate,
        "flagged": int(flagged.sum()),
        "share_flagged": float(flagged.mean()),
        "true_positives": true_positive,
        "true_positives_in_years_without_disbursement": true_positive_without_disbursement,
        "precision": precision,
        "recall": recall,
        # Flagging everything has recall 1 and precision equal to the base rate.
        "flag_everything_precision": base_rate,
        "lift_over_flag_everything": None if precision is None or base_rate == 0 else precision / base_rate,
    }


def run_version(population, keep_rows):
    rows = population[keep_rows].copy()
    rows = add_prior_ratio(rows)
    has_history = rows["prior_ratio"].notna()
    in_test_years = rows["year"] >= TEST_FIRST_YEAR
    scored = rows[has_history & in_test_years]

    result = {
        "activity_years_in_population": int(len(rows)),
        "activity_years_in_test_years": int(in_test_years.sum()),
        "dropped_no_earlier_year": int((in_test_years & ~has_history).sum()),
    }
    result.update(score_rule(scored))
    return result


def main():
    population = load_population()

    has_disbursement = population["disbursement_rows"] > 0
    results = {
        "rule": f"flag when earlier years of the same activity disbursed under {THRESHOLD:.0%} of plan",
        "threshold": THRESHOLD,
        "test_first_year": TEST_FIRST_YEAR,
        "headline": run_version(population, has_disbursement),
        "zero_fill": run_version(population, has_disbursement | population["had_earlier_disbursement"]),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = round_numbers(results)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
