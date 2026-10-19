-- Marts: the tables the README and the results page read.
-- The headline set ("comparable activity-years"):
--   * the original annual budget lines cover the whole calendar year (coverage_class),
--   * the plan is above zero and the year has at least one disbursement row,
--   * the reporting organisation is not left out (budget copies the disbursements, covers
--     only a slice of the spending, or is a needs-based appeal; see dim_donor).
-- The "all_" columns show the money outside that set, so nothing is hidden.

CREATE OR REPLACE VIEW comparable_activity_years AS
SELECT
    f.aid,
    f.year,
    f.planned_usd,
    f.disbursed_usd,
    -- The part of the plan that arrived in its own year. Extra money above the plan does
    -- not count, so one over-spending project cannot hide another that fell short.
    LEAST(f.disbursed_usd, f.planned_usd) AS arrived_usd,
    -- Variants used in the sensitivities: disbursement plus expenditure counted as arrived,
    -- and the larger of disbursed and planned (for a measure that also penalises overshoot).
    LEAST(f.disbursed_usd + f.expenditure_usd, f.planned_usd) AS arrived_with_expenditure_usd,
    f.disbursed_usd + f.expenditure_usd AS disbursed_plus_expenditure_usd,
    GREATEST(f.disbursed_usd, f.planned_usd) AS larger_of_disbursed_and_planned_usd,
    f.ratio,
    f.gap_usd,
    f.overlapping_usd,
    f.expenditure_usd,
    d.reporting_ref,
    d.donor_name,
    d.sector_group,
    d.sector_group_name,
    -- Within 1% of plan counts as on plan: a plan split by days is never exactly equal.
    (f.ratio < 0.99) AS is_shortfall,
    (f.ratio > 1.01) AS is_overshoot,
    (f.ratio < 0.7) AS is_under_70
FROM fact_activity_year AS f
INNER JOIN dim_activity AS d ON d.aid = f.aid
WHERE f.is_comparable AND NOT d.publisher_left_out;

-- By year
CREATE OR REPLACE TABLE mart_by_year AS
SELECT
    c.year,
    COUNT(*) AS comparable_activity_years,
    SUM(c.planned_usd) AS planned_usd,
    SUM(c.disbursed_usd) AS disbursed_usd,
    SUM(c.arrived_usd) AS arrived_usd,
    SUM(c.arrived_usd) / SUM(c.planned_usd) AS arrived_share,
    SUM(c.disbursed_usd) / SUM(c.planned_usd) AS ratio,
    -- The middle activity-year; totals are pulled by a few very large projects.
    quantile_cont(c.ratio, 0.5) AS median_ratio,
    SUM(c.disbursed_usd) - SUM(c.planned_usd) AS gap_usd,
    AVG(CAST(c.is_shortfall AS INTEGER)) AS share_shortfall,
    AVG(CAST(c.is_overshoot AS INTEGER)) AS share_overshoot,
    1 - AVG(CAST(c.is_shortfall AS INTEGER)) - AVG(CAST(c.is_overshoot AS INTEGER)) AS share_on_plan,
    AVG(CAST(c.is_under_70 AS INTEGER)) AS share_under_70,
    (SELECT SUM(f.disbursed_usd) FROM fact_activity_year AS f WHERE f.year = c.year) AS all_disbursed_usd,
    (SELECT SUM(f.planned_usd) FROM fact_activity_year AS f WHERE f.year = c.year) AS all_planned_usd
FROM comparable_activity_years AS c
GROUP BY c.year
ORDER BY c.year;

-- By reporting organisation (donor). NGOs and agencies report too, hence "reporting".
CREATE OR REPLACE TABLE mart_by_donor AS
SELECT
    reporting_ref,
    donor_name,
    COUNT(DISTINCT aid) AS activities,
    COUNT(*) AS comparable_activity_years,
    SUM(planned_usd) AS planned_usd,
    SUM(disbursed_usd) AS disbursed_usd,
    SUM(arrived_usd) / SUM(planned_usd) AS arrived_share,
    SUM(disbursed_usd) / SUM(planned_usd) AS ratio,
    quantile_cont(ratio, 0.5) AS median_ratio,
    AVG(CAST(is_under_70 AS INTEGER)) AS share_under_70
FROM comparable_activity_years
GROUP BY reporting_ref, donor_name;

-- By sector group
CREATE OR REPLACE TABLE mart_by_sector AS
SELECT
    sector_group,
    sector_group_name,
    COUNT(DISTINCT aid) AS activities,
    COUNT(*) AS comparable_activity_years,
    SUM(planned_usd) AS planned_usd,
    SUM(disbursed_usd) AS disbursed_usd,
    SUM(arrived_usd) / SUM(planned_usd) AS arrived_share,
    SUM(disbursed_usd) / SUM(planned_usd) AS ratio,
    quantile_cont(ratio, 0.5) AS median_ratio,
    AVG(CAST(is_under_70 AS INTEGER)) AS share_under_70
FROM comparable_activity_years
GROUP BY sector_group, sector_group_name;

