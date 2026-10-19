"""Stage 4: run every numbered .sql file in this folder, in order, against the DuckDB file."""
from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).resolve().parent
DB_PATH = SQL_DIR.parent / "data" / "aid_flows.duckdb"


def main():
    connection = duckdb.connect(str(DB_PATH))
    sql_files = sorted(SQL_DIR.glob("0*.sql"))
    for sql_file in sql_files:
        print(f"running {sql_file.name}")
        connection.execute(sql_file.read_text(encoding="utf-8"))
    connection.close()


if __name__ == "__main__":
    main()
