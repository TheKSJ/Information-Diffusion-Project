import numpy as np
import pandas as pd
import pytest
from scipy import stats

from eventstudy.controls import control_pool, match_controls
from eventstudy.inference import infer
from eventstudy.validation import validate_pairs


def test_matching_determinism_sign_year_and_nonreuse(calendar):
    events = pd.DataFrame([
        {"event_id": "e2", "ticker": "A", "event_session": "2023-08-01", "ar0": .03,
         "signed_post_car": .02, "initial_sign": 1, "residual_std": .01},
        {"event_id": "e1", "ticker": "A", "event_session": "2023-04-03", "ar0": .04,
         "signed_post_car": .01, "initial_sign": 1, "residual_std": .01}])
    controls = pd.DataFrame([
        {"control_id": "c1", "ticker": "A", "event_session": "2023-02-01", "ar0": .04,
         "signed_post_car": -.01, "initial_sign": 1, "residual_std": .01},
        {"control_id": "c2", "ticker": "A", "event_session": "2023-06-01", "ar0": .03,
         "signed_post_car": .005, "initial_sign": 1, "residual_std": .01},
        {"control_id": "wrong_sign", "ticker": "A", "event_session": "2023-06-15", "ar0": -.03,
         "signed_post_car": 0., "initial_sign": -1, "residual_std": .01}])
    pairs, missing = match_controls(events, controls, calendar)
    repeated, _ = match_controls(events.iloc[::-1], controls.iloc[::-1], calendar)
    pd.testing.assert_frame_equal(pairs, repeated)
    assert pairs.control_id.tolist() == ["c1", "c2"] and missing.empty
    assert pairs.difference.tolist() == pytest.approx([.02, .015])
    assert (pairs.event_ar0 > 0).all() and (pairs.control_ar0 > 0).all()
    validate_pairs(pairs)


def test_no_cross_issuer_fallback_or_overlapping_control_windows(calendar):
    events = pd.DataFrame([{"event_id": f"e{i}", "ticker": "A", "event_session": date,
                            "ar0": .03, "signed_post_car": .01, "initial_sign": 1, "residual_std": .01}
                           for i, date in enumerate(["2023-04-03", "2023-08-01", "2023-10-02"])])
    controls = pd.DataFrame([{"control_id": f"c{i}", "ticker": "A", "event_session": date,
                              "ar0": .03, "signed_post_car": 0., "initial_sign": 1, "residual_std": .01}
                             for i, date in enumerate(["2023-02-01", "2023-02-02"])])
    pairs, missing = match_controls(events, controls, calendar)
    assert len(pairs) == 1 and len(missing) == 2
    assert not pairs.control_id.duplicated().any()


def test_control_screening_uses_full_windows_and_no_missing_metadata(calendar, settings, model_returns):
    stock, market = model_returns
    settings.update(start="2023-05-01", end="2023-05-05")
    filings = [{"form": "10-Q", "filingDate": "2023-05-15"}]
    _, ledger, _ = control_pool("A", stock, market, calendar, filings, [], settings)
    assert ledger.primary_reason.eq("nearby_important_SEC_filing").all()
    _, ledger, _ = control_pool("A", stock, market, calendar, [], [], settings, metadata_complete=False)
    assert ledger.primary_reason.eq("incomplete_SEC_screening").all()


def simulated_pairs(effect=0., seed=23):
    rng = np.random.default_rng(seed)
    rows = []
    for issuer in range(30):
        issuer_effect = rng.normal(0, .006)
        for quarter in range(20):
            control = rng.normal(0, .01)
            difference = effect + issuer_effect + rng.normal(0, .008)
            rows.append({"ticker": f"SYN{issuer}", "difference": difference,
                         "event_signed_post_car": control + difference, "control_signed_post_car": control,
                         "event_quarter": f"{2021 + quarter // 4}Q{quarter % 4 + 1}",
                         "control_quarter": f"{2021 + ((quarter + 1) % 20) // 4}Q{(quarter + 1) % 4 + 1}"})
    return pd.DataFrame(rows)


def test_zero_drift_null_simulation():
    result = infer(simulated_pairs(), draws=5000)
    assert result["issuer_cluster"]["p_one_sided"] > .05
    assert result["issuer_cluster"]["ci95_pp"][0] < 0 < result["issuer_cluster"]["ci95_pp"][1]


@pytest.mark.parametrize("effect,positive", [(.02, True), (-.02, False)])
def test_continuation_and_reversal_simulations(effect, positive):
    result = infer(simulated_pairs(effect), draws=5000)
    assert (result["estimate_pp"] > 0) is positive
    if positive:
        assert result["issuer_cluster"]["p_one_sided"] < .001
    else:
        assert result["issuer_cluster"]["p_one_sided"] > .999


def test_cluster_reproducibility_ci_p_consistency_and_quarters():
    pairs = simulated_pairs(.005)
    a, b = infer(pairs), infer(pairs)
    assert a == b
    result = a["issuer_cluster"]
    expected = stats.t.sf(result["t_stat"], result["df"])
    assert result["p_one_sided"] == pytest.approx(expected)
    assert result["p_two_sided"] == pytest.approx(2 * min(expected, 1 - expected))
    assert (result["ci95_pp"][0] > 0) == (result["p_two_sided"] < .05)
    assert a["n_calendar_quarters"] == 20
    assert a["quarter_cluster_sensitivity"]["clusters"] == 20
    # Both event and control periods count, even when they do not intersect.
    changed = pairs.copy()
    changed["control_quarter"] = changed.control_quarter.str.replace("202", "203")
    assert infer(changed)["n_calendar_quarters"] == 40


def test_too_few_clusters_and_empty_data():
    result = infer(simulated_pairs().query("ticker in ['SYN1', 'SYN2']"))
    assert result["estimate_pp"] is not None
    assert result["issuer_cluster"]["status"] == "insufficient_clusters"
    assert result["issuer_cluster"]["p_one_sided"] is None
    assert infer(pd.DataFrame())["estimate_pp"] is None

