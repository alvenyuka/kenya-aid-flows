"""Stage 6: collect the headline figures into outputs/results.json.

The README and the results page quote only numbers from this file.
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rounding import round_numbers  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "aid_flows.duckdb"
RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEAN_DIR = PROJECT_DIR / "data" / "clean"
OUTPUT_DIR = PROJECT_DIR / "outputs"

TOP_N = 10
# A donor or sector needs at least this many comparable activity-years to be ranked.
# Smaller groups swing on one or two projects (the UN refugee agency's low score
# rested on 2 rows when everything was ranked).
MIN_ACTIVITY_YEARS = 10


def table_to_records(table):
    """DataFrame -> list of plain dicts (so json can write it)."""
    return json.loads(table.to_json(orient="records"))


def one_value(connection, sql):
    return connection.execute(sql).fetchone()[0]


def first_record(connection, sql):
    return table_to_records(connection.execute(sql).df())[0]


def main():
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    fetch_log = json.loads((RAW_DIR / "fetch_log.json").read_text())
    window = first_record(connection, "SELECT * FROM year_window")
    # The date of the downloaded data, not of this run, so repeated runs write the same file.
    results = {"snapshot_date": fetch_log["fetch_date"]}

    # 1. What was downloaded
    results["fetch"] = fetch_log
    results["checks_run"] = len(list((PROJECT_DIR / "checks").glob("*.sql")))

    # 2. What each cleaning rule removed, and what was kept
    rule_log = pd.read_csv(CLEAN_DIR / "rule_log.csv", keep_default_na=False)
    results["cleaning_rules"] = table_to_records(rule_log)
    results["rows_kept"] = {
        "activities": one_value(connection, "SELECT COUNT(*) FROM raw_activities"),
        "transactions": one_value(connection, "SELECT COUNT(*) FROM raw_transactions"),
        "budgets": one_value(connection, "SELECT COUNT(*) FROM raw_budgets"),
        "disbursement_rows": one_value(connection, "SELECT COUNT(*) FROM raw_transactions WHERE trans_code = 'D'"),
        "commitment_rows": one_value(connection, "SELECT COUNT(*) FROM raw_transactions WHERE trans_code = 'C'"),
        "original_budget_lines": one_value(connection, "SELECT COUNT(*) FROM stg_budget_lines"),
    }

    # 3. Budget lines behind the planned-money rule
    results["budget_lines"] = first_record(connection,
        """
        SELECT
            COUNT(*) AS original_lines,
            SUM(budget_usd) AS original_usd,
            SUM(CASE WHEN type_was_blank THEN 1 ELSE 0 END) AS lines_without_type_treated_as_original,
            SUM(CASE WHEN type_was_blank THEN budget_usd ELSE 0 END) AS usd_without_type_treated_as_original,
            SUM(CASE WHEN is_annual THEN 1 ELSE 0 END) AS annual_lines,
            SUM(CASE WHEN NOT is_annual THEN 1 ELSE 0 END) AS multi_year_lines
        FROM stg_budget_lines
        """)

    # 4. How much of the fact table can be compared
    results["year_window"] = first_record(connection, "SELECT * FROM year_window")
    results["activity_years_by_coverage"] = table_to_records(connection.execute(
        "SELECT coverage_class, COUNT(*) AS activity_years FROM fact_activity_year GROUP BY coverage_class ORDER BY coverage_class").df())
    results["activity_years"] = first_record(connection,
        """
        SELECT
            (SELECT COUNT(*) FROM fact_activity_year) AS all_activity_years,
            (SELECT COUNT(*) FROM fact_activity_year WHERE is_comparable) AS comparable_before_publisher_rule,
            (SELECT COUNT(*) FROM comparable_activity_years) AS comparable,
            (SELECT COUNT(*) FROM fact_activity_year WHERE coverage_class = 'no_plan') AS no_plan,
            (SELECT COUNT(*) FROM fact_activity_year WHERE coverage_class = 'full_annual' AND planned_usd > 0 AND disbursement_rows = 0) AS full_year_plan_but_no_disbursement
        """)

    # 5. The headline: planned against actual on full-year annual budgets
    results["headline"] = first_record(connection,
        """
        SELECT
            COUNT(*) AS activity_years,
            COUNT(DISTINCT aid) AS activities,
            SUM(planned_usd) AS planned_usd,
            SUM(disbursed_usd) AS disbursed_usd,
            SUM(arrived_usd) AS arrived_usd,
            SUM(arrived_usd) / SUM(planned_usd) AS arrived_share,
            -- Variant that also penalises overshoot: money that arrived divided by the larger of
            -- disbursed and planned, per activity-year, added up.
            SUM(arrived_usd) / SUM(larger_of_disbursed_and_planned_usd) AS arrived_share_overshoot_penalised,
            SUM(disbursed_usd) / SUM(planned_usd) AS ratio,
            quantile_cont(ratio, 0.5) AS median_ratio,
            AVG(CAST(is_shortfall AS INTEGER)) AS share_shortfall,
            AVG(CAST(is_overshoot AS INTEGER)) AS share_overshoot,
            1 - AVG(CAST(is_shortfall AS INTEGER)) - AVG(CAST(is_overshoot AS INTEGER)) AS share_on_plan,
            AVG(CAST(is_under_70 AS INTEGER)) AS share_under_70
        FROM comparable_activity_years
        """)
    results["by_year"] = table_to_records(connection.execute("SELECT * FROM mart_by_year ORDER BY year").df())

    # 6. Sensitivities
    # 6a. The needs-based publisher (UNHCR) put back in.
    results["sensitivity_needs_based_publisher_included"] = first_record(connection,
        """
        SELECT
            COUNT(*) AS activity_years,
            SUM(planned_usd) AS planned_usd,
            SUM(disbursed_usd) AS disbursed_usd,
            SUM(arrived_usd) / SUM(planned_usd) AS arrived_share,
            SUM(disbursed_usd) / SUM(planned_usd) AS ratio,
            quantile_cont(ratio, 0.5) AS median_ratio,
            AVG(CAST(ratio < 0.7 AS INTEGER)) AS share_under_70
        FROM comparable_with_needs_based
        """)
    results["needs_based_publisher_rows"] = table_to_records(connection.execute(
        """
        SELECT c.reporting_ref, d.donor_name, COUNT(*) AS activity_years, COUNT(DISTINCT c.aid) AS activities,
               SUM(c.planned_usd) AS planned_usd, SUM(c.disbursed_usd) AS disbursed_usd,
               SUM(c.arrived_usd) / SUM(c.planned_usd) AS arrived_share
        FROM comparable_with_needs_based AS c
        INNER JOIN dim_donor AS d ON d.reporting_ref = c.reporting_ref
        WHERE d.budget_needs_based
        GROUP BY c.reporting_ref, d.donor_name
        """).df())
    results["by_year_with_needs_based_publisher"] = table_to_records(connection.execute(
        """
        SELECT year, COUNT(*) AS activity_years, SUM(planned_usd) AS planned_usd, SUM(disbursed_usd) AS disbursed_usd,
               SUM(arrived_usd) / SUM(planned_usd) AS arrived_share
        FROM comparable_with_needs_based GROUP BY year ORDER BY year
        """).df())
    results["emergency_response_sector"] = first_record(connection,
        """
        SELECT
            (SELECT SUM(arrived_usd) / SUM(planned_usd) FROM comparable_activity_years WHERE sector_group = '720') AS arrived_share_without_needs_based,
            (SELECT SUM(arrived_usd) / SUM(planned_usd) FROM comparable_with_needs_based WHERE sector_group = '720') AS arrived_share_with_needs_based,
            (SELECT COUNT(*) FROM comparable_activity_years WHERE sector_group = '720') AS activity_years_without_needs_based
        """)

    # 6b. Disbursement plus expenditure counted as arrived (an upper bound: a publisher that
    # reports the same money as both D and E is counted twice).
    results["sensitivity_expenditure_counted"] = first_record(connection,
        """
        SELECT
            COUNT(*) AS activity_years,
            SUM(arrived_with_expenditure_usd) / SUM(planned_usd) AS arrived_share,
            SUM(disbursed_plus_expenditure_usd) / SUM(planned_usd) AS ratio
        FROM comparable_activity_years
        """)

    # 6c. Only budget lines with a stated type (no lines whose type is assumed), with
    # coverage and the plan recomputed from those lines alone.
    results["sensitivity_typed_lines_only"] = first_record(connection,
        """
        SELECT
            COUNT(*) AS activity_years,
            SUM(f.planned_typed_usd) AS planned_usd,
            SUM(f.disbursed_usd) AS disbursed_usd,
            SUM(LEAST(f.disbursed_usd, f.planned_typed_usd)) / SUM(f.planned_typed_usd) AS arrived_share,
            SUM(f.disbursed_usd) / SUM(f.planned_typed_usd) AS ratio,
            quantile_cont(f.disbursed_usd / f.planned_typed_usd, 0.5) AS median_ratio,
            AVG(CAST(f.disbursed_usd / f.planned_typed_usd < 0.7 AS INTEGER)) AS share_under_70
        FROM fact_activity_year AS f
        INNER JOIN dim_activity AS d ON d.aid = f.aid
        WHERE f.typed_full_coverage AND f.planned_typed_usd > 0 AND f.disbursement_rows > 0
          AND NOT d.publisher_left_out
        """)

    # 6d. Coverage and zero-fill sensitivities
    results["sensitivity_coverage"] = table_to_records(connection.execute(
        "SELECT * FROM sensitivity_coverage ORDER BY coverage_class").df())
    results["sensitivity_zero_disbursed_lower_bound"] = first_record(connection, "SELECT * FROM sensitivity_zero_disbursed")
    results["plans_from_activities_with_no_disbursement_rows"] = first_record(connection, "SELECT * FROM plans_without_any_disbursement")

    # 7. Publishers left out of the marts, and what that removes from the headline set
    results["publishers_left_out"] = table_to_records(connection.execute(
        """
        SELECT
            d.reporting_ref,
            d.donor_name,
            d.activity_years_with_plan_and_disbursement,
            d.share_within_1pct,
            d.median_ratio,
            d.budget_mirrors_actuals,
            d.budget_partial,
            d.budget_needs_based,
            d.budget_mirrors_actuals_pre2020,
            d.budget_partial_pre2020,
            (SELECT COUNT(*) FROM fact_activity_year AS f
                INNER JOIN dim_activity AS a ON a.aid = f.aid
                WHERE a.reporting_ref = d.reporting_ref AND f.is_comparable) AS headline_rows_removed
        FROM dim_donor AS d
        WHERE d.budget_mirrors_actuals OR d.budget_partial OR d.budget_needs_based
        ORDER BY d.reporting_ref
        """).df())
    results["publisher_rule_thresholds"] = {
        "min_activity_years": 100,
        "mirror_share_within_1pct": 0.95,
        "partial_median_ratio_above": 3,
        "needs_based_min_years": 3,
        "needs_based_every_year_ratio_below": 0.30,
        "needs_based_min_untyped_plan_share": 0.7,
        "needs_based_rule": "expenditure (E) exceeds disbursement (D)",
        "note": "chosen after looking at the data (the needs-based ones after looking at UNHCR), not taken from a standard",
    }

    # 8. Who and what arrives least of its plan (only groups with enough activity-years)
    results["ranking_rule"] = {
        "min_comparable_activity_years": MIN_ACTIVITY_YEARS,
        "ranked_by": "arrived_share, lowest first (disbursed capped at plan, per activity-year)",
    }
    results["lowest_arrived_share_donors"] = table_to_records(connection.execute(
        f"""
        SELECT reporting_ref, donor_name, comparable_activity_years, planned_usd, disbursed_usd,
               arrived_share, ratio, median_ratio, share_under_70
        FROM mart_by_donor WHERE comparable_activity_years >= {MIN_ACTIVITY_YEARS}
        ORDER BY arrived_share ASC LIMIT {TOP_N}
        """).df())
    results["lowest_arrived_share_sectors"] = table_to_records(connection.execute(
        f"""
        SELECT sector_group, sector_group_name, comparable_activity_years, planned_usd, disbursed_usd,
               arrived_share, ratio, median_ratio, share_under_70
        FROM mart_by_sector WHERE comparable_activity_years >= {MIN_ACTIVITY_YEARS}
        ORDER BY arrived_share ASC LIMIT {TOP_N}
        """).df())
    results["donors_ranked"] = one_value(connection, f"SELECT COUNT(*) FROM mart_by_donor WHERE comparable_activity_years >= {MIN_ACTIVITY_YEARS}")
    results["sectors_ranked"] = one_value(connection, f"SELECT COUNT(*) FROM mart_by_sector WHERE comparable_activity_years >= {MIN_ACTIVITY_YEARS}")

    # 9. Overlapping original budget lines, measured inside the planned money of the headline set
    results["overlapping_budget_money_in_headline_set"] = first_record(connection,
        """
        SELECT
            SUM(overlapping_usd) AS overlapping_usd,
            SUM(planned_usd) AS planned_usd,
            SUM(overlapping_usd) / SUM(planned_usd) AS share_of_planned
        FROM comparable_activity_years
        """)

    # 10. Sanity: largest single disbursements, and totals per year
    results["largest_disbursement_rows"] = table_to_records(connection.execute(
        "SELECT aid, trans_year, trans_usd FROM raw_transactions WHERE trans_code = 'D' ORDER BY trans_usd DESC LIMIT 5").df())
    results["all_disbursed_by_year"] = table_to_records(connection.execute(
        "SELECT trans_year AS year, SUM(trans_usd) AS disbursed_usd FROM raw_transactions WHERE trans_code = 'D' GROUP BY trans_year ORDER BY trans_year").df())
    # Planned money per year before the year window is applied, to show the late-reporting
    # pattern in the year after the window that ends the window.
    last_year = window["last_year"]
    next_year = last_year + 1
    results["original_budget_by_year"] = table_to_records(connection.execute(
        f"SELECT year, SUM(planned_all_lines_usd) AS planned_usd FROM planned_by_activity_year WHERE year BETWEEN {window['first_year']} AND {last_year + 2} GROUP BY year ORDER BY year").df())
    results["next_year_against_last_year"] = first_record(connection,
        f"""
        SELECT
            {last_year} AS last_year,
            {next_year} AS next_year,
            SUM(CASE WHEN trans_year = {last_year} THEN trans_usd END) AS usd_last_year,
            SUM(CASE WHEN trans_year = {next_year} THEN trans_usd END) AS usd_next_year,
            1 - SUM(CASE WHEN trans_year = {next_year} THEN trans_usd END) / SUM(CASE WHEN trans_year = {last_year} THEN trans_usd END) AS fall_share
        FROM raw_transactions WHERE trans_code = 'D'
        """)

    connection.close()

    # 11. The rule-of-thumb baseline
    results["baseline"] = json.loads((OUTPUT_DIR / "baseline_results.json").read_text())
    results["model"] = json.loads((OUTPUT_DIR / "model_results.json").read_text())
    results["first_look_naive_table"] = json.loads((OUTPUT_DIR / "first_look.json").read_text())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "results.json").write_text(json.dumps(round_numbers(results), indent=2))
    print(f"wrote {OUTPUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
