# Kenya Aid Flows

A data pipeline that downloads Kenya's open aid data, cleans it, and measures how much of the money donors scheduled for a year actually arrived in that year.

![Bar chart of planned and disbursed aid to Kenya by year, 2010 to 2024, for activities with a full-year annual budget](figures/planned_vs_disbursed_by_year.png)

## What this project does

Donors tell Kenya how much they plan to give in a year, and governments and charities budget around those promises. When the money arrives late or short, projects stall. This project asks: for each project and year, how much of the scheduled money was disbursed in that year, and which donors and sectors fall short most?

The measure is a variant inspired by the Paris Declaration and GPEDC indicator 7 (aid disbursed within the fiscal year for which it was scheduled). It differs in four ways: it uses calendar years, not Kenya's July to June fiscal year; it works at activity level, not donor-country level; it includes NGO publishers; and an overshoot is not penalised in the main figure (a penalised variant is below).

The data is the International Aid Transparency Initiative (IATI) records for Kenya, read through the d-portal query API: 26,438 activities, 469,065 transactions and 113,136 budget lines, snapshot taken 2026-10-19. Years compared: 2010 to 2024. DuckDB (a database in one file) holds the tables and plain numbered SQL files build the results.

## Results

The measure covers activity-years (one project in one calendar year) where the donor's original annual budget lines cover the whole year, the plan is above zero, and at least one disbursement is reported. Three publishers whose budgets cannot be compared with their spending are set aside (below). That leaves 2,901 activity-years from 1,416 activities.

- **73% of the scheduled money arrived in its own year.** Of $4.63 billion planned, $3.40 billion was disbursed up to the plan. Any amount above plan is not counted, so one over-spending project cannot hide another that fell short. A variant that also penalises overshoot (money that arrived divided by the larger of disbursed and planned) gives 60%.
- **Disbursed against planned: 0.96.** $4.45 billion was disbursed against $4.63 billion planned. The middle activity-year sent 0.95 of its plan.
- **28.9% of activity-years received under 70% of plan.** 58.8% fell short of plan (under 99%), 34.6% went over (above 101%), and 6.7% were within 1% of plan.
- **A simple rule gets a decent lift.** Flagging an activity-year when the same activity disbursed under 70% of plan in earlier years gave flags that were right 67% of the time, against a 31% base rate (the hit rate of flagging everything), and caught 59% of the true cases (706 activity-years scored, 2020 on).

- **A logistic regression does not beat that rule.** Trained on 779 activity-years before 2020 and scored on the same 706 test rows, it ranks them a little better (PR-AUC 0.70 against 0.66). At the same number of flags (192) its precision is 65% against 67% and its recall 58% against 59%, so on the flags themselves it is no better.

**UNHCR is set aside, and it matters.** The UN refugee agency (UNHCR, XM-DAC-41121) publishes needs-based budgets, an appeal for what is needed, and reports most of its spending as expenditure, not disbursement. Its 8 activity-years carry $1.35 billion of planned money and only 20% of it arrived as disbursement. With UNHCR left in, the result is 61% arrived and a ratio of 0.79 on 2,909 activity-years. The rule that sets it aside (below) was written after looking at UNHCR's numbers, so it is built to describe it.

By year (`outputs/results.json`, written by `report/make_results.py`). Arrived is the share of the plan that arrived in its year, and the sixth column puts UNHCR back, which is the dip in 2016 to 2020, 2023 and 2024:

