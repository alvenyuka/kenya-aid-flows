-- Every transaction and budget row must belong to an activity in the activities table.
SELECT t.aid, 'transactions' AS source_table
FROM raw_transactions AS t
LEFT JOIN raw_activities AS a ON a.aid = t.aid
WHERE a.aid IS NULL
UNION ALL
SELECT b.aid, 'budgets' AS source_table
FROM raw_budgets AS b
LEFT JOIN raw_activities AS a ON a.aid = b.aid
WHERE a.aid IS NULL
