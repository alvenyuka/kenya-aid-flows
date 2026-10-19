-- One row per activity per year.
SELECT aid, year, COUNT(*) AS copies
FROM fact_activity_year
GROUP BY aid, year
HAVING COUNT(*) > 1
