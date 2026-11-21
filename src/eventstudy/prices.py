"""Explicit adjusted prices; missing sessions remain missing, including adjacent returns."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .sec_client import SourceError
from .storage import sha256, utc_now, write_json


def normalize_prices(frame):
    if isinstance(frame.columns, pd.MultiIndex):
        if len(frame.columns.get_level_values(-1).unique()) != 1:
            raise SourceError("multiple_tickers_in_single_price_frame")
        frame = frame.copy()
        frame.columns = frame.columns.get_level_values(0)
    if "Adj Close" not in frame:
        raise SourceError("missing_adjusted_close_no_unadjusted_fallback")
    if frame.index.has_duplicates:
        raise SourceError("duplicate_price_sessions")
    result = frame.copy()
    index = pd.to_datetime(result.index)
    if index.tz is not None:
        index = index.tz_convert("America/New_York").tz_localize(None)
    result.index = index.normalize()
    result.index.name = "session"
    if result.index.has_duplicates:
        raise SourceError("duplicate_normalized_price_sessions")
    return result.sort_index()


def adjusted_returns(frame, sessions):
    frame = normalize_prices(frame)
    price = pd.to_numeric(frame["Adj Close"], errors="coerce").reindex(sessions)
    price = price.where(np.isfinite(price) & (price > 0))
    returns = price.pct_change(fill_method=None)
    returns.name = "return"
    return returns


def price_quality(frame, sessions, ticker):
    frame = normalize_prices(frame)
    price = pd.to_numeric(frame["Adj Close"], errors="coerce").reindex(sessions)
    returns = adjusted_returns(frame, sessions)
    records = []
    for session in sessions:
        reasons = []
        p = price.loc[session]
        if pd.isna(p):
            reasons.append("missing_adjusted_price")
        elif not np.isfinite(p) or p <= 0:
            reasons.append("invalid_adjusted_price")
        if pd.notna(returns.loc[session]) and abs(returns.loc[session]) > .4:
            reasons.append("extreme_adjusted_return_review")
        if session in frame.index and "Stock Splits" in frame and frame.at[session, "Stock Splits"] != 0:
            reasons.append("corporate_split_reported")
        for reason in reasons:
            records.append({"ticker": ticker, "session": str(session.date()), "issue": reason,
                            "adj_close": p, "adjusted_return": returns.loc[session]})
    return records


def fetch_prices(ticker, start, end, cache, offline=False, downloader=None):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{ticker}_{start}_{end}.csv"
    meta_path = path.with_name(path.name + ".meta.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if sha256(path.read_bytes()) != meta["sha256"]:
            raise SourceError(f"corrupt_price_snapshot:{ticker}")
        return normalize_prices(pd.read_csv(path, index_col=0, parse_dates=True)), meta
    if offline:
        raise SourceError(f"offline_price_cache_miss:{ticker}")
    if downloader is None:
        import yfinance as yf
        downloader = yf.download
    frame = downloader(ticker, start=start, end=end, interval="1d", auto_adjust=False,
                       back_adjust=False, actions=True, repair=False, keepna=True,
                       progress=False, threads=False, multi_level_index=False, timeout=25)
    if frame is None or frame.empty:
        raise SourceError(f"empty_vendor_price_response:{ticker}")
    frame = normalize_prices(frame)
    payload = frame.to_csv(float_format="%.15g", lineterminator="\n").encode()
    path.write_bytes(payload)
    meta = {"ticker": ticker, "vendor": "Yahoo Finance via yfinance", "retrieved_at": utc_now(),
            "sha256": sha256(payload), "rows": len(frame), "start": start, "end_exclusive": end,
            "auto_adjust": False, "back_adjust": False, "repair": False, "actions": True,
            "interval": "1d", "return_field": "Adj Close"}
    write_json(meta_path, meta)
    # Use the serialized snapshot even on the first run, making cached and first-run results identical.
    return normalize_prices(pd.read_csv(path, index_col=0, parse_dates=True)), meta

