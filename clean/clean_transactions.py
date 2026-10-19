"""Cleaning rules for the transactions table (one row per money movement)."""
import pandas as pd

from common import FIRST_DAY, LAST_VALID_DAY, day_number_to_date, drop_and_log, label_missing_sector

TABLE = "transactions"
KEEP_COLUMNS = [
    "aid", "trans_ref", "trans_day", "trans_currency", "trans_value", "trans_usd",
    "trans_code", "trans_flow_code", "trans_sector", "trans_sector_group",
]

# IATI flow type 10 is official development assistance (ODA). A blank flow type is
# kept: most publishers leave it empty on ordinary aid. Other flows (20 other official
# flows, 30 private grants, 35 private market investment, and so on) are not aid in the
# sense of this project; the biggest is IFC (XM-DAC-903), whose flow is 35.
ODA_FLOW_CODES = ["10"]

# Incoming funds: the receiving organisation reports the same money the donor already
# reported as a disbursement, so keeping it would count the money twice.
# "IF" is Incoming Funds. "11" is Incoming Commitment (the receiver's copy of a commitment);
# the descriptions on the code 11 rows in the download read "Incoming commitment from ...".
INCOMING_CODES = ["IF", "11"]

# The planned-vs-actual work only uses these two, and a negative one is a reversal.
MONEY_CODES = ["C", "D"]

# trans_id is just a row counter inside each activity, so it is left out of the
# duplicate test. trans_sector stays in: one disbursement split over two sectors
# is two real rows.
DUPLICATE_KEY = [
    "aid", "trans_ref", "trans_day", "trans_code", "trans_flow_code", "trans_currency",
    "trans_value", "trans_usd", "trans_sector",
]


def keep_needed_columns(transactions):
    return transactions[KEEP_COLUMNS].copy()


def drop_incoming_funds(transactions):
    is_incoming = transactions["trans_code"].isin(INCOMING_CODES)
    return drop_and_log(transactions, is_incoming, TABLE, "drop_incoming_funds", "trans_usd",
                        note="IF and 11: the receiver's copy of money the donor already reported")


def drop_non_oda_flows(transactions):
    """Keep flow type 10 (ODA) and blank. The note lists what was removed, by flow type
    and for IFC, so the effect is visible in the rule log."""
    flow = transactions["trans_flow_code"]
    is_non_oda = flow.notna() & ~flow.isin(ODA_FLOW_CODES)
    removed = transactions[is_non_oda]
    disbursements = removed[removed["trans_code"] == "D"]
    by_flow = disbursements.groupby("trans_flow_code")["trans_usd"].sum()
    parts = []
    for flow_code, usd in by_flow.items():
        parts.append(f"flow {flow_code}: D USD {usd / 1e6:,.0f}m")
    ifc = disbursements[disbursements["aid"].str.startswith("XM-DAC-903")]
    note = "removed disbursements by flow type (" + "; ".join(parts) + ")"
    note = note + f"; of which IFC (XM-DAC-903): {len(ifc)} D rows, USD {ifc['trans_usd'].sum() / 1e6:,.0f}m"
    return drop_and_log(transactions, is_non_oda, TABLE, "drop_non_oda_flows", "trans_usd", note=note)


def drop_bad_days(transactions):
    day = transactions["trans_day"]
    is_bad = day.isna() | (day < FIRST_DAY) | (day > LAST_VALID_DAY)
    return drop_and_log(transactions, is_bad, TABLE, "drop_bad_days", "trans_usd",
                        note="trans_day missing or outside 2000-01-01..2026-12-31")


def drop_missing_usd(transactions):
    """d-portal already converts each amount to USD on the transaction date.
    A row with no USD value cannot be compared with the others."""
    is_missing = transactions["trans_usd"].isna()
    return drop_and_log(transactions, is_missing, TABLE, "drop_missing_usd",
                        note="no USD value")


def drop_duplicate_transactions(transactions):
    is_duplicate = transactions.duplicated(subset=DUPLICATE_KEY, keep="first")
    return drop_and_log(transactions, is_duplicate, TABLE, "drop_duplicate_transactions", "trans_usd",
                        note="same activity, ref, date, code, amount and sector")


def drop_negative_money(transactions):
    """Negative C or D rows are corrections. They are dropped, not netted, because
    the row they correct is often missing or in a different year. This slightly
    raises the totals; the amount is in the rule log."""
    is_money_code = transactions["trans_code"].isin(MONEY_CODES)
    is_negative = is_money_code & (transactions["trans_usd"] < 0)
    return drop_and_log(transactions, is_negative, TABLE, "drop_negative_money", "trans_usd",
                        note="negative C or D rows (reversals)")


def drop_orphans(transactions, activity_ids):
    """Rows whose activity is not in the activities table cannot be given a donor."""
    is_orphan = ~transactions["aid"].isin(activity_ids)
    return drop_and_log(transactions, is_orphan, TABLE, "drop_orphans", "trans_usd",
                        note="aid not in the cleaned activities table")


def add_date_columns(transactions):
    transactions["trans_date"] = day_number_to_date(transactions["trans_day"])
    transactions["trans_year"] = transactions["trans_date"].dt.year
    return transactions


def clean_transactions(raw, activity_ids):
    transactions = keep_needed_columns(raw)
    transactions = drop_incoming_funds(transactions)
    transactions = drop_non_oda_flows(transactions)
    transactions = drop_bad_days(transactions)
    transactions = drop_missing_usd(transactions)
    transactions = drop_duplicate_transactions(transactions)
    transactions = drop_negative_money(transactions)
    transactions = drop_orphans(transactions, activity_ids)
    transactions = label_missing_sector(transactions, TABLE, "trans_sector", "trans_sector_group")
    transactions = add_date_columns(transactions)
    return transactions
