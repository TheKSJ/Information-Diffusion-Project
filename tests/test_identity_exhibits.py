import pytest

from eventstudy.collection import archive_document_url, cover_evidence
from eventstudy.sec_client import SourceError


def test_follow_explicitly_incorporated_identity_exhibit():
    filing = {"primary_document_url": "https://www.sec.gov/Archives/edgar/data/1/2/annual.htm",
              "source_url": "https://www.sec.gov/Archives/edgar/data/1/2/index.html"}
    bodies = {
        filing["primary_document_url"]: '<ix:nonNumeric name="dei:EntityCentralIndexKey">0000000001</ix:nonNumeric>'
              'Securities registered pursuant to section 12(b): See Exhibit 99.01',
        filing["source_url"]: '<table><tr><td>EX-99.01</td><td><a href="/ix?doc=/Archives/edgar/data/1/2/security.htm">security</a></td></tr></table>',
        "https://www.sec.gov/Archives/edgar/data/1/2/security.htm": '<ix:nonNumeric name="dei:TradingSymbol">SYN</ix:nonNumeric>'}
    class Client:
        def get(self, url):
            return bodies[url].encode(), {"sha256": "synthetic-hash"}
    symbols, ciks, evidence = cover_evidence(filing, Client())
    assert symbols == ["SYN"] and ciks == ["0000000001"]
    assert evidence["evidence_url"].endswith("/security.htm")
    assert evidence["identity_evidence_method"] == "annual_cover_explicitly_incorporated_securities_exhibit"


def test_viewer_url_requires_archive_document():
    with pytest.raises(SourceError):
        archive_document_url("https://www.sec.gov/index", "/ix?doc=https://elsewhere.invalid/x")

