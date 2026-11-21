"""Cached-input analysis. Failure ledgers are first-class outputs, never synthetic fallback."""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .calendar import TradingCalendar
from .controls import conservative_filing_positions, control_pool, match_controls
from .inference import infer
from .market_model import ObservationError, observation
from .prices import adjusted_returns, fetch_prices, price_quality
from .storage import environment, read_csv, sha256, snapshot_manifest, write_csv, write_json
from .validation import validate_config, validate_pairs

LOG = logging.getLogger(__name__)


def save_schemas(output):
    schemas = {}
    for path in sorted(Path(output).glob("*.csv")):
        frame = read_csv(path)
        schemas[path.name] = {"rows": len(frame), "columns": {name: str(dtype) for name, dtype in frame.dtypes.items()},
                              "return_units": "decimal unless column ends _percent or _pp"}
    write_json(Path(output) / "dataset_schema.json", schemas)


def verify_fingerprints(root, fingerprints):
    changed = [name for name, digest in fingerprints.items()
               if not (Path(root) / name).exists() or sha256((Path(root) / name).read_bytes()) != digest]
    if changed:
        raise ValueError("Inputs or implementation changed during run; discard this pass and rerun: " + ", ".join(changed))


def truth(value):
    return str(value).lower() in {"true", "1", "yes"}


def records(frame):
    return frame.replace({np.nan: None}).to_dict("records")


def apply_release_reviews(candidates, reviews, calendar):
    reviewed = {r["event_id"]: r for r in records(reviews)} if not reviews.empty else {}
    output = []
    for original in records(candidates):
        row = dict(original)
        row["clean_release_timing"] = False
        row["release_timing_uncertain"] = True
        row["release_may_precede_filing"] = "unknown"
        row["concurrent_disclosed_items_flag"] = bool(row.get("other_economic_items"))
        row["retrospective_realized_return_selection"] = True
        row["nonstandard_disclosure_flag"] = False
        row["disclosure_reviewed"] = False
        row["first_public_release_verified"] = False
        review = reviewed.get(row["event_id"])
        if review:
            row["release_review_notes"] = review.get("notes")
            row["release_date"] = review.get("release_date")
            row["release_reviewer"] = review.get("reviewer")
            row["disclosure_reviewed"] = truth(review.get("reviewed"))
            row["release_evidence_url"] = review.get("evidence_url")
            row["release_may_precede_filing"] = review.get("release_may_precede_filing")
            row["nonstandard_disclosure_flag"] = truth(review.get("nonstandard_disclosure_flag"))
            row["disclosure_review_notes"] = review.get("concurrent_news_notes")
            if (truth(review.get("reviewed")) and truth(review.get("first_public_release_verified"))
                    and review.get("evidence_url") and review.get("release_timestamp")):
                try:
                    stamp = pd.Timestamp(review["release_timestamp"])
                    aligned = calendar.align(stamp)
                    row["release_timestamp"] = stamp.isoformat()
                    row["release_session"] = aligned["event_session"]
                    row["release_timing_uncertain"] = False
                    row["first_public_release_verified"] = True
                    row["clean_release_timing"] = aligned["event_session"] == row.get("event_session")
                except (ValueError, TypeError):
                    row["release_review_error"] = "timestamp_timezone_or_calendar_invalid"
        output.append(row)
    return pd.DataFrame(output)


def calculate_events(candidates, returns, calendar, settings, model="market_model"):
    ledger, observations, windows = [], [], []
    seen = set()
    ordered = candidates.sort_values("event_id") if not candidates.empty else candidates
    positions = {}
    for row in records(candidates):
        positions.setdefault(row["ticker"], []).extend(conservative_filing_positions(row, calendar))
    for row in records(ordered):
        row = dict(row)
        row["primary_reason"] = row.get("primary_reason") or ""
        row["overlapping_event_window"] = False
        if not truth(row.get("timestamp_verified")):
            row["primary_reason"] = "timestamp_unverified"
        elif not settings["start"] <= row.get("event_session", "") <= settings["end"]:
            row["primary_reason"] = "outside_research_sessions"
        elif not truth(row.get("historical_identity_verified")):
            row["primary_reason"] = "historical_identity_unverified"
        elif row["ticker"] not in returns or settings["market"] not in returns:
            row["primary_reason"] = "missing_stock_or_market_prices"
        else:
            session = row["event_session"]
            p = calendar.position(session)
            row["overlapping_event_window"] = sum(abs(p - x) <= 15 for x in positions[row["ticker"]]) > 1
            try:
                calculated, long = observation(returns[row["ticker"]], returns[settings["market"]],
                                               calendar, session, settings, model)
                row.update(calculated)
                key = (row["ticker"], session)
                if key in seen:
                    row["primary_reason"] = "duplicate_ticker_session"
                else:
                    seen.add(key)
                    row["above_primary_threshold"] = abs(row["ar0"]) >= settings["initial_threshold"]
                    observations.append(dict(row))
                    long["event_id"], long["ticker"] = row["event_id"], row["ticker"]
                    windows.append(long)
                    if not row["above_primary_threshold"]:
                        row["primary_reason"] = "below_initial_threshold"
            except ObservationError as exc:
                row.update(primary_reason=exc.reason, **exc.details)
        ledger.append(row)
    return pd.DataFrame(ledger), pd.DataFrame(observations), windows