-- One row per activity
CREATE OR REPLACE TABLE mart_activity AS
SELECT
    c.aid,
    d.title,
    d.donor_name,
    d.sector_group_name,
    COUNT(*) AS comparable_years,
    SUM(c.planned_usd) AS planned_usd,
    SUM(c.disbursed_usd) AS disbursed_usd,
    SUM(c.arrived_usd) / SUM(c.planned_usd) AS arrived_share,
    SUM(c.disbursed_usd) / SUM(c.planned_usd) AS ratio,
    SUM(CAST(c.is_under_70 AS INTEGER)) AS years_under_70
FROM comparable_activity_years AS c
INNER JOIN dim_activity AS d ON d.aid = c.aid
GROUP BY c.aid, d.title, d.donor_name, d.sector_group_name;

-- Sensitivity 1: what the answer looks like if part-year and multi-year plans are used
-- as well. Same conditions as the headline except the coverage class.
CREATE OR REPLACE TABLE sensitivity_coverage AS
SELECT
    f.coverage_class,
    COUNT(*) AS activity_years,
    SUM(f.planned_usd) AS planned_usd,
    SUM(f.disbursed_usd) AS disbursed_usd,
    SUM(LEAST(f.disbursed_usd, f.planned_usd)) / SUM(f.planned_usd) AS arrived_share,
    SUM(f.disbursed_usd) / SUM(f.planned_usd) AS ratio,
    quantile_cont(f.ratio, 0.5) AS median_ratio,
    AVG(CAST(f.ratio < 0.7 AS INTEGER)) AS share_under_70
FROM fact_activity_year AS f
INNER JOIN dim_activity AS d ON d.aid = f.aid
WHERE f.planned_usd > 0 AND f.disbursement_rows > 0 AND NOT d.publisher_left_out
GROUP BY f.coverage_class;

-- Sensitivity 2 (a lower bound): add the full-year plans that have NO disbursement row in
-- the year, counted as zero disbursed, but only for activities that report disbursements
-- in some other year. For these a zero is probably a real gap; for an activity that never
-- reports a disbursement it may only be a reporting habit.
CREATE OR REPLACE TABLE sensitivity_zero_disbursed AS
SELECT
    COUNT(*) AS activity_years,
    SUM(CASE WHEN f.disbursement_rows = 0 THEN 1 ELSE 0 END) AS counted_as_zero,
    SUM(f.planned_usd) AS planned_usd,
    SUM(f.disbursed_usd) AS disbursed_usd,
    SUM(LEAST(f.disbursed_usd, f.planned_usd)) / SUM(f.planned_usd) AS arrived_share,
    SUM(f.disbursed_usd) / SUM(f.planned_usd) AS ratio,
    AVG(CAST(f.ratio < 0.7 AS INTEGER)) AS share_under_70
FROM fact_activity_year AS f
INNER JOIN dim_activity AS d ON d.aid = f.aid
WHERE f.coverage_class = 'full_annual' AND f.planned_usd > 0
  AND d.reports_disbursements AND NOT d.publisher_left_out;

-- Full-year plans with no disbursement row from activities that never report one:
-- how many of them report expenditure (E) instead.
CREATE OR REPLACE TABLE plans_without_any_disbursement AS
SELECT
    COUNT(*) AS activity_years,
    SUM(CASE WHEN d.reports_expenditure THEN 1 ELSE 0 END) AS activity_years_with_expenditure_rows,
    SUM(f.planned_usd) AS planned_usd
FROM fact_activity_year AS f
INNER JOIN dim_activity AS d ON d.aid = f.aid
WHERE f.coverage_class = 'full_annual' AND f.planned_usd > 0
  AND NOT d.reports_disbursements AND NOT d.publisher_left_out;

-- The population the baseline scores: every full-year annual plan above zero, whatever the
-- disbursement, for publishers not excluded under the baseline rules (see dim_donor).
-- had_earlier_disbursement uses only years BEFORE the row's year, so nothing from the
-- future decides who is included. The python script picks the rows it scores.
CREATE OR REPLACE VIEW baseline_activity_years AS
SELECT
    f.aid,
    f.year,
    f.planned_usd,
    f.disbursed_usd,
    f.disbursement_rows,
    f.disbursed_usd / f.planned_usd AS ratio_with_zero,
    EXISTS (
        SELECT 1 FROM disbursed_by_activity_year AS d
        WHERE d.aid = f.aid AND d.year < f.year
    ) AS had_earlier_disbursement
FROM fact_activity_year AS f
INNER JOIN dim_activity AS a ON a.aid = f.aid
WHERE f.coverage_class = 'full_annual' AND f.planned_usd > 0
  AND NOT a.publisher_left_out_baseline;

-- Sensitivity: the headline set with the needs-based publisher (UNHCR) put back.
CREATE OR REPLACE VIEW comparable_with_needs_based AS
SELECT
    f.aid,
    f.year,
    f.planned_usd,
    f.disbursed_usd,
    LEAST(f.disbursed_usd, f.planned_usd) AS arrived_usd,
    f.ratio,
    d.reporting_ref,
    d.sector_group,
    d.sector_group_name
FROM fact_activity_year AS f
INNER JOIN dim_activity AS d ON d.aid = f.aid
WHERE f.is_comparable AND NOT d.publisher_left_out_without_needs_rule;
