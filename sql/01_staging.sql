-- Staging: thin views over the cleaned tables, so later files read from clear names.

-- Years that are compared: 2010 to 2024, fixed numbers (not the run date) so results do
-- not change when the calendar year turns. They must equal FIRST_YEAR and END_YEAR in
-- clean/common.py; tests/test_settings.py checks that. IATI reporting before 2010 is thin.
-- The window ends in 2024 because publishers report late: in the 2026-10-19 download,
-- disbursements dated 2025 were about 25% below 2024 while the 2025 budgets were the
-- largest ever, which looks like missing reports, not a real fall.
CREATE OR REPLACE VIEW year_window AS
SELECT
    2010 AS first_year,
    2024 AS last_year;

CREATE OR REPLACE VIEW stg_activities AS
SELECT
    aid,
    reporting_ref,
    reporting,
    title,
    status_code,
    date_start,
    date_end
FROM raw_activities;

-- Money actually sent (disbursements), by calendar year of the transaction.
CREATE OR REPLACE VIEW stg_disbursements AS
SELECT
    aid,
    trans_year AS year,
    trans_sector_group AS sector_group,
    trans_usd AS usd
FROM raw_transactions
WHERE trans_code = 'D';

-- Money reported as spent (expenditure, code E). Many publishers report spending as E
-- instead of D, so E is used to judge whether a missing disbursement is a real gap.
CREATE OR REPLACE VIEW stg_expenditures AS
SELECT
    aid,
    trans_year AS year,
    trans_usd AS usd
FROM raw_transactions
WHERE trans_code = 'E';

-- Money promised (commitments).
CREATE OR REPLACE VIEW stg_commitments AS
SELECT
    aid,
    trans_year AS year,
    trans_usd AS usd
FROM raw_transactions
WHERE trans_code = 'C';

-- Original budget lines, one row per line, with an id. "Original" includes lines with no
-- type (the IATI standard says an omitted type means original; see clean/clean_budgets.py).
-- A revised budget is a later plan, so using it would hide the slippage this project
-- measures. Planned-disbursement rows were already removed in cleaning.
-- is_annual: the line covers 400 days or fewer, so it is a one-year budget (some are
-- fiscal years or 52-week years, hence 400 and not 366).
CREATE OR REPLACE TABLE stg_budget_lines AS
SELECT
    row_number() OVER () AS line_id,
    aid,
    budget_sector_group AS sector_group,
    budget_sector AS sector,
    budget_start,
    budget_end,
    budget_days,
    budget_days <= 400 AS is_annual,
    budget_usd,
    type_was_blank
FROM raw_budgets
WHERE budget_type_name = 'original';

-- Names for the 3-digit OECD DAC sector groups seen most often. Anything not listed
-- keeps its code as the name.
CREATE OR REPLACE TABLE dim_sector_group AS
SELECT * FROM (VALUES
    ('111', 'Education, level unspecified'),
    ('112', 'Basic education'),
    ('113', 'Secondary education'),
    ('114', 'Post-secondary education'),
    ('121', 'Health, general'),
    ('122', 'Basic health'),
    ('123', 'Non-communicable diseases'),
    ('130', 'Population and reproductive health'),
    ('140', 'Water supply and sanitation'),
    ('151', 'Government and civil society'),
    ('152', 'Conflict, peace and security'),
    ('160', 'Other social infrastructure'),
    ('210', 'Transport and storage'),
    ('220', 'Communications'),
    ('230', 'Energy'),
    ('231', 'Energy policy'),
    ('232', 'Energy generation, renewable sources'),
    ('233', 'Energy generation, non-renewable sources'),
    ('236', 'Energy distribution'),
    ('240', 'Banking and financial services'),
    ('250', 'Business and other services'),
    ('311', 'Agriculture'),
    ('312', 'Forestry'),
    ('313', 'Fishing'),
    ('321', 'Industry'),
    ('322', 'Mineral resources and mining'),
    ('323', 'Construction'),
    ('331', 'Trade policy and regulations'),
    ('332', 'Tourism'),
    ('410', 'General environmental protection'),
    ('430', 'Other multisector'),
    ('510', 'General budget support'),
    ('520', 'Development food assistance'),
    ('530', 'Other commodity assistance'),
    ('600', 'Action relating to debt'),
    ('720', 'Emergency response'),
    ('730', 'Reconstruction relief'),
    ('740', 'Disaster prevention and preparedness'),
    ('910', 'Administrative costs of donors'),
    ('920', 'Support to non-governmental organisations'),
    ('998', 'Unallocated or unspecified')
) AS names(sector_group, sector_group_name);