def analyze_inputs(config, filings, candidates, coverage, price_frames, failures, output,
                   timing_reviews=None, synthetic=False, run_robustness=True):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    settings = config["study"]
    calendar = TradingCalendar()
    candidates = apply_release_reviews(candidates, timing_reviews if timing_reviews is not None else pd.DataFrame(), calendar)
    returns, price_rows, price_issues = {}, [], []
    required_sessions = calendar.sessions[(calendar.sessions >= settings["price_start"])
                                          & (calendar.sessions < settings["price_end_exclusive"])]
    for ticker, frame in sorted(price_frames.items()):
        returns[ticker] = adjusted_returns(frame, calendar.sessions)
        normalized = frame.reindex(required_sessions)
        rows = pd.DataFrame({"ticker": ticker, "session": required_sessions.strftime("%Y-%m-%d"),
                             "adj_close": normalized["Adj Close"].to_numpy(),
                             "return": returns[ticker].reindex(required_sessions).to_numpy()})
        if "Close" in normalized:
            rows["unadjusted_close"] = normalized["Close"].to_numpy()
        for name in ["Dividends", "Stock Splits"]:
            if name in normalized:
                rows[name.lower().replace(" ", "_")] = normalized[name].to_numpy()
        price_rows.append(rows)
        price_issues.extend(price_quality(frame, required_sessions, ticker))
    ledger, observations, event_windows = calculate_events(candidates, returns, calendar, settings)
    all_controls, control_ledgers, control_windows = [], [], []
    coverage_by = {r["ticker"]: r for r in records(coverage)}
    filings_by = {}
    for row in records(filings):
        filings_by.setdefault(row["ticker"], []).append(row)
    candidates_by = {}
    for row in records(candidates):
        candidates_by.setdefault(row["ticker"], []).append(row)
    tickers = sorted(candidates.ticker.unique()) if not candidates.empty else []
    for ticker in tickers:
        if ticker not in returns or settings["market"] not in returns:
            continue
        issuer_coverage = coverage_by.get(ticker, {})
        complete = truth(issuer_coverage.get("SEC_screening_complete")) and truth(
            issuer_coverage.get("historical_identity_verified"))
        LOG.warning("Computing screened pseudo-dates for %s", ticker)
        controls, screening, windows = control_pool(
            ticker, returns[ticker], returns[settings["market"]], calendar,
            filings_by.get(ticker, []), candidates_by.get(ticker, []), settings,
            metadata_complete=complete, threshold=min(settings["robustness_thresholds"]))
        if not controls.empty:
            all_controls.append(controls)
        control_ledgers.append(screening)
        control_windows.extend(windows)
    controls = pd.concat(all_controls, ignore_index=True) if all_controls else pd.DataFrame()
    qualifying = observations[observations.ar0.abs() >= settings["initial_threshold"]].copy() if not observations.empty else pd.DataFrame()
    primary_controls = controls[controls.ar0.abs() >= settings["initial_threshold"]] if not controls.empty else controls
    pairs, unmatched = match_controls(qualifying, primary_controls, calendar)
    validate_pairs(pairs)
    primary = infer(pairs, settings["seed"], settings["bootstrap_draws"], settings["minimum_clusters"])
    primary["data_kind"] = "SYNTHETIC DEMONSTRATION — NOT EMPIRICAL FINDINGS" if synthetic else "genuine cached sources"
    write_json(output / "primary_inference.json", primary)
    write_csv(output / "event_ledger.csv", ledger, ["event_id", "ticker", "primary_reason"])
    write_csv(output / "analytical_events.csv", observations, ["event_id", "ticker", "event_session", "ar0", "signed_post_car"])
    write_csv(output / "included_events.csv", qualifying, ["event_id", "ticker", "event_session", "ar0", "signed_post_car"])
    excluded = ledger[ledger.primary_reason.fillna("") != ""] if not ledger.empty else ledger
    write_csv(output / "excluded_events.csv", excluded, ["event_id", "ticker", "primary_reason"])
    write_csv(output / "matched_pairs.csv", pairs, ["event_id", "control_id", "ticker", "difference"])
    matching_diagnostics = {"matched": len(pairs), "unmatched": len(unmatched),
                            "rule": "no magnitude caliper; gaps disclosed, not relaxed or hidden"}
    if not pairs.empty:
        matching_diagnostics.update({"year_fallback_count": int(pairs.year_fallback.sum()),
                                     "magnitude_gap_median_pp": float(pairs.magnitude_gap.median() * 100),
                                     "magnitude_gap_max_pp": float(pairs.magnitude_gap.max() * 100),
                                     "magnitude_gap_p95_pp": float(pairs.magnitude_gap.quantile(.95) * 100),
                                     "residual_volatility_gap_median_pp": float(pairs.volatility_gap.median() * 100),
                                     "pairs_by_issuer": pairs.groupby("ticker").size().to_dict()})
    write_json(output / "matching_diagnostics.json", matching_diagnostics)
    write_csv(output / "unmatched_events.csv", unmatched, ["event_id", "reason"])
    write_csv(output / "control_candidates.csv", controls, ["control_id", "ticker", "event_session", "ar0", "signed_post_car"])
    write_csv(output / "control_screening.csv", pd.concat(control_ledgers, ignore_index=True) if control_ledgers else [],
              ["control_id", "ticker", "event_session", "primary_reason"])
    write_csv(output / "event_abnormal_returns.csv", pd.concat(event_windows, ignore_index=True) if event_windows else [],
              ["event_id", "ticker", "offset", "session", "stock_return", "market_return", "expected_return", "abnormal_return"])
    write_csv(output / "control_abnormal_returns.csv", pd.concat(control_windows, ignore_index=True) if control_windows else [],
              ["control_id", "ticker", "offset", "session", "abnormal_return"])
    write_csv(output / "adjusted_prices_returns.csv", pd.concat(price_rows, ignore_index=True) if price_rows else [],
              ["ticker", "session", "adj_close", "return"])
    write_csv(output / "price_quality.csv", price_issues, ["ticker", "session", "issue", "adj_close", "adjusted_return"])
    write_csv(output / "verified_events.csv", candidates[candidates.timestamp_verified.map(truth)] if not candidates.empty else [],
              ["event_id", "ticker", "verified_acceptance_timestamp", "timestamp_source", "event_session"])
    timestamp_columns = ["event_id", "ticker", "raw_acceptance_timestamp", "verified_acceptance_timestamp",
                         "timestamp_source", "api_minus_verified_seconds", "timestamp_discrepancy",
                         "discrepancy_changes_session", "event_session", "timing_class", "timestamp_verified"]
    write_csv(output / "timestamp_ledger.csv", candidates.reindex(columns=timestamp_columns))
    waterfall = ledger.primary_reason.fillna("").replace("", "included_primary").value_counts().sort_index().to_dict() if not ledger.empty else {}
    write_json(output / "exclusion_waterfall.json", {"candidate_total": len(ledger), "mutually_exclusive": waterfall,
                                                    "qualifying_unmatched": len(unmatched)})
    if not ledger.empty:
        issuer_year = ledger.assign(year=pd.to_datetime(ledger.get("filingDate"), errors="coerce").dt.year)
        quality = issuer_year.groupby(["ticker", "year", "primary_reason"], dropna=False).size().reset_index(name="count")
    else:
        quality = pd.DataFrame(columns=["ticker", "year", "primary_reason", "count"])
    write_csv(output / "coverage_by_issuer_year.csv", quality)
    write_json(output / "source_failures.json", failures)
    robustness = []
    if run_robustness:
        from .robustness import robustness_results
        robustness = robustness_results(config, observations, controls, returns, calendar, filings, candidates, coverage_by)
    write_json(output / "robustness.json", robustness)
    summary = {"status": "analysis_available" if len(pairs) else "no_testable_matched_sample",
               "data_kind": "SYNTHETIC" if synthetic else "LIVE", "companies_requested": len(coverage),
               "companies_with_prices": len(set(price_frames) - {settings["market"]}),
               "filings_discovered": len(filings), "candidate_events": len(candidates),
               "verified_events": int(candidates.timestamp_verified.map(truth).sum()) if not candidates.empty else 0,
               "analytical_events": len(observations), "included_large_move_events": len(qualifying),
               "excluded_events": len(excluded), "matched_controls": len(pairs), "unmatched_events": len(unmatched),
               "price_quality_issues": len(price_issues), "failed_operations": len(failures),
               "release_timing_verified": int(candidates.clean_release_timing.map(truth).sum()) if not candidates.empty else 0}
    if not candidates.empty and "event_session" in candidates:
        in_research = candidates.event_session.fillna("").between(settings["start"], settings["end"])
        summary["verified_candidates_in_research_sessions"] = int((in_research & candidates.timestamp_verified.map(truth)).sum())
    else:
        summary["verified_candidates_in_research_sessions"] = 0
    summary["inference_status"] = primary["issuer_cluster"]["status"]
    write_json(output / "run_summary.json", summary)
    write_json(output / "environment.json", environment())
    from .reporting import render_report
    render_report(output, synthetic=synthetic)
    save_schemas(output)
    return summary


