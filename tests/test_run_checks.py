import importlib.util
import subprocess
import sys
from pathlib import Path

import duckdb

CHECKS_DIR = Path(__file__).resolve().parent.parent / "checks"
RUN_CHECKS_PATH = CHECKS_DIR / "run_checks.py"


def load_run_checks_module():
    spec = importlib.util.spec_from_file_location("run_checks", RUN_CHECKS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_tiny_db(folder, with_bad_row):
    """A two-row table plus one check that fails if any amount is negative."""
    db_path = folder / "tiny.duckdb"
    connection = duckdb.connect(str(db_path))
    connection.execute("CREATE TABLE tiny (id INTEGER, amount DOUBLE)")
    connection.execute("INSERT INTO tiny VALUES (1, 10.0), (2, 20.0)")
    if with_bad_row:
        connection.execute("INSERT INTO tiny VALUES (3, -5.0)")
    connection.close()

    checks_folder = folder / "checks"
    checks_folder.mkdir()
    (checks_folder / "01_no_negative_amounts.sql").write_text("SELECT * FROM tiny WHERE amount < 0")
    return db_path, checks_folder


def test_check_passes_when_no_rows_come_back(tmp_path):
    db_path, checks_folder = make_tiny_db(tmp_path, with_bad_row=False)
    run_checks = load_run_checks_module()
    results = run_checks.run_checks(db_path, checks_folder)
    assert results == [("01_no_negative_amounts.sql", 0)]


def test_check_reports_the_offending_rows(tmp_path):
    db_path, checks_folder = make_tiny_db(tmp_path, with_bad_row=True)
    run_checks = load_run_checks_module()
    results = run_checks.run_checks(db_path, checks_folder)
    assert results == [("01_no_negative_amounts.sql", 1)]


def test_script_exits_non_zero_when_a_check_fails(tmp_path):
    # The script reads the checks folder next to itself, so this runs it on a
    # copy placed beside a failing check.
    db_path, checks_folder = make_tiny_db(tmp_path, with_bad_row=True)
    script_copy = checks_folder / "run_checks.py"
    script_copy.write_text(RUN_CHECKS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    completed = subprocess.run([sys.executable, str(script_copy), str(db_path)], capture_output=True, text=True)
    assert completed.returncode == 1
    assert "FAIL" in completed.stdout