| Year | Activity-years | Planned ($m) | Disbursed ($m) | Arrived | Arrived with UNHCR | Ratio | Median ratio | Under 70% of plan |
|---|---|---|---|---|---|---|---|---|
| 2010 | 90 | 145 | 137 | 68% | 68% | 0.94 | 1.05 | 15.6% |
| 2011 | 107 | 197 | 212 | 74% | 74% | 1.07 | 1.16 | 11.2% |
| 2012 | 169 | 256 | 291 | 78% | 78% | 1.14 | 1.03 | 13.0% |
| 2013 | 157 | 255 | 261 | 77% | 77% | 1.02 | 1.09 | 22.3% |
| 2014 | 141 | 244 | 208 | 66% | 66% | 0.85 | 1.00 | 25.5% |
| 2015 | 151 | 238 | 233 | 78% | 78% | 0.98 | 0.93 | 27.2% |
| 2016 | 181 | 219 | 203 | 68% | 43% | 0.93 | 0.92 | 34.8% |
| 2017 | 189 | 249 | 255 | 74% | 50% | 1.02 | 0.95 | 29.6% |
| 2018 | 225 | 304 | 347 | 71% | 51% | 1.14 | 0.96 | 32.9% |
| 2019 | 228 | 322 | 320 | 80% | 60% | 0.99 | 0.95 | 34.2% |
| 2020 | 240 | 363 | 327 | 75% | 58% | 0.90 | 0.93 | 35.0% |
| 2021 | 270 | 412 | 331 | 73% | 73% | 0.80 | 0.91 | 41.1% |
| 2022 | 200 | 417 | 376 | 68% | 68% | 0.90 | 0.88 | 32.5% |
| 2023 | 275 | 420 | 406 | 71% | 56% | 0.97 | 0.93 | 29.1% |
| 2024 | 278 | 591 | 545 | 77% | 63% | 0.92 | 0.93 | 24.1% |

![Histogram of disbursed divided by planned for each activity-year, with lines at 70% and 100%](figures/ratio_distribution.png)

The bunch near 1.0 is activities that sent about what they planned. The long tail to the left is the shortfall, and the pile at zero is activity-years with a plan and almost nothing disbursed.

### How the answer changes

| Version | Activity-years | Arrived | Ratio |
|---|---|---|---|
| Headline | 2,901 | 73% | 0.96 |
| UNHCR put back | 2,909 | 61% | 0.79 |
| Expenditure counted as arrived too (an upper bound) | 2,901 | 76% | 1.00 |
| Budget lines with a stated type only | 2,000 | 73% | 0.98 |
| Part-year annual plans | 3,527 | 72% | 1.08 |
| Multi-year budgets split evenly | 532 | 77% | 2.90 |
| Missing disbursement counted as zero (a lower bound) | 3,611 | 63% | 0.82 |

