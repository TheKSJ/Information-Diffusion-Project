import json
from pathlib import Path

import pandas as pd
import pytest

from eventstudy.cli import main
from eventstudy.demo import synthetic_inputs
from eventstudy.pipeline import analyze_inputs, apply_release_reviews, calculate_events
from eventstudy.storage import load_config, sha256
from eventstudy.validation import validate_config, validate_pairs

ROOT = Path(__file__).resolve().parents[1]


def test_fixed_config_and_cli_codes(capsys, tmp_path):
    config = load_config(ROOT / "configs/study.yaml")
    assert len(validate_config(config)) == 30
    assert main(["validate", "--config", str(ROOT / "configs/study.yaml")]) == 0
    assert "valid" in capsys.readouterr().out
    assert main(["run", "--config", str(tmp_path / "missing.yaml")]) == 1
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0


def test_offline_end_to_end_and_identical_outputs(tmp_path, monkeypatch):
    import requests
    import yfinance
    def forbidden(*args, **kwargs):
        raise AssertionError("offline integration attempted network access")
    monkeypatch.setattr(requests.Session, "get", forbidden)
    monkeypatch.setattr(yfinance, "download", forbidden)
    config, filings, candidates, coverage, prices = synthetic_inputs(2)
    config["study"].update(start="2021-01-01", end="2021-06-30", bootstrap_draws=100)
    for name in ["first", "second"]:
        summary = analyze_inputs(config, filings, candidates, coverage, prices, [], tmp_path / name,
                                 synthetic=True, run_robustness=True)
        assert summary["data_kind"] == "SYNTHETIC"
        assert summary["verified_events"] == len(candidates)
        assert summary["matched_controls"] > 0
        pairs = pd.read_csv(tmp_path / name / "matched_pairs.csv")
        validate_pairs(pairs)
        event_long = pd.read_csv(tmp_path / name / "event_abnormal_returns.csv")
        control_long = pd.read_csv(tmp_path / name / "control_abnormal_returns.csv")
        for _, pair in pairs.iterrows():
            e = event_long[(event_long.event_id == pair.event_id) & event_long.offset.between(1, 5)]
            c = control_long[(control_long.control_id == pair.control_id) & control_long.offset.between(1, 5)]
            assert len(e) == 5 and len(c) == 5
            assert pair.event_signed_post_car == pytest.approx(e.abnormal_return.sum() * (1 if pair.event_ar0 > 0 else -1))
            assert pair.control_signed_post_car == pytest.approx(c.abnormal_return.sum() * (1 if pair.control_ar0 > 0 else -1))
    for source in sorted((tmp_path / "first").rglob("*")):
        if source.is_file():
            target = tmp_path / "second" / source.relative_to(tmp_path / "first")
            assert sha256(source.read_bytes()) == sha256(target.read_bytes()), source.name


def test_empty_dataset_produces_untestable_outputs(tmp_path):
    config, *_ = synthetic_inputs(1)
    summary = analyze_inputs(config, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {},
                             [{"stage": "network", "error": "fixture failure"}], tmp_path, run_robustness=True)
    assert summary["status"] == "no_testable_matched_sample"
    result = json.loads((tmp_path / "primary_inference.json").read_text())
    assert result["estimate_pp"] is None and result["n_pairs"] == 0
    assert "fixture failure" in (tmp_path / "source_failures.json").read_text()
    assert len(list((tmp_path / "figures").glob("*.png"))) == 5


def test_release_date_alone_does_not_become_time(calendar):
    candidates = pd.DataFrame([{"event_id": "a", "event_session": "2024-05-01"}])
    reviews = pd.DataFrame([{"event_id": "a", "reviewed": True, "first_public_release_verified": True,
                             "evidence_url": "https://issuer.example/release", "release_date": "2024-05-01"}])
    result = apply_release_reviews(candidates, reviews, calendar)
    assert not result.clean_release_timing.iloc[0]
    assert result.release_timing_uncertain.iloc[0]


def test_primary_missing_prices_not_replaced(calendar, settings):
    candidates = pd.DataFrame([{"event_id": "a", "ticker": "A", "event_session": "2024-05-01",
                                "timestamp_verified": True, "historical_identity_verified": True}])
    ledger, observations, windows = calculate_events(candidates, {}, calendar, settings)
    assert observations.empty and not windows
    assert ledger.primary_reason.iloc[0] == "missing_stock_or_market_prices"

