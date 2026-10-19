"""A tiny shared log: every cleaning rule records how many rows (and dollars) it removed."""
import pandas as pd

RULE_LOG = []


def clear_log():
    RULE_LOG.clear()


def log_rule(table, rule, rows_in, rows_out, usd_removed=0.0, note=""):
    entry = {
        "table": table,
        "rule": rule,
        "rows_in": int(rows_in),
        "rows_out": int(rows_out),
        "rows_removed": int(rows_in) - int(rows_out),
        "usd_removed": round(float(usd_removed), 2),
        "note": note,
    }
    RULE_LOG.append(entry)
    print(f"  [{table}] {rule}: {rows_in} -> {rows_out} rows (removed {entry['rows_removed']}, USD {entry['usd_removed']:,.0f})")


def save_log(path):
    log_table = pd.DataFrame(RULE_LOG)
    log_table.to_csv(path, index=False)
    return log_table
