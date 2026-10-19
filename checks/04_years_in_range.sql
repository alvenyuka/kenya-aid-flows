-- Fact years must sit inside the window set in 01_staging.sql.
SELECT f.aid, f.year
FROM fact_activity_year AS f
CROSS JOIN year_window AS w
WHERE f.year < w.first_year OR f.year > w.last_year
