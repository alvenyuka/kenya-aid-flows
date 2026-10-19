-- One row per activity, with a single donor name, a single sector group, and flags for
-- publishers whose budgets cannot be compared with their disbursements.

-- One sector group per activity. An activity can have money in several sectors and its
-- budget and transaction sectors do not always agree, so the rule is:
-- the group with the most disbursed money; if it never disbursed, the group with the
-- most planned money; if neither, 'Unknown'.
CREATE OR REPLACE TABLE activity_sector AS
WITH disbursed_by_group AS (
    SELECT aid, sector_group, SUM(usd) AS usd
    FROM stg_disbursements
    GROUP BY aid, sector_group
),
planned_by_group AS (
    SELECT aid, sector_group, SUM(budget_usd) AS usd
    FROM stg_budget_lines
    GROUP BY aid, sector_group
),
disbursed_ranked AS (
    SELECT aid, sector_group,
        ROW_NUMBER() OVER (PARTITION BY aid ORDER BY usd DESC, sector_group) AS rank_in_activity
    FROM disbursed_by_group
),
planned_ranked AS (
    SELECT aid, sector_group,
        ROW_NUMBER() OVER (PARTITION BY aid ORDER BY usd DESC, sector_group) AS rank_in_activity
    FROM planned_by_group
)
SELECT
    a.aid,
    COALESCE(d.sector_group, p.sector_group, 'Unknown') AS sector_group
FROM stg_activities AS a
LEFT JOIN disbursed_ranked AS d ON d.aid = a.aid AND d.rank_in_activity = 1
LEFT JOIN planned_ranked AS p ON p.aid = a.aid AND p.rank_in_activity = 1;

-- Three kinds of publisher make the plan-against-actual comparison meaningless. The
-- thresholds below were chosen AFTER looking at the data (they are not from a standard):
--   budget_mirrors_actuals: the budget is a copy of the disbursements (the Gates
--     Foundation). At least 100 such activity-years and 95% or more within 1% of plan.
--   budget_partial: the budget covers only a slice of the spending (CGIAR). At least 100
--     such activity-years and a median ratio above 3.
-- Both tests count every activity-year with a plan above zero and a disbursement row,
-- whatever its coverage class, so a publisher is judged on all its data and not only on
-- the part that the coverage rule lets through (most CGIAR years fail the coverage rule
-- already, which is why only 20 of its years reach the headline set).
--   budget_needs_based: the budget is a needs-based appeal (the UN refugee agency, UNHCR),
--     not a spending plan. At least 3 years with a comparable activity-year; in EVERY such
--     year it disbursed (code D) under 30% of its plan; at least 70% of its planned money
--     sits on lines with no stated budget type; and it reports more spending as
--     expenditure (code E) than as disbursement. These thresholds were chosen after
--     looking at UNHCR's numbers, so the rule is built to describe it.
-- A flagged reporting organisation keeps its rows in the fact table but leaves the marts.
-- The "pre2020" flags use only years before 2020, so the baseline in baseline/ does not
-- use information from the years it is scored on.
CREATE OR REPLACE TABLE dim_donor AS
WITH all_years AS (
    SELECT
        a.reporting_ref,
        COUNT(*) AS n,
        AVG(CAST(abs(f.ratio - 1) <= 0.01 AS INTEGER)) AS share_within_1pct,
        quantile_cont(f.ratio, 0.5) AS median_ratio
    FROM fact_activity_year AS f
    INNER JOIN stg_activities AS a ON a.aid = f.aid
    WHERE f.planned_usd > 0 AND f.disbursement_rows > 0
    GROUP BY a.reporting_ref
),
before_2020 AS (
    SELECT
        a.reporting_ref,
        COUNT(*) AS n,
        AVG(CAST(abs(f.ratio - 1) <= 0.01 AS INTEGER)) AS share_within_1pct,
        quantile_cont(f.ratio, 0.5) AS median_ratio
    FROM fact_activity_year AS f
    INNER JOIN stg_activities AS a ON a.aid = f.aid
    WHERE f.planned_usd > 0 AND f.disbursement_rows > 0 AND f.year < 2020
    GROUP BY a.reporting_ref
),
needs_years AS (
    SELECT
        a.reporting_ref,
        f.year,
        SUM(f.planned_usd) AS planned_usd,
        SUM(f.disbursed_usd) AS disbursed_usd,
        SUM(f.planned_untyped_usd) AS planned_untyped_usd
    FROM fact_activity_year AS f
    INNER JOIN stg_activities AS a ON a.aid = f.aid
    WHERE f.is_comparable
    GROUP BY a.reporting_ref, f.year
),
needs_all AS (
    SELECT
        reporting_ref,
        COUNT(*) AS years,
        MAX(disbursed_usd / planned_usd) AS highest_yearly_ratio,
        SUM(planned_untyped_usd) / SUM(planned_usd) AS untyped_share
    FROM needs_years
    GROUP BY reporting_ref
),
needs_before_2020 AS (
    SELECT
        reporting_ref,
        COUNT(*) AS years,
        MAX(disbursed_usd / planned_usd) AS highest_yearly_ratio,
        SUM(planned_untyped_usd) / SUM(planned_usd) AS untyped_share
    FROM needs_years
    WHERE year < 2020
    GROUP BY reporting_ref
),
spending_all AS (
    SELECT
        a.reporting_ref,
        SUM(CASE WHEN t.trans_code = 'E' THEN t.trans_usd ELSE 0 END) AS expenditure_usd,
        SUM(CASE WHEN t.trans_code = 'D' THEN t.trans_usd ELSE 0 END) AS disbursed_usd
    FROM raw_transactions AS t
    INNER JOIN stg_activities AS a ON a.aid = t.aid
    WHERE t.trans_year BETWEEN 2010 AND 2024
    GROUP BY a.reporting_ref
),
spending_before_2020 AS (
    SELECT
        a.reporting_ref,
        SUM(CASE WHEN t.trans_code = 'E' THEN t.trans_usd ELSE 0 END) AS expenditure_usd,
        SUM(CASE WHEN t.trans_code = 'D' THEN t.trans_usd ELSE 0 END) AS disbursed_usd
    FROM raw_transactions AS t
    INNER JOIN stg_activities AS a ON a.aid = t.aid
    WHERE t.trans_year BETWEEN 2010 AND 2019
    GROUP BY a.reporting_ref
)
SELECT
    a.reporting_ref,
    mode(a.reporting) AS donor_name,
    COALESCE(MAX(x.n), 0) AS activity_years_with_plan_and_disbursement,
    MAX(x.share_within_1pct) AS share_within_1pct,
    MAX(x.median_ratio) AS median_ratio,
    COALESCE(MAX(x.n) >= 100 AND MAX(x.share_within_1pct) >= 0.95, FALSE) AS budget_mirrors_actuals,
    COALESCE(MAX(x.n) >= 100 AND MAX(x.median_ratio) > 3, FALSE) AS budget_partial,
    COALESCE(MAX(na.years) >= 3 AND MAX(na.highest_yearly_ratio) < 0.30 AND MAX(na.untyped_share) >= 0.7
             AND MAX(sa.expenditure_usd) > MAX(sa.disbursed_usd), FALSE) AS budget_needs_based,
    COALESCE(MAX(y.n) >= 100 AND MAX(y.share_within_1pct) >= 0.95, FALSE) AS budget_mirrors_actuals_pre2020,
    COALESCE(MAX(y.n) >= 100 AND MAX(y.median_ratio) > 3, FALSE) AS budget_partial_pre2020,
    COALESCE(MAX(nb.years) >= 3 AND MAX(nb.highest_yearly_ratio) < 0.30 AND MAX(nb.untyped_share) >= 0.7
             AND MAX(sb.expenditure_usd) > MAX(sb.disbursed_usd), FALSE) AS budget_needs_based_pre2020
