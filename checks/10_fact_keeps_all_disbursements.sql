-- Every disbursement dollar dated inside the year window must be in the fact table:
-- raw cleaned transactions against the fact, within 1 USD.
SELECT t.raw_usd, f.fact_usd
FROM (
    SELECT SUM(trans_usd) AS raw_usd
    FROM raw_transactions
    WHERE trans_code = 'D' AND trans_year BETWEEN 2010 AND 2024
) AS t
CROSS JOIN (SELECT SUM(disbursed_usd) AS fact_usd FROM fact_activity_year) AS f
WHERE abs(t.raw_usd - f.fact_usd) > 1
