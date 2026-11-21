"""Session alignment independent of available vendor prices."""
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

EASTERN = ZoneInfo("America/New_York")


class TradingCalendar:
    def __init__(self, start="2020-01-01", end="2026-12-31"):
        self.exchange = xcals.get_calendar("XNYS", start=start, end=end)
        self.schedule = self.exchange.schedule
        self.sessions = pd.DatetimeIndex(self.schedule.index).tz_localize(None)

    def align(self, timestamp):
        stamp = pd.Timestamp(timestamp)
        if stamp.tzinfo is None:
            raise ValueError("Verified acceptance timestamp must have a timezone")
        local = stamp.tz_convert(EASTERN)
        date = local.tz_localize(None).normalize()
        position = int(self.sessions.searchsorted(date))
        if position >= len(self.sessions):
            raise ValueError("timestamp_outside_calendar")
        session = self.sessions[position]
        if session != date:
            classification = "non_session"
        else:
            opening = self.exchange.session_open(session)
            closing = self.exchange.session_close(session)
            if stamp < opening:
                classification = "before_open"
            elif stamp < closing:
                classification = "intraday"
            else:
                classification = "after_close"
                position += 1
                if position >= len(self.sessions):
                    raise ValueError("timestamp_outside_calendar")
                session = self.sessions[position]
        return {"event_session": session.strftime("%Y-%m-%d"),
                "timing_class": classification,
                "intraday_prefiling_activity": classification == "intraday"}

    def position(self, session):
        date = pd.Timestamp(session).tz_localize(None).normalize()
        position = self.sessions.get_indexer([date])[0]
        if position < 0:
            raise ValueError("not_an_exchange_session")
        return int(position)

    def window(self, session, first, last):
        p = self.position(session)
        if p + first < 0 or p + last >= len(self.sessions):
            raise ValueError("window_outside_calendar")
        return self.sessions[p + first:p + last + 1]

