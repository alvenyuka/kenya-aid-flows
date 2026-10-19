-- The by-year mart and the by-activity mart are grouped differently but come from the same
-- rows, so their planned and disbursed totals must match (within 1 USD).
SELECT y.planned_usd, a.planned_usd, y.disbursed_usd, a.disbursed_usd
FROM (SELECT SUM(planned_usd) AS planned_usd, SUM(disbursed_usd) AS disbursed_usd FROM mart_by_year) AS y
CROSS JOIN (SELECT SUM(planned_usd) AS planned_usd, SUM(disbursed_usd) AS disbursed_usd FROM mart_activity) AS a
WHERE abs(y.planned_usd - a.planned_usd) > 1
   OR abs(y.disbursed_usd - a.disbursed_usd) > 1
