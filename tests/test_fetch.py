import json

import fetch_dportal


def write_old_download(raw_dir, table_name, file_date, rows):
    (raw_dir / f"{table_name}_{file_date}.csv").write_text("aid\nX\n")
    log = {"rows_fetched": rows, "rows_expected_by_api_count": rows, "pages": 1, "file": f"{table_name}_{file_date}.csv"}
    (raw_dir / f"fetch_log_{table_name}_{file_date}.json").write_text(json.dumps(log))


def test_latest_download_picks_the_newest_date(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_dportal, "RAW_DIR", tmp_path)
    write_old_download(tmp_path, "act", "2026-01-05", 1)
    write_old_download(tmp_path, "act", "2026-03-09", 2)
    assert fetch_dportal.latest_download("act").name == "act_2026-03-09.csv"
    assert fetch_dportal.latest_download("trans") is None


def test_rerun_on_a_later_day_reuses_the_old_download(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_dportal, "RAW_DIR", tmp_path)
    monkeypatch.setattr(fetch_dportal.sys, "argv", ["fetch_dportal.py"])
    for table_name in ["act", "trans", "budget"]:
        write_old_download(tmp_path, table_name, "2026-01-05", 1)

    def fail_if_called(*arguments):
        raise AssertionError("the API must not be called when a download exists")

    monkeypatch.setattr(fetch_dportal, "count_rows", fail_if_called)
    monkeypatch.setattr(fetch_dportal, "fetch_table", fail_if_called)

    fetch_dportal.main()

    fetch_log = json.loads((tmp_path / "fetch_log.json").read_text())
    assert fetch_log["fetch_date"] == "2026-01-05"