FROM stg_activities AS a
LEFT JOIN all_years AS x ON x.reporting_ref = a.reporting_ref
LEFT JOIN before_2020 AS y ON y.reporting_ref = a.reporting_ref
LEFT JOIN needs_all AS na ON na.reporting_ref = a.reporting_ref
LEFT JOIN needs_before_2020 AS nb ON nb.reporting_ref = a.reporting_ref
LEFT JOIN spending_all AS sa ON sa.reporting_ref = a.reporting_ref
LEFT JOIN spending_before_2020 AS sb ON sb.reporting_ref = a.reporting_ref
GROUP BY a.reporting_ref;

-- Which activities report disbursements (D) in any year, and which report only
-- expenditure (E). An E-only activity has no disbursement rows, which does not mean
-- nothing was spent.
CREATE OR REPLACE TABLE activity_reporting AS
SELECT
    a.aid,
    EXISTS (SELECT 1 FROM raw_transactions AS t WHERE t.aid = a.aid AND t.trans_code = 'D') AS reports_disbursements,
    EXISTS (SELECT 1 FROM raw_transactions AS t WHERE t.aid = a.aid AND t.trans_code = 'E') AS reports_expenditure
FROM stg_activities AS a;

CREATE OR REPLACE TABLE dim_activity AS
SELECT
    a.aid,
    a.title,
    a.reporting_ref,
    d.donor_name,
    (d.budget_mirrors_actuals OR d.budget_partial OR d.budget_needs_based) AS publisher_left_out,
    -- The headline set with only the mirror and partial rules, for the "UNHCR put back" sensitivity.
    (d.budget_mirrors_actuals OR d.budget_partial) AS publisher_left_out_without_needs_rule,
    d.budget_needs_based,
    (d.budget_mirrors_actuals_pre2020 OR d.budget_partial_pre2020 OR d.budget_needs_based_pre2020) AS publisher_left_out_pre2020,
    -- Used by the baseline: the Gates copy rule uses all years (a copied budget is a feature of
    -- the budget, not of the outcome); CGIAR and UNHCR use only years before 2020.
    (d.budget_mirrors_actuals OR d.budget_partial_pre2020 OR d.budget_needs_based_pre2020) AS publisher_left_out_baseline,
    r.reports_disbursements,
    r.reports_expenditure,
    s.sector_group,
    COALESCE(n.sector_group_name, s.sector_group) AS sector_group_name
FROM stg_activities AS a
INNER JOIN dim_donor AS d ON d.reporting_ref = a.reporting_ref
INNER JOIN activity_reporting AS r ON r.aid = a.aid
INNER JOIN activity_sector AS s ON s.aid = a.aid
LEFT JOIN dim_sector_group AS n ON n.sector_group = s.sector_group;
