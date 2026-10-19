"""Run every stage in order. Stops at the first stage that fails.

    py -3 run_all.py              (re-uses today's downloaded files if they exist)
    py -3 run_all.py --refresh    (download again)
"""
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

STAGES = [
    ("1 fetch", "ingest/fetch_dportal.py"),
    ("2 first look", "explore/first_look.py"),
    ("3 clean", "clean/run_clean.py"),
    ("4 warehouse", "warehouse/build_db.py"),
    ("5 sql models", "sql/run_sql.py"),
    ("6 checks", "checks/run_checks.py"),
    ("7 baseline", "baseline/rule_of_thumb.py"),
    ("8 model", "model/slippage.py"),
    ("9 results", "report/make_results.py"),
    ("10 figures", "report/make_figures.py"),
    ("11 page", "site/build_page.py"),
]


def main():
    extra_arguments = sys.argv[1:]
    start = time.time()
    for stage_name, script in STAGES:
        print(f"\n===== stage {stage_name} =====", flush=True)
        stage_start = time.time()
        command = [sys.executable, str(PROJECT_DIR / script)]
        if script.startswith("ingest"):
            command = command + extra_arguments
        completed = subprocess.run(command, cwd=PROJECT_DIR)
        if completed.returncode != 0:
            print(f"Stage {stage_name} failed with exit code {completed.returncode}")
            sys.exit(completed.returncode)
        print(f"stage {stage_name} took {time.time() - stage_start:.0f} s", flush=True)
    print(f"\nAll stages finished in {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
