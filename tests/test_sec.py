import json

import pytest
import requests

from eventstudy.events import classify_filing, document_items, normalize_records
from eventstudy.sec_client import SECClient, SourceError, filing_urls, item_tokens, reconstruct_arrays, validate_user_agent

UA = "SyntheticUnitTest actual.person@university.edu"  # MOCK ONLY, never sent on a live request.


@pytest.fixture(autouse=True)
def reset_limiter():
    SECClient._blocked_hosts.clear()
    SECClient._last_request = 0
    yield
    SECClient._blocked_hosts.clear()


class Response:
    def __init__(self, value, status=200):
        self.content = json.dumps(value).encode()
        self.status_code = status
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(str(self.status_code))
            error.response = self
            raise error


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def test_parallel_arrays():
    arrays = {"accessionNumber": ["b", "a"], "form": ["8-K", "10-K"], "items": ["2.02", ""]}
    assert reconstruct_arrays(arrays)[1] == {"accessionNumber": "a", "form": "10-K", "items": ""}
    with pytest.raises(SourceError, match="length_mismatch"):
        reconstruct_arrays({"accessionNumber": [1, 2], "items": ["2.02"]})


@pytest.mark.parametrize("value,expected", [("2.02,9.01", True), ("12.02", False), ("2.020", False),
                                           ("2.02; 7.01", True), (None, None), ("", None)])
def test_exact_item_tokens(value, expected):
    tokens = item_tokens(value)
    actual = None if tokens is None else "2.02" in tokens
    if value == "2.020":
        assert actual is None
    else:
        assert actual is expected


def test_amendment_missing_items_and_heading():
    assert classify_filing({"form": "8-K/A", "items": "2.02"}) == "amendment"
    assert classify_filing({"form": "8-K", "items": ""}) == "unresolved_items"
    assert document_items("<b>Item 2.02.</b> Results") == ("2.02",)
    assert document_items("Item 12.02 other; Item 2.020") == ("12.02",)


def test_url_uses_actual_issuer_not_accession_prefix():
    urls = filing_urls(320193, "0001193125-21-123456", "earnings.htm")
    assert "/320193/000119312521123456/" in urls["source_url"]
    assert urls["primary_document_url"].endswith("/earnings.htm")
    with pytest.raises(SourceError):
        filing_urls(1, "bad", "x")


def test_duplicate_accession_preserved_and_flagged():
    record = {"accessionNumber": "0000320193-21-000001", "form": "8-K", "items": "2.02", "primaryDocument": "x"}
    issuer = {"ticker": "AAPL", "cik": 320193, "sector": "Tech", "company": "Apple"}
    result = normalize_records([record, record], issuer)
    assert len(result) == 2
    assert [r["duplicate_accession"] for r in result] == [False, True]


def test_historical_pagination_and_cache(tmp_path):
    base = {"cik": 1, "filings": {"recent": {"accessionNumber": ["recent"], "filingDate": ["2025-01-01"]},
             "files": [{"name": "old.json", "filingFrom": "2021-01-01", "filingTo": "2022-01-01"}]}}
    old = {"accessionNumber": ["old"], "filingDate": ["2021-06-01"]}
    session = Session([Response(base), Response(old)])
    client = SECClient(tmp_path, UA, session=session, sleep=lambda _: None, clock=lambda: 100)
    _, records, errors = client.submissions(1, "2021-01-01", "2025-12-31")
    assert [r["accessionNumber"] for r in records] == ["recent", "old"]
    assert not errors and len(session.calls) == 2
    client.submissions(1, "2021-01-01", "2025-12-31")
    assert len(session.calls) == 2


def test_partial_pagination_failure_is_visible(tmp_path):
    base = {"filings": {"recent": {"accessionNumber": ["ok"], "filingDate": ["2021-01-01"]},
            "files": [{"name": "bad.json", "filingFrom": "2021-01-01", "filingTo": "2021-12-31"}]}}
    client = SECClient(tmp_path, UA, retries=0, session=Session([Response(base), Response({}, 500)]), sleep=lambda _: None)
    _, records, errors = client.submissions(1, "2021-01-01", "2021-12-31")
    assert len(records) == 1 and errors[0]["stage"] == "pagination"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retry_behavior(tmp_path, status):
    delays = []
    session = Session([Response({}, status), Response({"ok": True})])
    client = SECClient(tmp_path, UA, session=session, sleep=delays.append, clock=lambda: 100)
    value, _ = client.json("https://data.sec.gov/test")
    assert value["ok"] and len(session.calls) == 2 and max(delays) >= 2


def test_403_circuit_and_corrupt_cache(tmp_path):
    session = Session([Response({}, 403)])
    client = SECClient(tmp_path, UA, session=session, sleep=lambda _: None)
    with pytest.raises(SourceError, match="403"):
        client.get("https://www.sec.gov/one")
    with pytest.raises(SourceError, match="blocked_after_403"):
        client.get("https://www.sec.gov/two")
    assert len(session.calls) == 1
    SECClient._blocked_hosts.clear()
    client = SECClient(tmp_path, UA, session=Session([Response({})]), sleep=lambda _: None)
    client.get("https://data.sec.gov/one")
    list(tmp_path.glob("*.body"))[0].write_text("tampered")
    with pytest.raises(SourceError, match="corrupt"):
        client.get("https://data.sec.gov/one")


def test_user_agent_and_offline_no_fallback(tmp_path):
    for value in ["", "project your@email.com", "project user@example.com"]:
        with pytest.raises(ValueError):
            validate_user_agent(value)
    client = SECClient(tmp_path, "", offline=True)
    with pytest.raises(SourceError, match="offline_cache_miss"):
        client.get("https://data.sec.gov/missing")

