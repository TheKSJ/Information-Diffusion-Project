import numpy as np
import pandas as pd
import pytest

from eventstudy.market_model import ObservationError, fit_market_model, observation, summarize_ar
from eventstudy.prices import adjusted_returns, fetch_prices, normalize_prices
from eventstudy.sec_client import SourceError


def test_adjusted_return_and_no_forward_fill():
    dates = pd.bdate_range("2024-01-01", periods=4)
    frame = pd.DataFrame({"Adj Close": [100, 102, 104], "Close": [100, 51, 52]}, index=dates[[0, 1, 3]])
    result = adjusted_returns(frame, dates)
    assert result.iloc[1] == pytest.approx(.02)
    assert pd.isna(result.iloc[2]) and pd.isna(result.iloc[3])


@pytest.mark.parametrize("invalid", [0, -100, np.inf, np.nan])
def test_invalid_prices_do_not_create_returns(invalid):
    dates = pd.bdate_range("2024-01-01", periods=3)
    result = adjusted_returns(pd.DataFrame({"Adj Close": [100, invalid, 110]}, index=dates), dates)
    assert result.isna().all()


def test_missing_adjusted_field_and_duplicates():
    with pytest.raises(SourceError, match="missing_adjusted"):
        normalize_prices(pd.DataFrame({"Close": [100]}))
    with pytest.raises(SourceError, match="duplicate"):
        normalize_prices(pd.DataFrame({"Adj Close": [100, 101]}, index=["2024-01-01"] * 2))


def test_known_alpha_beta(model_returns):
    stock, market = model_returns
    fit = fit_market_model(stock.iloc[:100], market.iloc[:100])
    assert fit["alpha"] == pytest.approx(.001, abs=1e-12)
    assert fit["beta"] == pytest.approx(1.5, abs=1e-12)
    assert fit["r_squared"] == pytest.approx(1.)


def test_estimation_boundaries_and_no_future_leakage(calendar, settings, model_returns):
    stock, market = model_returns
    session = "2023-05-01"
    p = calendar.position(session)
    stock.iloc[p - 20:] += .2
    result, window = observation(stock, market, calendar, session, settings)
    assert result["alpha"] == pytest.approx(.001, abs=1e-12)
    assert result["beta"] == pytest.approx(1.5, abs=1e-12)
    assert result["estimation_first"] == str(calendar.sessions[p - 120].date())
    assert result["estimation_last"] == str(calendar.sessions[p - 21].date())
    assert result["estimation_valid"] == 100
    assert result["ar0"] == pytest.approx(.2)
    assert result["car_post_1_5"] == pytest.approx(1.)
    assert list(window.offset) == list(range(-5, 11))


def test_ar_car_sign_and_day_zero_excluded():
    ar = pd.Series(0., index=range(-5, 11))
    ar.loc[0] = -.04
    ar.loc[1:5] = [-.01, -.02, .01, -.005, .005]
    result = summarize_ar(ar)
    assert result["car_post_1_5"] == pytest.approx(-.02)
    assert result["signed_post_car"] == pytest.approx(.02)
    assert result["car_0_1"] == pytest.approx(-.05)
    assert result["car_minus1_1"] == pytest.approx(-.05)


def test_missing_estimation_and_event_returns_rejected(calendar, settings, model_returns):
    stock, market = model_returns
    p = calendar.position("2023-05-01")
    damaged = stock.copy()
    damaged.iloc[p - 120] = np.nan
    with pytest.raises(ObservationError, match="insufficient_estimation") as caught:
        observation(damaged, market, calendar, "2023-05-01", settings)
    assert caught.value.details["estimation_valid"] == 99
    stock.iloc[p + 5] = np.nan
    with pytest.raises(ObservationError, match="incomplete_observation"):
        observation(stock, market, calendar, "2023-05-01", settings)


def test_explicit_vendor_settings_and_pinned_snapshot(tmp_path):
    calls = []
    def download(ticker, **kwargs):
        calls.append(kwargs)
        return pd.DataFrame({"Adj Close": [100, 101], "Close": [110, 111]},
                            index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    a, meta = fetch_prices("TEST", "2024-01-01", "2024-02-01", tmp_path, downloader=download)
    b, cached = fetch_prices("TEST", "2024-01-01", "2024-02-01", tmp_path, offline=True)
    assert calls[0]["auto_adjust"] is False and calls[0]["repair"] is False
    assert calls[0]["actions"] is True and meta == cached
    pd.testing.assert_frame_equal(a, b)
    with pytest.raises(SourceError, match="offline_price_cache_miss"):
        fetch_prices("MISSING", "2024-01-01", "2024-02-01", tmp_path, offline=True)

