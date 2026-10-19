-- After cleaning, no commitment or disbursement may be negative.
SELECT *
FROM raw_transactions
WHERE trans_code IN ('C', 'D')
  AND trans_usd < 0
