"""Rounds the numbers in a results dictionary, so two runs write byte-identical files.

Dollar amounts go to cents, everything else to six decimals. The totals come from
parallel SQL sums, which can differ in the last binary digit between runs.
"""


def round_numbers(value):
    """Return a copy of value (dicts, lists, numbers) with every float rounded."""
    if isinstance(value, dict):
        rounded = {}
        for key in value:
            rounded[key] = round_numbers(value[key])
        return rounded
    if isinstance(value, list):
        rounded_list = []
        for item in value:
            rounded_list.append(round_numbers(item))
        return rounded_list
    if isinstance(value, float):
        if abs(value) >= 1000:
            return round(value, 2)
        return round(value, 6)
    return value
