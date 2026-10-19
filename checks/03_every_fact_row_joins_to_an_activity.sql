-- Every activity-year in the fact table must have a row in dim_activity.
SELECT f.aid, f.year
FROM fact_activity_year AS f
LEFT JOIN dim_activity AS d ON d.aid = f.aid
WHERE d.aid IS NULL
