-- dim_activity must have one row per activity, or every join to it multiplies money.
SELECT aid, COUNT(*) AS copies
FROM dim_activity
GROUP BY aid
HAVING COUNT(*) > 1
