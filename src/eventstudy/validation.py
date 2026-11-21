"""Preflight invariants and output schema checks."""
from pathlib import Path

import pandas as pd

FIXED_TICKERS = set("AAPL MSFT NVDA INTC ORCL CSCO JPM BAC GS MS WFC C WMT COST HD MCD KO PEP JNJ PFE MRK ABBV UNH BMY CAT DE HON UPS LMT UNP".split())


def validate_config(config):
    s = config["study"]
    if s["estimation"] != [-120, -21] or s["min_estimation"] != 100:
        raise ValueError("Primary estimation specification changed; version design explicitly first")
    if s["observation"] != [-5, 10] or s["primary_post"] != [1, 5]:
        raise ValueError("Primary observation/post specification changed")
    if s["initial_threshold"] != .02:
        raise ValueError("Primary threshold changed; use prespecified robustness output")
    if s["start"] != "2021-01-01" or s["end"] != "2025-12-31":
        raise ValueError("Primary study dates changed")
    if not 0 < config["sec"]["requests_per_second"] <= 2:
        raise ValueError("SEC request rate exceeds project policy")
    if s["bootstrap_draws"] < 100 or s["minimum_clusters"] < 2:
        raise ValueError("invalid_inference_settings")
    universe = pd.read_csv(Path(config["root"]) / config["paths"]["universe"])
    if len(universe) != 30 or set(universe.ticker) != FIXED_TICKERS or universe.ticker.duplicated().any():
        raise ValueError("Fixed 30-security universe changed")
    if universe.cik.isna().any() or (universe.cik <= 0).any():
        raise ValueError("invalid_seed_CIK")
    return universe


def validate_pairs(pairs):
    required = {"event_id", "control_id", "ticker", "event_session", "control_session",
                "difference", "event_signed_post_car", "control_signed_post_car"}
    if pairs.empty:
        return
    if not required.issubset(pairs.columns):
        raise ValueError("incomplete_pair_schema")
    if pairs.control_id.duplicated().any() or pairs.event_id.duplicated().any():
        raise ValueError("duplicate_pair_members")
    error = (pairs.difference - pairs.event_signed_post_car + pairs.control_signed_post_car).abs()
    if (error > 1e-12).any():
        raise ValueError("pair_difference_arithmetic_error")

