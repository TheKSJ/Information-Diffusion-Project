"""OLS and additive CAR arithmetic with explicitly bounded pre-event estimation."""
import numpy as np
import pandas as pd


class ObservationError(ValueError):
    def __init__(self, reason, **details):
        super().__init__(reason)
        self.reason, self.details = reason, details


def fit_market_model(stock, market):
    y, x = np.asarray(stock, dtype=float), np.asarray(market, dtype=float)
    if len(y) != len(x) or len(x) < 3 or not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ObservationError("invalid_estimation_data")
    if np.var(x) < 1e-12:
        raise ObservationError("degenerate_market_model")
    design = np.column_stack([np.ones(len(x)), x])
    alpha, beta = np.linalg.lstsq(design, y, rcond=None)[0]
    residuals = y - design @ np.array([alpha, beta])
    sse = float(residuals @ residuals)
    tss = float(np.sum((y - y.mean())**2))
    return {"alpha": float(alpha), "beta": float(beta),
            "r_squared": 1 - sse / tss if tss > 0 else None,
            "residual_std": float(np.sqrt(sse / (len(x) - 2)))}


def summarize_ar(ar):
    def car(first, last):
        selected = ar.loc[first:last]
        if len(selected) != last - first + 1 or not np.isfinite(selected).all():
            raise ObservationError("incomplete_CAR_window", first=first, last=last)
        return float(selected.sum())
    ar0 = float(ar.loc[0])
    post = car(1, 5)
    return {"ar0": ar0, "car_pre_5_1": car(-5, -1), "car_0_1": car(0, 1),
            "car_minus1_1": car(-1, 1), "car_post_1_5": post, "car_post_1_10": car(1, 10),
            "signed_post_car": float(np.sign(ar0) * post),
            "initial_sign": int(np.sign(ar0))}


def observation(stock, market, calendar, session, settings, model="market_model"):
    first, last = settings["estimation"]
    dates = calendar.window(session, first, last)
    estimation = pd.concat([stock.reindex(dates).rename("stock"),
                            market.reindex(dates).rename("market")], axis=1)
    valid = np.isfinite(estimation).all(axis=1)
    complete = int(valid.sum())
    if complete != settings["min_estimation"] or len(dates) != settings["min_estimation"]:
        raise ObservationError("insufficient_estimation_coverage", estimation_valid=complete,
                               estimation_expected=settings["min_estimation"])
    fit = fit_market_model(estimation.stock, estimation.market)
    obs_first, obs_last = settings["observation"]
    window_dates = calendar.window(session, obs_first, obs_last)
    y, x = stock.reindex(window_dates), market.reindex(window_dates)
    count = int((np.isfinite(y) & np.isfinite(x)).sum())
    if count != len(window_dates):
        raise ObservationError("incomplete_observation_returns", observation_valid=count,
                               observation_expected=len(window_dates))
    if model == "market_model":
        expected = fit["alpha"] + fit["beta"] * x.to_numpy()
    elif model == "market_adjusted":
        expected = x.to_numpy()
    else:
        raise ValueError("unknown_return_model")
    offsets = np.arange(obs_first, obs_last + 1)
    ar = pd.Series(y.to_numpy() - expected, index=offsets)
    results = {**fit, **summarize_ar(ar), "model": model, "event_session": str(pd.Timestamp(session).date()),
               "estimation_valid": complete, "estimation_first": str(dates[0].date()),
               "estimation_last": str(dates[-1].date()), "observation_valid": count}
    midpoint = len(estimation) // 2
    fit1 = fit_market_model(estimation.stock.iloc[:midpoint], estimation.market.iloc[:midpoint])
    fit2 = fit_market_model(estimation.stock.iloc[midpoint:], estimation.market.iloc[midpoint:])
    results["beta_first_half"], results["beta_second_half"] = fit1["beta"], fit2["beta"]
    results["model_instability_flag"] = abs(fit1["beta"] - fit2["beta"]) > 1
    results["event_volatility_ratio"] = (float(ar.std(ddof=1) / fit["residual_std"])
                                         if fit["residual_std"] > 1e-12 else None)
    results["event_induced_volatility_flag"] = (results["event_volatility_ratio"] or 0) > 2
    results["extreme_return_flag"] = bool(np.max(np.abs(y)) > .4)
    long = pd.DataFrame({"offset": offsets, "session": window_dates.strftime("%Y-%m-%d"),
                         "stock_return": y.to_numpy(), "market_return": x.to_numpy(),
                         "expected_return": expected, "abnormal_return": ar.to_numpy()})
    return results, long

