"""Network-free SYNTHETIC fixture generator. Never used by live fetch/run."""
import copy
from pathlib import Path

import numpy as np
import pandas as pd

from .calendar import TradingCalendar
from .events import normalize_records, verify_candidate
from .pipeline import analyze_inputs
from .sec_client import reconstruct_arrays
from .storage import sha256, write_json

DEMO_SETTINGS = {"start": "2021-01-01", "end": "2025-12-31", "price_start": "2020-06-01",
                 "price_end_exclusive": "2026-03-01", "market": "SPY", "estimation": [-120, -21],
                 "observation": [-5, 10], "primary_post": [1, 5], "min_estimation": 100,
                 "initial_threshold": .02, "robustness_thresholds": [.015, .025], "seed": 20261018,
                 "bootstrap_draws": 5000, "minimum_clusters": 6, "control_sec_buffer": 5,
                 "clean_timing_minimum": 20}


class SyntheticSEC:
    """In-memory authoritative-index fixture; no network client is constructed."""
    def __init__(self, bodies):
        self.bodies = bodies

    def get(self, url):
        content = self.bodies[url].encode()
        return content, {"sha256": sha256(content), "retrieved_at": "SYNTHETIC_FIXED_FIXTURE"}


def synthetic_inputs(n_issuers=6, seed=20261018):
    calendar = TradingCalendar()
    settings = copy.deepcopy(DEMO_SETTINGS)
    rng = np.random.default_rng(seed)
    sessions = calendar.sessions[(calendar.sessions >= settings["price_start"])
                                  & (calendar.sessions < settings["price_end_exclusive"])]
    market = rng.normal(.0002, .009, len(sessions))
    prices = {"SPY": pd.DataFrame({"Adj Close": 100 * np.cumprod(1 + market),
                                   "Close": 100 * np.cumprod(1 + market)}, index=sessions)}
    positions = [i for i in range(190, len(sessions) - 30, 126)
                 if settings["start"] <= str(sessions[i].date()) <= settings["end"]]
    all_filings, candidates, coverage = [], [], []
    for issuer_index in range(n_issuers):
        ticker = f"SYN{issuer_index:02d}"
        issuer = {"ticker": ticker, "cik": 990000 + issuer_index,
                  "company": f"SYNTHETIC ISSUER {issuer_index}", "sector": "Synthetic"}
        stock = .0001 + (1 + issuer_index * .07) * market + rng.normal(0, .003, len(sessions))
        raw_records = []
        bodies = {}
        for event_number, p in enumerate(positions):
            sign = 1 if (event_number + issuer_index) % 2 == 0 else -1
            stock[p] += sign * .035
            stock[p + 1:p + 6] += sign * .0018
            # Non-filing controls have large initial moves, without injected subsequent drift.
            for shift in [32, 62]:
                if p + shift + 10 < len(stock):
                    stock[p + shift] += sign * .035
            date = str(sessions[p].date())
            accession = f"{issuer['cik']:010d}-{sessions[p].year % 100:02d}-{event_number + 1:06d}"
            raw_records.append({"accessionNumber": accession, "form": "8-K", "items": "2.02,9.01",
                                "filingDate": date, "reportDate": date,
                                "acceptanceDateTime": date + "T08:00:00Z",  # Deliberate bad-Z fixture.
                                "primaryDocument": "synthetic.htm"})
        arrays = {key: [r[key] for r in raw_records] for key in raw_records[0]}
        filings = normalize_records(reconstruct_arrays(arrays), issuer)
        for row in filings:
            bodies[row["source_url"]] = f"<div>Accepted</div><div>{row['filingDate']} 08:00:00</div>"
        client = SyntheticSEC(bodies)
        for row in filings:
            verified = verify_candidate(row, client, calendar)
            verified.update(historical_identity_verified=True, SEC_screening_complete=True,
                            fixture_label="SYNTHETIC, not a real SEC filing")
            candidates.append(verified)
        all_filings.extend(filings)
        adjusted = 100 * np.cumprod(1 + stock)
        prices[ticker] = pd.DataFrame({"Adj Close": adjusted, "Close": adjusted * 1.04,
                                       "Dividends": 0., "Stock Splits": 0.}, index=sessions)
        coverage.append({"ticker": ticker, "SEC_screening_complete": True,
                         "historical_identity_verified": True})
    return {"study": settings}, pd.DataFrame(all_filings), pd.DataFrame(candidates), pd.DataFrame(coverage), prices


def run_demo(output, n_issuers=6, run_robustness=True):
    config, filings, candidates, coverage, prices = synthetic_inputs(n_issuers)
    summary = analyze_inputs(config, filings, candidates, coverage, prices, [], output,
                             synthetic=True, run_robustness=run_robustness)
    write_json(Path(output) / "fixture_manifest.json",
               {"data_kind": "SYNTHETIC — NOT REAL EMPIRICAL FINDINGS", "seed": config["study"]["seed"],
                "generator": "eventstudy.demo.synthetic_inputs", "network_requests": 0,
                "configuration": config, "source_filings": len(filings),
                "candidate_ledger_sha256": sha256(candidates.to_csv(index=False).encode())})
    return summary

