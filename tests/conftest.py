import copy

import numpy as np
import pandas as pd
import pytest

from eventstudy.calendar import TradingCalendar
from eventstudy.demo import DEMO_SETTINGS


@pytest.fixture(scope="session")
def calendar():
    return TradingCalendar()


@pytest.fixture
def settings():
    return copy.deepcopy(DEMO_SETTINGS)


@pytest.fixture
def model_returns(calendar):
    rng = np.random.default_rng(42)
    market = pd.Series(rng.normal(0, .01, len(calendar.sessions)), index=calendar.sessions)
    stock = .001 + 1.5 * market
    return stock, market

