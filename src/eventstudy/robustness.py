"""Prespecified sensitivities; never a replacement primary specification."""
import pandas as pd

from .controls import control_pool, match_controls
from .inference import infer
from .pipeline import calculate_events, records, truth


def robustness_results(config, observations, controls, returns, calendar, filings, candidates, coverage):
    s = config["study"]
    results = []
    filings_by, candidates_by = {}, {}
    for row in records(filings):
        filings_by.setdefault(row["ticker"], []).append(row)
    for row in records(candidates):
        candidates_by.setdefault(row["ticker"], []).append(row)

    def append(name, events, pool):
        pairs, unmatched = match_controls(events, pool, calendar)
        result = infer(pairs, s["seed"], s["bootstrap_draws"], s["minimum_clusters"])
        result.update(specification=name, classification="prespecified exploratory sensitivity",
                      unmatched=len(unmatched), multiple_testing="No confirmatory interpretation; no headline selection")
        results.append(result)

    for threshold in s["robustness_thresholds"]:
        ev = observations[observations.ar0.abs() >= threshold] if not observations.empty else observations
        pool = controls[controls.ar0.abs() >= threshold] if not controls.empty else controls
        append(f"threshold_{threshold:g}", ev, pool)
    if not observations.empty:
        large = observations[observations.ar0.abs() >= s["initial_threshold"]]
        less_confounded = large[(~large.overlapping_event_window.map(truth))
                                & large.other_economic_items.fillna("").eq("")]
    else:
        less_confounded = observations
    primary_pool = controls[controls.ar0.abs() >= s["initial_threshold"]] if not controls.empty else controls
    append("nonoverlap_no_other_economic_items", less_confounded, primary_pool)
    verified_release = observations[observations.clean_release_timing.map(truth)] if not observations.empty else observations
    if len(verified_release) >= s["clean_timing_minimum"]:
        append("independently_verified_first_release_same_session",
               verified_release[verified_release.ar0.abs() >= s["initial_threshold"]], primary_pool)
    else:
        results.append({"specification": "independently_verified_first_release_same_session",
                        "status": "unavailable_insufficient_independent_release_timing_evidence",
                        "verified_available": len(verified_release), "required": s["clean_timing_minimum"]})
    if returns and not candidates.empty:
        _, alt_events, _ = calculate_events(candidates, returns, calendar, s, "market_adjusted")
        pools = []
        for ticker in sorted(candidates.ticker.unique()):
            if ticker not in returns or s["market"] not in returns:
                continue
            cv = coverage.get(ticker, {})
            pool, _, _ = control_pool(ticker, returns[ticker], returns[s["market"]], calendar,
                                     filings_by.get(ticker, []), candidates_by.get(ticker, []), s,
                                     metadata_complete=truth(cv.get("SEC_screening_complete")) and truth(cv.get("historical_identity_verified")),
                                     model="market_adjusted")
            if not pool.empty:
                pools.append(pool)
        alt_pool = pd.concat(pools, ignore_index=True) if pools else pd.DataFrame()
        append("simple_market_adjusted", alt_events[alt_events.ar0.abs() >= s["initial_threshold"]]
               if not alt_events.empty else alt_events, alt_pool)
    else:
        append("simple_market_adjusted", pd.DataFrame(), pd.DataFrame())
    return results

