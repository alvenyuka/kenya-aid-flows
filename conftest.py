"""Lets the tests import the cleaning, baseline and model modules, which sit in their own folders."""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "clean"))
sys.path.insert(0, str(PROJECT_DIR / "model"))
sys.path.insert(0, str(PROJECT_DIR / "baseline"))
sys.path.insert(0, str(PROJECT_DIR / "site"))
sys.path.insert(0, str(PROJECT_DIR / "ingest"))
