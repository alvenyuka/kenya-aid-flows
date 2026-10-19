import re
from pathlib import Path

import common

PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_sql_year_window_matches_the_python_constants():
    staging = (PROJECT_DIR / "sql" / "01_staging.sql").read_text(encoding="utf-8")
    first_year = int(re.search(r"(\d{4}) AS first_year", staging).group(1))
    last_year = int(re.search(r"(\d{4}) AS last_year", staging).group(1))
    assert first_year == common.FIRST_YEAR
    assert last_year == common.END_YEAR
