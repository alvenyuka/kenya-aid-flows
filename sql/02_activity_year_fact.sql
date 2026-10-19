-- The activity-year fact: one row per activity per calendar year, with what was
-- planned, what was committed and what was disbursed.

-- Step 1. Cut every original budget line into calendar-year pieces.
-- A line can cross calendar years (a July-June fiscal year, or a 3-year budget). Rule:
-- split the amount across the years in proportion to the days of the line in each year.
-- Every line is cut into pieces for the years 2000 to 2100, so no line is lost
-- (checks/06 tests that the pieces add back up to the budget lines).
CREATE OR REPLACE TABLE budget_pieces AS
WITH years AS (
    SELECT unnest(generate_series(2000, 2100)) AS year
)
SELECT
    b.line_id,
    b.aid,
    b.sector,
    b.is_annual,
    b.type_was_blank,
    b.budget_start,
    b.budget_end,
    b.budget_days,
    y.year,
    date_diff(
        'day',
        greatest(b.budget_start, make_date(y.year, 1, 1)),
        least(b.budget_end, make_date(y.year, 12, 31))
    ) + 1 AS days_in_year,
    b.budget_usd * (
        date_diff(
            'day',
            greatest(b.budget_start, make_date(y.year, 1, 1)),
            least(b.budget_end, make_date(y.year, 12, 31))
        ) + 1
    ) / b.budget_days AS usd_in_year
FROM stg_budget_lines AS b
INNER JOIN years AS y
    ON y.year BETWEEN EXTRACT(year FROM b.budget_start) AND EXTRACT(year FROM b.budget_end);

-- Step 2. Mark pieces whose line overlaps another line of the same activity and sector
-- in the same year: that money may be counted twice. Measured in results, not removed.
CREATE OR REPLACE TABLE budget_pieces_flagged AS
SELECT
    p.*,
    EXISTS (
        SELECT 1
        FROM budget_pieces AS q
        WHERE q.aid = p.aid
          AND q.sector = p.sector
          AND q.year = p.year
          AND q.line_id <> p.line_id
          AND q.budget_start <= p.budget_end
          AND p.budget_start <= q.budget_end
    ) AS overlaps_another_line
FROM budget_pieces AS p;

-- Step 3. Days of each calendar year covered by ANNUAL lines. Each distinct annual period
-- of an activity is turned into one row per day, so lines for several sectors, or lines
-- that overlap, do not count a day twice.
CREATE OR REPLACE TABLE annual_coverage AS
WITH annual_periods AS (
    SELECT DISTINCT aid, budget_start, budget_end
    FROM stg_budget_lines
    WHERE is_annual
),
covered_days AS (
    SELECT DISTINCT
        aid,
        CAST(unnest(generate_series(budget_start, budget_end, INTERVAL 1 DAY)) AS DATE) AS day
    FROM annual_periods
)
SELECT
    aid,
    CAST(EXTRACT(year FROM day) AS INTEGER) AS year,
    COUNT(*) AS covered_days
FROM covered_days
GROUP BY aid, CAST(EXTRACT(year FROM day) AS INTEGER);

-- Same coverage count, using only lines that carry an explicit budget type. Used by the
-- "typed lines only" sensitivity, which drops the lines whose type is assumed.
CREATE OR REPLACE TABLE annual_coverage_typed AS
WITH annual_periods AS (
    SELECT DISTINCT aid, budget_start, budget_end
    FROM stg_budget_lines
    WHERE is_annual AND NOT type_was_blank
),
covered_days AS (
    SELECT DISTINCT
        aid,
        CAST(unnest(generate_series(budget_start, budget_end, INTERVAL 1 DAY)) AS DATE) AS day
    FROM annual_periods
)
SELECT
    aid,
    CAST(EXTRACT(year FROM day) AS INTEGER) AS year,
    COUNT(*) AS covered_days
FROM covered_days
GROUP BY aid, CAST(EXTRACT(year FROM day) AS INTEGER);

-- Step 4. Planned money per activity-year, and how well the lines cover the year.
CREATE OR REPLACE TABLE planned_by_activity_year AS
SELECT
    p.aid,
    p.year,
    SUM(p.usd_in_year) AS planned_all_lines_usd,
    SUM(CASE WHEN p.is_annual THEN p.usd_in_year ELSE 0 END) AS planned_annual_lines_usd,
    SUM(CASE WHEN p.is_annual AND p.type_was_blank THEN p.usd_in_year ELSE 0 END) AS planned_annual_untyped_usd,
    SUM(CASE WHEN p.is_annual AND NOT p.type_was_blank THEN p.usd_in_year ELSE 0 END) AS planned_annual_typed_usd,
    SUM(CASE WHEN p.overlaps_another_line THEN p.usd_in_year ELSE 0 END) AS overlapping_usd,
    MAX(p.budget_days) AS max_line_days,
    COALESCE(MAX(c.covered_days), 0) AS annual_covered_days,
    COALESCE(MAX(ct.covered_days), 0) AS typed_covered_days,
    date_diff('day', make_date(p.year, 1, 1), make_date(p.year + 1, 1, 1)) AS days_in_calendar_year
