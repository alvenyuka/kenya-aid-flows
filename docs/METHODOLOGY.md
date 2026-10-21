# Method details

Detail moved out of the README to keep it readable. Every figure comes from `outputs/results.json` (written by `report/make_results.py`) or `data/clean/rule_log.csv` (written by the cleaning step), snapshot 2026-10-19.

## How the answer changes

The headline is 2,901 activity-years (one project in one calendar year). Each row below changes one choice.

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

## Publishers set aside

- **The Gates Foundation:** its budgets repeat its disbursements (1,090 activity-years, 100% within 1% of plan). This removes 1,090 headline activity-years.
- **CGIAR:** its budgets cover only a slice of its spending (1,074 activity-years, median ratio 4.47). Most of its years already fail the coverage test, so the rule removes 20 more.
- **UNHCR:** removes 8 activity-years.
- **Thresholds**, all chosen after looking at the data: a copy is 100 or more activity-years with 95% within 1% of plan; a partial budget is 100 or more with a median ratio above 3; a needs-based budget is at least 3 years, a disbursement ratio under 30% in every year, at least 70% of the plan on lines with no stated type, and more spending reported as expenditure than as disbursement.
- **IFC:** its disbursements are flow type 35 (private market investment), not aid, so 129 IFC disbursement rows worth $3,842 million are removed with the other non-ODA flows.

## Cleaning rules that remove rows

Each rule in `clean/` logs rows in, rows out and dollars removed to `data/clean/rule_log.csv`. Negative dollar figures are the sum of the negative amounts removed.

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

Incoming funds are the receiver's copy of money the donor already reported, so keeping them counts the money twice. The non-ODA rule keeps flow type 10 (official development assistance) and blank, and its dollars include every transaction code. Rows with a missing sector are kept as "Unknown" (7,811 transactions, 2,110 budget lines). Only dates from 2000 to the end of 2026 are accepted. After cleaning there are 26,429 activities, 334,070 transactions (134,019 disbursement rows, 51,849 commitment rows) and 79,571 budget lines.
