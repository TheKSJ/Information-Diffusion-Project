import json
from pathlib import Path

import pandas as pd

from eventstudy.collection import fetch
from eventstudy.sec_client import SourceError
from eventstudy.storage import load_config


def test_three_company_fetch_preserves_partial_network_failure(tmp_path, monkeypatch):
    import eventstudy.collection as collection
    source_root = Path(__file__).resolve().parents[1]
    (tmp_path / "configs").mkdir()
    config_file = tmp_path / "configs/study.yaml"
    config_file.write_text((source_root / "configs/study.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "configs/universe.csv").write_bytes((source_root / "configs/universe.csv").read_bytes())
    class PartialClient:
        def submissions(self, cik, start, end):
            if cik == 19617:
                raise SourceError("synthetic connection failure for JPM")
            rows = [{"accessionNumber": f"{cik:010d}-24-000001", "form": "8-K", "items": "2.02",
                     "filingDate": "2024-05-01", "primaryDocument": "fixture.htm"}]
            return {"cik": cik, "name": "SYNTHETIC"}, rows, []
    monkeypatch.setattr(collection, "make_client", lambda *args: PartialClient())
    monkeypatch.setattr(collection, "historical_identity", lambda *args: (True, []))
    monkeypatch.setattr(collection, "verify_candidate", lambda row, *args: dict(row, timestamp_verified=True, event_session="2024-05-01"))
    monkeypatch.setattr(collection, "fetch_prices", lambda *args: (pd.DataFrame(), {}))
    monkeypatch.setattr(collection, "audit_filings", lambda *args: [])
    result = fetch(load_config(config_file), pilot=True)
    assert result["requested_companies"] == 3
    assert result["candidate_events"] == 2 and result["verified_events"] == 2
    coverage = pd.read_csv(tmp_path / "data/interim/pilot/issuer_coverage.csv")
    assert set(coverage.ticker) == {"AAPL", "JPM", "CAT"}
    failures = json.loads((tmp_path / "data/interim/pilot/source_failures.json").read_text())
    assert any(r["ticker"] == "JPM" and "synthetic connection" in r["error"] for r in failures)
    assert result["failed_operations"] == 1