- **Stated-type lines only** (2,000 activity-years) has a median ratio of 0.93 and 33.3% under 70% of plan. It drops the 9,004 budget lines ($4.42 billion) with no type, which the main figure treats as original because the IATI standard says "If the @type attribute is omitted, then BudgetType code 1 (Original) is assumed" (https://iatistandard.org/en/iati-standard/203/activity-standard/iati-activities/iati-activity/budget/).
- **The zero-counted version** adds full-year plans with no disbursement row (710 counted as zero), only for activities that report disbursements in another year. It is a lower bound because a zero can mean the publisher reports spending as expenditure. 2,687 more full-year plans ($1.52 billion) belong to activities that never report a disbursement, 1,405 of them to activities that report expenditure, and are not counted.
- **Multi-year budgets** are not a plan for any one year, so the ratio of 2.90 says little.

### Which donors and sectors fall furthest short

Ranked by the share of the plan that arrived in its year, lowest first, among groups with at least 10 comparable activity-years (27 donors and 27 sectors qualify), because smaller groups swing on one or two projects. NGOs and agencies report too, so the first column is a reporting organisation.

| Reporting organisation | Activity-years | Planned ($m) | Arrived | Ratio |
|---|---|---|---|---|
| Diakonia | 11 | 1 | 1% | 0.01 |
| International Trade Centre (ITC) | 30 | 13 | 3% | 0.03 |
| Stichting Agriterra | 52 | 4 | 15% | 0.15 |
| International Organization for Migration (IOM) | 10 | 7 | 38% | 0.52 |
| HelpAge International | 28 | 20 | 44% | 0.44 |
| Global Environment Facility | 47 | 33 | 54% | 0.79 |
| Hivos | 17 | 38 | 55% | 0.57 |
| Mensen met een Missie | 11 | 6 | 57% | 0.62 |
| AFD | 38 | 55 | 60% | 0.75 |
| Liverpool School of Tropical Medicine | 11 | 2 | 66% | 0.71 |

| Sector group | Activity-years | Planned ($m) | Arrived | Ratio |
|---|---|---|---|---|
| Unknown | 16 | 27 | 13% | 0.14 |
| Unallocated or unspecified | 14 | 7 | 18% | 0.20 |
| Energy generation, renewable sources | 41 | 19 | 25% | 0.35 |
| Energy policy | 31 | 461 | 49% | 0.75 |
| Basic education | 75 | 75 | 50% | 0.60 |
| Post-secondary education | 84 | 65 | 55% | 0.79 |
| Industry | 41 | 25 | 59% | 0.73 |
| Health, general | 147 | 70 | 68% | 0.97 |
| Population and reproductive health | 101 | 101 | 68% | 0.92 |
| Other social infrastructure | 95 | 89 | 72% | 0.78 |

"Unknown" and "Unallocated or unspecified" are activities with no usable sector code. Several rows rest on little money, so read the planned column first. The Emergency response sector is no longer near the bottom (76% arrived on 73 activity-years); with UNHCR left in it is 24%.

### Publishers set aside

- **The Gates Foundation:** its budgets repeat its disbursements (1,090 activity-years, 100% within 1% of plan). This removes 1,090 headline activity-years.
- **CGIAR:** its budgets cover only a slice of its spending (1,074 activity-years, median ratio 4.47). Most of its years already fail the coverage test, so the rule removes 20 more.
- **UNHCR:** removes 8 activity-years.
- **Thresholds**, all chosen after looking at the data: a copy is 100 or more activity-years with 95% within 1% of plan; a partial budget is 100 or more with a median ratio above 3; a needs-based budget is at least 3 years, a disbursement ratio under 30% in every year, at least 70% of the plan on lines with no stated type, and more spending reported as expenditure than as disbursement.
- **IFC:** its disbursements are flow type 35 (private market investment), not aid, so 129 IFC disbursement rows worth $3,842 million are removed with the other non-ODA flows.

## How I built it

1. **Download the data** (`ingest/fetch_dportal.py`). It pages through d-portal's `act` (activities), `trans` (transactions) and `budget` tables for Kenya, 5,000 rows per request, with a pause between pages, a User-Agent naming the project, retries with waiting, and a file cache so a re-run the same day does not download again. Every table matched the API's own row count. Raw files go to `data/raw/` (not committed).
2. **Look at the raw data** (`explore/first_look.py`). It prints transaction codes, flow types, budget types and missing values, then builds the simplest planned-vs-disbursed table with no cleaning. That table is unstable (0.20 to 4.93 depending on the year, 1.07 overall), which is what the later steps fix.
3. **Clean it, one rule per function** (`clean/`). Each rule logs rows in, rows out and dollars removed to `data/clean/rule_log.csv`. The rules that remove rows:

   | Table and rule | Rows removed | USD removed ($m) |
   |---|---|---|
   | activities: duplicates | 9 | 0 |
   | transactions: incoming funds (codes IF and 11) | 102,089 | 11,153 |
   | transactions: non-ODA flow types | 5,863 | 14,453 |
   | transactions: impossible dates | 824 | 2,284 |
   | transactions: exact duplicates | 7,403 | 4,095 |
   | transactions: negative commitments and disbursements | 18,815 | -3,691 |
   | transactions: no matching activity | 1 | 0 |
   | budgets: planned-disbursement rows | 24,209 | 3,479 |
   | budgets: impossible dates | 5,217 | 9,567 |
   | budgets: exact duplicates | 2,753 | 23,239 |
   | budgets: negative budgets | 1,386 | -294 |

   Incoming funds are the receiver's copy of money the donor already reported, so keeping them counts the money twice. The non-ODA rule keeps flow type 10 (official development assistance) and blank, and its dollars include every transaction code. Rows with a missing sector are kept as "Unknown" (7811 transactions, 2110 budget lines). Only dates from 2000 to the end of 2026 are accepted. After cleaning there are 26,429 activities, 334,070 transactions (134,019 disbursement rows, 51,849 commitment rows) and 79,571 budget lines.
4. **Load a database** (`warehouse/build_db.py`). The cleaned parquet files become three DuckDB tables.
5. **Build the models in SQL** (`sql/01_staging.sql` to `04_marts.sql`, run by `sql/run_sql.py`). The key table is `fact_activity_year`: one row per activity per year with the planned amount, the disbursed amount, their ratio and a coverage class. Of 46,232 activity-years, 25,460 have no original budget, 7,961 have annual lines covering only part of the year, 5,020 are covered only by a longer budget, and 7,791 have a full-year annual budget. Of those, 4,019 report a disbursement, and 2,901 remain after the publisher rules. Another 3,408 full-year plans have no disbursement row. The rules:
   - Planned is the original budget only: a revised budget is a later plan and would hide slippage. Lines with no type count as original (see above).
   - Each budget line is cut into calendar-year pieces by days. A check confirms the pieces add back up to the lines. A year is comparable only if annual lines (400 days or fewer) cover every day of it; 3,634 lines run longer than a year.
   - Actual is the sum of disbursements (code D) dated in that year.
   - Years are 2010 to 2024, fixed in `clean/common.py` and `sql/01_staging.sql` so numbers do not change with the run date. Disbursements dated 2025 are 25% below 2024 while the 2025 budgets are the largest of any year, which looks like late reporting.
   - Each activity gets one sector group: the one with the most disbursed money, else the most planned money.
6. **Check the tables** (`checks/`, run by `checks/run_checks.py`). Ten SQL queries that must return zero rows, including that the day split keeps every budget dollar, that every comparable row has a full year of annual coverage (tested day by day from the budget table), that no disbursement is lost between the cleaned data and the fact table, and that two differently grouped marts agree. The script exits with an error if any returns a row. 
7. **Write the figures** (`report/make_results.py`, `report/make_figures.py`) into `outputs/results.json` and `figures/`. Every number in this README comes from that file.
8. **Try a rule of thumb** (`baseline/rule_of_thumb.py`). For each activity-year, add up the plans and disbursements of the same activity's earlier years. If that ratio is under 70%, flag it, then compare with what happened that year. The headline version scores only years with a disbursement. It excludes Gates by the copy rule on all years, and CGIAR and UNHCR using only years before 2020. A second version counts a missing disbursement as zero when the activity disbursed in an earlier year (nothing from later years decides who is in): precision 77% against a 46% base rate on 929 activity-years, but 132 of its 263 true positives are years with no disbursement row, so it partly detects activities that stop reporting.
9. **Fit a model** (`model/slippage.py`). A logistic regression (a model that turns features into a probability) flags activity-years likely to arrive under 70% of plan. Same rows, same 2020 split and no peeking at later years as the rule. It is trained on years before 2020 only, with features from earlier years: the activity's earlier ratio and count of earlier years, plan size, the publisher's earlier record and the sector with the most planned money. The publisher's record keeps updating through the test years, from strictly earlier years only, like the activity's own earlier ratio: a 2022 row uses the outcomes of 2020 and 2021. At a fixed 0.5 cut-off it flags 134 rows with 75% precision and 47% recall. Nothing was tuned on the test years. PR-AUC (area under the precision-recall curve) measures how well scores rank true cases first.
10. **Build the page** (`site/build_page.py`) writes the results page `site/index.html` from the two results files.
11. **Test the rules** (`tests/`). Small hand-made tables test every cleaning rule, the history features, the year settings in SQL and Python are tested to agree, and a tiny DuckDB tests that `run_checks.py` reports a failing check and exits non-zero.

## Problems I hit

- **Multi-year budgets made the ratio meaningless.** Split evenly, a three-year budget is not the plan for any one of its years (ratio 2.90 on those years alone). Only years fully covered by annual lines are compared.
- **Three publishers' budgets did not describe their spending.** Gates copied disbursements into its budget, CGIAR budgeted only a slice, and UNHCR budgeted needs. Each has a stated rule above.
- **IFC investments looked like aid.** Keeping the flow type and restricting to ODA removed them.
- **The budget table holds two kinds of rows.** d-portal mixes budgets and planned disbursements in one table; 24,209 planned-disbursement rows are removed before anything is summed.
- **The newest year looked like a collapse.** I treated 2025 as late reporting and ended the window at 2024.
- **A row counter is not a duplicate test.** `trans_id` repeats within an activity, and leaving the sector out of the key would delete rows split across sectors. The key uses the activity, reference, date, code, flow type, amount and sector.
- **Ranking by dollars short measured timing, not reliability.** It put the African Development Bank first even though it sent more than planned overall. The rankings use the share that arrived, with at least 10 activity-years.

## Data

IATI data for Kenya through the d-portal query API (`https://d-portal.org/q.json`), retrieved 2026-10-19 (the snapshot date: a re-run reuses the most recent download and keeps this date unless run with `--refresh`). Each publisher sets its own licence in the IATI Registry. The raw data is not redistributed here, and derived figures credit "IATI publishers via d-portal.org", retrieved 2026-10-19. Amounts are in US dollars as converted by d-portal.

## Limits

- Only 2,901 of 46,232 activity-years can be compared, and publishers that give full-year budgets are not a random sample of aid to Kenya.
- The comparison is against the original budget. Budgets are often revised, so a project can look short when its plan changed.
- Removing incoming funds does not remove every double count: if a donor and its implementer both report one disbursement, both stay.
- Negative disbursements and commitments are dropped, not netted, which raises totals slightly.
- Overlapping original budget lines are added together. Inside the headline set that is $10 million of $4.63 billion planned (0.2%), so I left it in.
- The publisher thresholds were chosen after seeing the data, and other unusual publishers may remain.
- A zero disbursement can be a reporting habit (spending reported as expenditure). The expenditure version counts D plus E, which double counts a publisher that reports the same money both ways.
- Sector names come from a list I typed from the OECD DAC codes. I have not compared the yearly totals with published Kenya aid figures.
- The baseline is scored on 706 activity-years, and 557 test-year rows had no earlier year to learn from.

## How to run

Prerequisites: Python 3.13 with the packages in `requirements.txt` (DuckDB, pandas, pyarrow, requests, matplotlib, scikit-learn, numpy, pytest).

```
py -3 -m pip install -r requirements.txt
py -3 run_all.py            # all stages; the first download takes about 15 minutes
py -3 -m pytest             # the tests
```

Each stage also runs alone, for example `py -3 checks/run_checks.py`. `py -3 run_all.py --refresh` downloads again. `.github/workflows/refresh.yml` runs the same steps monthly once the project is on GitHub.

## Project structure

```
ingest/     download with retries and a cache      explore/   raw-data facts, first naive table
clean/      one function per cleaning rule         warehouse/ parquet files into DuckDB
sql/        staging, fact, dimensions, marts       checks/    SQL queries that must return zero rows
baseline/   the 70% rule and its scores            report/    results.json and the charts
model/      logistic regression vs the rule         site/      results page and its builder
outputs/    results.json and its inputs            figures/   the two charts
tests/      pytest                                 run_all.py every stage in order
```

## License

MIT. See `LICENSE`.

Alven Yuka · [LinkedIn](https://www.linkedin.com/in/alven-yuka-610b78174/) · [Email](mailto:alvenyuka2@gmail.com)
