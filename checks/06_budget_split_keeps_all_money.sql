-- Cutting budget lines into calendar-year pieces must not create or lose money.
-- Compares the pieces with the original lines in the cleaned table (within 1 USD).
SELECT p.pieces_usd, r.lines_usd
FROM (SELECT SUM(usd_in_year) AS pieces_usd FROM budget_pieces) AS p
CROSS JOIN (
    SELECT SUM(budget_usd) AS lines_usd FROM raw_budgets WHERE budget_type_name = 'original'
) AS r
WHERE abs(p.pieces_usd - r.lines_usd) > 1
