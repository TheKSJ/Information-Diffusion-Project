import json

import numpy as np
import pandas as pd
import pytest
import requests
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_cluster

from eventstudy.cli import main
from eventstudy.controls import match_controls
from eventstudy.inference import infer
from eventstudy.sec_client import SECClient, SourceError
from test_controls_inference import simulated_pairs
from test_sec import Response, Session, UA


def test_cluster_variance_matches_independent_statsmodels():
    pairs = simulated_pairs(.004)
    result = infer(pairs)
    model = sm.OLS(pairs.difference, np.ones((len(pairs), 1))).fit()
    reference = cov_cluster(model, pairs.ticker, use_correction=True)
    assert result["issuer_cluster"]["se_pp"] == pytest.approx(100 * np.sqrt(reference[0, 0]), rel=1e-12)


def test_connection_failure_retried_without_invented_records(tmp_path):
    session = Session([requests.ConnectionError("synthetic unavailable")] * 3)
    client = SECClient(tmp_path, UA, session=session, retries=2, sleep=lambda _: None)
    with pytest.raises(SourceError, match="ConnectionError"):
        client.json("https://data.sec.gov/failure")
    assert len(session.calls) == 3 and not list(tmp_path.glob("*.body"))


def test_global_limiter_across_client_instances(tmp_path):
    SECClient._last_request = 0
    clock = [100.]
    waits = []
    def sleep(delay):
        waits.append(delay)
        clock[0] += delay
    for i in range(3):
        client = SECClient(tmp_path, UA, session=Session([Response({})]), sleep=sleep, clock=lambda: clock[0])
        client.get(f"https://data.sec.gov/{i}")
    assert waits == pytest.approx([.5, .5])
    with pytest.raises(ValueError):
        SECClient(tmp_path, UA, rate=3)


def test_same_year_priority_and_explicit_year_fallback(calendar):
    event = pd.DataFrame([{"event_id": "e", "ticker": "A", "event_session": "2023-06-01",
                           "ar0": .03, "initial_sign": 1, "residual_std": .01, "signed_post_car": .01}])
    controls = pd.DataFrame([{"control_id": "same", "ticker": "A", "event_session": "2023-02-01",
                              "ar0": .06, "initial_sign": 1, "residual_std": .01, "signed_post_car": .01},
                             {"control_id": "old", "ticker": "A", "event_session": "2022-02-01",
                              "ar0": .03, "initial_sign": 1, "residual_std": .01, "signed_post_car": .01}])
    pairs, _ = match_controls(event, controls, calendar)
    assert pairs.control_id.iloc[0] == "same" and not pairs.year_fallback.iloc[0]
    pairs, _ = match_controls(event, controls[controls.control_id == "old"], calendar)
    assert pairs.control_id.iloc[0] == "old" and pairs.year_fallback.iloc[0]
    assert pairs.year_gap.iloc[0] == 1


def test_partial_fetch_cli_return_code(monkeypatch, tmp_path):
    import eventstudy.collection
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(eventstudy.collection, "fetch", lambda *args: {"failed_operations": 1, "snapshots": []})
    assert main(["fetch", "--config", str(root / "configs/study.yaml")]) == 2


def test_committed_synthetic_json_fixture():
    from pathlib import Path
    from eventstudy.sec_client import reconstruct_arrays
    from eventstudy.events import classify_filing
    value = json.loads((Path(__file__).parent / "fixtures/submissions_synthetic.json").read_text(encoding="utf-8"))
    assert "SYNTHETIC" in value["fixture_label"]
    rows = reconstruct_arrays(value["filings"]["recent"])
    assert [classify_filing(row) for row in rows] == ["candidate", "amendment", "unresolved_items"]