def run(config):
    universe = validate_config(config)
    root = Path(config["root"])
    data = root / config["paths"]["data"]
    interim, output = data / "interim", data / "processed"
    if not (interim / "fetch_manifest.json").exists():
        raise FileNotFoundError("No completed collection manifest; run fetch first (partial collection is permitted)")
    input_paths = [*interim.glob("*.csv"), *interim.glob("*.json"), config["config_path"],
                   root / "docs/research_design.md", root / config["paths"]["universe"],
                   root / config["paths"]["timing_review"], root / "requirements-lock.txt",
                   *sorted((root / "src").rglob("*.py"))]
    fingerprints = {p.relative_to(root).as_posix(): sha256(p.read_bytes()) for p in input_paths}
    source_snapshots = snapshot_manifest(data / "raw")
    if not all(entry["hash_valid"] for entry in source_snapshots):
        raise ValueError("Pinned raw source hash mismatch; no valid reproducible run can be produced")
    filings = read_csv(interim / "all_filings.csv", dtype={"event_id": str})
    candidates = read_csv(interim / "candidate_events.csv", dtype={"event_id": str})
    coverage = read_csv(interim / "issuer_coverage.csv")
    reviews = read_csv(root / config["paths"]["timing_review"])
    failures = json.loads((interim / "source_failures.json").read_text())
    prices = {}
    s = config["study"]
    for ticker in [*universe.ticker, s["market"]]:
        try:
            prices[ticker], _ = fetch_prices(ticker, s["price_start"], s["price_end_exclusive"], data / "raw/prices", offline=True)
        except Exception as exc:
            failures.append({"ticker": ticker, "stage": "cached_prices", "error": str(exc)})
    summary = analyze_inputs(config, filings, candidates, coverage, prices, failures, output, reviews)
    resolved = universe.merge(coverage, on="ticker", how="left", suffixes=("", "_coverage"))
    resolved["configured_mapping_provenance"] = resolved.mapping_provenance
    resolved["mapping_provenance"] = resolved.cik.map(lambda cik: f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    resolved["historical_identity_status"] = resolved.historical_identity_verified.map(
        lambda value: "corroborated_annual_10K_covers_2021_2025" if truth(value) else "unverified_excluded")
    write_csv(output / "universe_resolved.csv", resolved)
    unresolved = read_csv(interim / "unresolved_items.csv")
    write_csv(output / "unresolved_items.csv", unresolved, ["event_id", "ticker", "primary_reason"])
    try:
        verify_fingerprints(root, fingerprints)
    except ValueError:
        summary["status"] = "invalid_inputs_changed_during_run"
        write_json(output / "run_summary.json", summary)
        raise
    provenance = {"configuration": {k: v for k, v in config.items() if k not in {"root", "config_path"}},
                  "config_sha256": sha256(config["config_path"].read_bytes()),
                  "design_sha256": sha256((root / "docs/research_design.md").read_bytes()),
                  "universe_sha256": sha256((root / config["paths"]["universe"]).read_bytes()),
                  "timing_reviews_sha256": sha256((root / config["paths"]["timing_review"]).read_bytes()),
                  "source_snapshots": source_snapshots,
                  "frozen_input_fingerprints": fingerprints,
                  "interim_inputs": {p.name: sha256(p.read_bytes()) for p in sorted(interim.glob("*.csv"))},
                  "source_code": {p.relative_to(root).as_posix(): sha256(p.read_bytes())
                                  for p in sorted((root / "src").rglob("*.py"))},
                  "dependency_lock_sha256": sha256((root / "requirements-lock.txt").read_bytes()),
                  "seed": s["seed"], "bootstrap_draws": s["bootstrap_draws"]}
    write_json(output / "run_manifest.json", provenance)
    save_schemas(output)
    from .reporting import report_from_config
    report_from_config(config)
    return summary

