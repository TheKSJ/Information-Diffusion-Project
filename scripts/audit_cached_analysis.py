"""Independent closed-form numerical audit of three genuine cached-source observations."""
import json
import sys
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from eventstudy.events import visible_text
from eventstudy.storage import load_config, sha256, write_json


def audit(root):
    config = load_config(root / "configs/study.yaml")
    processed = root / config["paths"]["data"] / "processed"
    prices_path = root / config["paths"]["data"] / "raw/prices"
    settings = config["study"]
    events = pd.read_csv(processed / "analytical_events.csv")
    pairs = pd.read_csv(processed / "matched_pairs.csv")
    long = pd.read_csv(processed / "event_abnormal_returns.csv")
    control_long = pd.read_csv(processed / "control_abnormal_returns.csv")
    calendar = xcals.get_calendar("XNYS", start="2020-01-01", end="2026-12-31")
    sessions = calendar.sessions.tz_localize(None)
    def price(ticker):
        frame = pd.read_csv(prices_path / f"{ticker}_{settings['price_start']}_{settings['price_end_exclusive']}.csv",
                            index_col=0, parse_dates=True).reindex(sessions)
        return frame
    spy = price("SPY")["Adj Close"].pct_change(fill_method=None)
    chosen = []
    for ticker in ["AAPL", "JPM", "CAT"]:
        subset = events[events.ticker == ticker].sort_values("event_session")
        if len(subset):
            chosen.append(subset.iloc[0])
    for _, row in events.sort_values(["ticker", "event_session"]).iterrows():
        if len(chosen) >= 3:
            break
        if row.event_id not in {e.event_id for e in chosen}:
            chosen.append(row)
    cases = []
    for event in chosen:
        frame = price(event.ticker)
        stock = frame["Adj Close"].pct_change(fill_method=None)
        p = sessions.get_loc(pd.Timestamp(event.event_session))
        est = sessions[p - 120:p - 20]  # Python exclusive end gives exactly -120 through -21.
        x, y = spy.loc[est].to_numpy(), stock.loc[est].to_numpy()
        beta = float(np.sum((x - x.mean()) * (y - y.mean())) / np.sum((x - x.mean())**2))
        alpha = float(y.mean() - beta * x.mean())
        dates = sessions[p - 5:p + 11]
        ar = stock.loc[dates].to_numpy() - alpha - beta * spy.loc[dates].to_numpy()
        post = float(ar[6:11].sum())
        signed = float(np.sign(ar[5]) * post)
        source = root / "data/raw/sec" / (sha256(event.timestamp_source.encode()) + ".body")
        index_text = visible_text(source.read_text(encoding="utf-8", errors="replace"))
        offset = index_text.find("Accepted")
        residuals = {"alpha": alpha - event.alpha, "beta": beta - event.beta,
                     "ar0": ar[5] - event.ar0, "post_car": post - event.car_post_1_5,
                     "signed_post_car": signed - event.signed_post_car}
        assert max(abs(v) for v in residuals.values()) < 1e-9, residuals
        cases.append({"event_id": event.event_id, "ticker": event.ticker, "event_session": event.event_session,
                      "estimation_first": str(est[0].date()), "estimation_last": str(est[-1].date()), "n": len(est),
                      "stock_adj_close_previous": frame["Adj Close"].iloc[p - 1],
                      "stock_adj_close_day_zero": frame["Adj Close"].iloc[p],
                      "stock_adjusted_return_day_zero": stock.iloc[p],
                      "stock_unadjusted_return_day_zero": frame.Close.iloc[p] / frame.Close.iloc[p - 1] - 1,
                      "spy_return_day_zero": spy.iloc[p], "alpha_closed_form": alpha, "beta_closed_form": beta,
                      "ar0_recomputed": ar[5], "post_ar_1_5": ar[6:11].tolist(), "post_car_recomputed": post,
                      "signed_post_car_recomputed": signed, "arithmetic_residuals": residuals,
                      "index_accepted_evidence": index_text[max(offset - 30, 0):offset + 100],
                      "raw_api_timestamp": event.raw_acceptance_timestamp,
                      "verified_timestamp": event.verified_acceptance_timestamp, "source_url": event.source_url})
    pair_residuals = []
    assert not pairs.control_id.duplicated().any()
    for _, pair in pairs.iterrows():
        event_ar = long[(long.event_id == pair.event_id) & long.offset.between(1, 5)].abnormal_return
        control_ar = control_long[(control_long.control_id == pair.control_id) & control_long.offset.between(1, 5)].abnormal_return
        assert len(event_ar) == len(control_ar) == 5
        difference = np.sign(pair.event_ar0) * event_ar.sum() - np.sign(pair.control_ar0) * control_ar.sum()
        pair_residuals.append(float(difference - pair.difference))
    assert max(map(abs, pair_residuals), default=0) < 1e-9
    manifest = json.loads((processed / "run_manifest.json").read_text())
    hash_failures = []
    for entry in manifest["source_snapshots"]:
        path = root / "data/raw" / entry["path"]
        if sha256(path.read_bytes()) != entry["sha256"]:
            hash_failures.append(entry["path"])
    assert not hash_failures
    output = {"data_kind": "GENUINE CACHED SOURCES", "worked_cases": cases,
              "all_pairs_checked": len(pairs), "control_reuse": 0,
              "max_pair_arithmetic_residual": max(map(abs, pair_residuals), default=0),
              "source_snapshots_checked": len(manifest["source_snapshots"]), "hash_failures": hash_failures}
    write_json(root / "reports/manual_numerical_audit.json", output)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    audit(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])