FROM budget_pieces_flagged AS p
LEFT JOIN annual_coverage AS c ON c.aid = p.aid AND c.year = p.year
LEFT JOIN annual_coverage_typed AS ct ON ct.aid = p.aid AND ct.year = p.year
GROUP BY p.aid, p.year;

CREATE OR REPLACE TABLE disbursed_by_activity_year AS
SELECT
    aid,
    year,
    SUM(usd) AS disbursed_usd,
    COUNT(*) AS disbursement_rows
FROM stg_disbursements
GROUP BY aid, year;

CREATE OR REPLACE TABLE expenditure_by_activity_year AS
SELECT
    aid,
    year,
    SUM(usd) AS expenditure_usd
FROM stg_expenditures
GROUP BY aid, year;

CREATE OR REPLACE TABLE committed_by_activity_year AS
SELECT
    aid,
    year,
    SUM(usd) AS committed_usd
FROM stg_commitments
GROUP BY aid, year;

-- Step 5. Full outer join: many activities have a plan but no disbursement, or the reverse.
-- Only years inside year_window are kept.
--
-- coverage_class says how far the plan can be trusted as "the plan for this year":
--   full_annual       annual budget lines cover every day of the year. Used for the headline.
--   part_year         annual lines cover only part of the year (a plan for 3 months, say).
--   multi_year_split  only multi-year lines touch the year, so the year's plan is a
--                     share of a longer budget (assumes the money is spread evenly).
--   no_plan           no original budget line touches the year.
-- planned_usd comes from annual lines only when coverage is full (a long line over the
-- same year would double the plan); otherwise from all lines.
CREATE OR REPLACE TABLE fact_base AS
WITH keys AS (
    SELECT aid, year FROM planned_by_activity_year
    UNION
    SELECT aid, year FROM disbursed_by_activity_year
    UNION
    SELECT aid, year FROM committed_by_activity_year
    UNION
    SELECT aid, year FROM expenditure_by_activity_year
),
joined AS (
    SELECT
        k.aid,
        k.year,
        p.annual_covered_days,
        p.typed_covered_days,
        p.planned_annual_untyped_usd,
        p.planned_annual_typed_usd,
        p.days_in_calendar_year,
        p.max_line_days,
        p.overlapping_usd,
        p.planned_all_lines_usd,
        p.planned_annual_lines_usd,
        COALESCE(d.disbursed_usd, 0) AS disbursed_usd,
        COALESCE(d.disbursement_rows, 0) AS disbursement_rows,
        COALESCE(c.committed_usd, 0) AS committed_usd,
        COALESCE(e.expenditure_usd, 0) AS expenditure_usd
    FROM keys AS k
    LEFT JOIN planned_by_activity_year AS p ON p.aid = k.aid AND p.year = k.year
    LEFT JOIN disbursed_by_activity_year AS d ON d.aid = k.aid AND d.year = k.year
    LEFT JOIN committed_by_activity_year AS c ON c.aid = k.aid AND c.year = k.year
    LEFT JOIN expenditure_by_activity_year AS e ON e.aid = k.aid AND e.year = k.year
    WHERE k.year BETWEEN (SELECT first_year FROM year_window) AND (SELECT last_year FROM year_window)
),
classified AS (
    SELECT
        *,
        CASE
            WHEN planned_all_lines_usd IS NULL THEN 'no_plan'
            WHEN annual_covered_days >= days_in_calendar_year THEN 'full_annual'
            WHEN annual_covered_days > 0 THEN 'part_year'
            ELSE 'multi_year_split'
        END AS coverage_class
    FROM joined
)
SELECT
    aid,
    year,
    coverage_class,
    annual_covered_days,
    days_in_calendar_year,
    max_line_days,
    -- Annual lines with no stated type (assumed original), and annual lines with a stated type.
    planned_annual_untyped_usd AS planned_untyped_usd,
    planned_annual_typed_usd AS planned_typed_usd,
    typed_covered_days >= days_in_calendar_year AS typed_full_coverage,
    CASE
        WHEN coverage_class = 'full_annual' THEN planned_annual_lines_usd
        ELSE planned_all_lines_usd
    END AS planned_usd,
    CASE
        WHEN coverage_class = 'full_annual' THEN LEAST(overlapping_usd, planned_annual_lines_usd)
        ELSE overlapping_usd
    END AS overlapping_usd,
    disbursed_usd,
    disbursement_rows,
    committed_usd,
    expenditure_usd
FROM classified;

-- Ratio, gap and the comparable flag are added in a second step so each column is
-- written once.
CREATE OR REPLACE TABLE fact_activity_year AS
SELECT
    *,
    -- Ratio only exists when there is a plan above zero.
    CASE WHEN planned_usd > 0 THEN disbursed_usd / planned_usd END AS ratio,
    -- Negative gap = shortfall, positive = overshoot.
    CASE WHEN planned_usd IS NOT NULL THEN disbursed_usd - planned_usd END AS gap_usd,
    -- The headline set: a full-year annual plan above zero and at least one disbursement
    -- row in the year. A missing disbursement often means the publisher reports
    -- expenditure instead, or nothing at all, not that nothing was sent.
    (coverage_class = 'full_annual' AND planned_usd > 0 AND disbursement_rows > 0) AS is_comparable
FROM fact_base;
