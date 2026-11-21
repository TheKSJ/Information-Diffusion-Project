"""Predetermined control screening and deterministic same-issuer/sign matching."""
import numpy as np
import pandas as pd

from .market_model import ObservationError, observation


def conservative_filing_positions(row, calendar):
    if row.get("event_session") and pd.notna(row.get("event_session")):
        return [calendar.position(row["event_session"])]
    date = row.get("filingDate")
    if not date or pd.isna(date):
        return []
    p = int(calendar.sessions.searchsorted(pd.Timestamp(date)))
    return [p, p + 1]  # Unverified clock: protect same and next regular session.


def control_pool(ticker, stock, market, calendar, filings, candidates, settings,
                 metadata_complete=True, model="market_model", threshold=None):
    threshold = settings["initial_threshold"] if threshold is None else threshold
    earnings = sorted({p for row in candidates for p in conservative_filing_positions(row, calendar)})
    important = {"8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A"}
    sec = sorted({p for row in filings if row.get("form") in important
                  for p in conservative_filing_positions(row, calendar)})
    earnings, sec = np.asarray(earnings, dtype=int), np.asarray(sec, dtype=int)
    accepted, ledger, windows = [], [], []
    first, last = settings["observation"]
    buffer = settings["control_sec_buffer"]
    for session in calendar.sessions:
        date = str(session.date())
        if not settings["start"] <= date <= settings["end"]:
            continue
        p = calendar.position(session)
        row = {"control_id": f"control_{ticker}_{date}", "ticker": ticker, "event_session": date,
               "year": session.year, "primary_reason": "", "metadata_complete": metadata_complete}
        if not metadata_complete:
            row["primary_reason"] = "incomplete_SEC_screening"
        elif np.any((earnings >= p + first - last) & (earnings <= p + last - first)):
            row["primary_reason"] = "earnings_window_overlap"
        elif np.any((sec >= p + first - buffer) & (sec <= p + last + buffer)):
            row["primary_reason"] = "nearby_important_SEC_filing"
        else:
            try:
                stats, long = observation(stock, market, calendar, session, settings, model)
                row.update(stats)
                if abs(row["ar0"]) < threshold:
                    row["primary_reason"] = "below_initial_threshold"
                else:
                    accepted.append(dict(row))
                    long["control_id"] = row["control_id"]
                    long["ticker"] = ticker
                    windows.append(long)
            except ObservationError as exc:
                row.update(primary_reason=exc.reason, **exc.details)
        ledger.append(row)
    return pd.DataFrame(accepted), pd.DataFrame(ledger), windows


def match_controls(events, controls, calendar, observation_window=(-5, 10)):
    pairs, unmatched = [], []
    if events.empty:
        return pd.DataFrame(), pd.DataFrame(columns=["event_id", "reason"])
    controls = controls.copy()
    used, used_positions = set(), {}
    for _, event in events.sort_values(["event_session", "ticker", "event_id"]).iterrows():
        if controls.empty:
            unmatched.append({"event_id": event.event_id, "reason": "no_eligible_controls"})
            continue
        available = controls[(controls.ticker == event.ticker)
                             & (controls.initial_sign == event.initial_sign)
                             & ~controls.control_id.isin(used)].copy()
        if available.empty:
            unmatched.append({"event_id": event.event_id, "reason": "no_same_issuer_sign_control"})
            continue
        event_date = pd.Timestamp(event.event_session)
        available["year_gap"] = (pd.to_datetime(available.event_session).dt.year - event_date.year).abs()
        available["magnitude_gap"] = (available.ar0.abs() - abs(event.ar0)).abs()
        available["volatility_gap"] = (available.residual_std - event.residual_std).abs().fillna(np.inf)
        available["days_gap"] = (pd.to_datetime(available.event_session) - event_date).abs().dt.days
        available = available.sort_values(["year_gap", "magnitude_gap", "volatility_gap", "days_gap", "control_id"])
        chosen = None
        separation = observation_window[1] - observation_window[0]
        for _, control in available.iterrows():
            pos = calendar.position(control.event_session)
            if all(abs(pos - x) > separation for x in used_positions.get(event.ticker, [])):
                chosen = control
                break
        if chosen is None:
            unmatched.append({"event_id": event.event_id, "reason": "remaining_control_windows_overlap"})
            continue
        control = chosen
        used.add(control.control_id)
        used_positions.setdefault(event.ticker, []).append(calendar.position(control.event_session))
        pairs.append({"event_id": event.event_id, "control_id": control.control_id, "ticker": event.ticker,
                      "event_session": event.event_session, "control_session": control.event_session,
                      "event_quarter": str(event_date.to_period("Q")),
                      "control_quarter": str(pd.Timestamp(control.event_session).to_period("Q")),
                      "event_signed_post_car": event.signed_post_car,
                      "control_signed_post_car": control.signed_post_car,
                      "difference": event.signed_post_car - control.signed_post_car,
                      "event_ar0": event.ar0, "control_ar0": control.ar0,
                      "year_gap": control.year_gap, "magnitude_gap": control.magnitude_gap,
                      "volatility_gap": control.volatility_gap,
                      "year_fallback": bool(control.year_gap > 0)})
    return pd.DataFrame(pairs), pd.DataFrame(unmatched)

