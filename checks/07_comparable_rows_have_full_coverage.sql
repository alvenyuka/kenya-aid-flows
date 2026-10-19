-- Every comparable activity-year must have an annual (400 days or fewer) original budget
-- line covering EVERY day of the year. Tested straight from the cleaned budget table,
-- day by day, not from the coverage table built in the SQL models.
WITH calendar AS (
    SELECT
        CAST(EXTRACT(year FROM day) AS INTEGER) AS year,
        day
    FROM (SELECT unnest(generate_series(DATE '2010-01-01', DATE '2024-12-31', INTERVAL 1 DAY)) AS day)
)
SELECT c.aid, c.year
FROM comparable_activity_years AS c
INNER JOIN calendar AS k ON k.year = c.year
WHERE NOT EXISTS (
    SELECT 1
    FROM raw_budgets AS b
    WHERE b.aid = c.aid
      AND b.budget_type_name = 'original'
      AND b.budget_days <= 400
      AND k.day BETWEEN b.budget_start AND b.budget_end
)
GROUP BY c.aid, c.year
