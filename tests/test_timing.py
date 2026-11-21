import pandas as pd
import pytest

from eventstudy.events import authoritative_time, timestamp_comparison, verify_candidate
from eventstudy.sec_client import SourceError


@pytest.mark.parametrize("stamp,date,kind", [
    ("2024-05-01T08:00:00-04:00", "2024-05-01", "before_open"),
    ("2024-05-01T10:00:00-04:00", "2024-05-01", "intraday"),
    ("2024-05-01T16:00:00-04:00", "2024-05-02", "after_close"),
    ("2024-05-03T16:01:00-04:00", "2024-05-06", "after_close"),
    ("2024-05-04T08:00:00-04:00", "2024-05-06", "non_session"),
    ("2024-11-28T12:00:00-05:00", "2024-11-29", "non_session"),
    ("2024-11-29T13:00:00-05:00", "2024-12-02", "after_close"),
    ("2024-07-03T12:59:59-04:00", "2024-07-03", "intraday"),
    ("2024-07-03T13:00:00-04:00", "2024-07-05", "after_close"),
    ("2024-03-08T21:00:00Z", "2024-03-11", "after_close"),
    ("2024-03-11T20:00:00Z", "2024-03-12", "after_close"),
    ("2025-01-09T12:00:00-05:00", "2025-01-10", "non_session"),
])
def test_alignment(calendar, stamp, date, kind):
    result = calendar.align(stamp)
    assert (result["event_session"], result["timing_class"]) == (date, kind)


def test_authoritative_local_time_and_dst():
    winter = authoritative_time("<ACCEPTANCE-DATETIME>20240102163000")
    summer = authoritative_time("<div>Accepted</div><div>2024-07-02 16:30:00</div>")
    assert winter.utcoffset().total_seconds() == -18000
    assert summer.utcoffset().total_seconds() == -14400
    with pytest.raises(SourceError, match="ambiguous"):
        authoritative_time("<ACCEPTANCE-DATETIME>20241103013000")


def test_wrong_z_changes_event_day(calendar):
    accepted = authoritative_time("Accepted 2024-05-03 16:30:00")
    result = timestamp_comparison("2024-05-03T16:30:00Z", accepted, calendar)
    assert result["api_minus_verified_seconds"] == -14400
    assert result["discrepancy_changes_session"] is True
    assert result["raw_api_session"] == "2024-05-03"
    assert calendar.align(accepted)["event_session"] == "2024-05-06"


def test_naive_api_not_assumed_utc(calendar):
    accepted = authoritative_time("Accepted 2024-01-02 08:00:00")
    assert timestamp_comparison("2024-01-02T08:00:00", accepted, calendar)["raw_timestamp_parse_issue"] == "timezone_missing"
    with pytest.raises(ValueError, match="timezone"):
        calendar.align("2024-01-02 08:00:00")


def test_no_timestamp_fabrication(calendar):
    class Missing:
        def get(self, url):
            raise SourceError("unavailable")
    row = verify_candidate({"source_url": "x", "submission_url": "y", "acceptanceDateTime": "2024-01-02T08:00Z"}, Missing(), calendar)
    assert row["timestamp_verified"] is False
    assert row["primary_reason"] == "timestamp_unverified"
    assert "event_session" not in row


def test_missing_prices_do_not_realign(calendar):
    result = calendar.align("2024-05-01T10:00:00-04:00")
    available_prices = pd.Series([100], index=pd.to_datetime(["2024-05-02"]))
    assert pd.Timestamp(result["event_session"]) not in available_prices.index
    assert result["event_session"] == "2024-05-01"

