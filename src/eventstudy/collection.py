"""Resumable live collection, historical-identity evidence and release audit ledger."""
import logging
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse


from .calendar import TradingCalendar
from .events import document_items, normalize_records, verify_candidate, visible_text
from .prices import fetch_prices
from .sec_client import SECClient, SourceError
from .storage import sha256, snapshot_manifest, utc_now, write_csv, write_json
from .validation import validate_config

LOG = logging.getLogger(__name__)


def make_client(config, offline=False):
    s = config["sec"]
    return SECClient(Path(config["root"]) / config["paths"]["data"] / "raw/sec",
                     os.environ.get("SEC_USER_AGENT", ""), rate=s["requests_per_second"],
                     timeout=s["timeout"], retries=s["retries"], backoff=s["backoff_seconds"], offline=offline)


class IndexDocuments(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.links = [], [], []
        self.in_row = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row, self.row, self.links = True, [], []
        if tag == "a" and self.in_row:
            self.links.extend(v for k, v in attrs if k == "href")

    def handle_data(self, data):
        if self.in_row:
            self.row.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.rows.append((" ".join(self.row), list(self.links)))
            self.in_row = False


def archive_document_url(index_url, href):
    url = urljoin(index_url, href)
    parsed = urlparse(url)
    if parsed.path in {"/ix", "/ixviewer/doc/action"}:
        document = parse_qs(parsed.query).get("doc", [""])[0]
        if not document.startswith("/Archives/edgar/data/"):
            raise SourceError("invalid_SEC_inline_viewer_document")
        return "https://www.sec.gov" + document
    return url


def cover_tags(text):
    tags = re.findall(r"<ix:nonNumeric\b([^>]*)>(.*?)</ix:nonNumeric>", text, re.I | re.S)
    symbols = [visible_text(body) for attrs, body in tags
               if re.search(r'name=[\"\']dei:TradingSymbol[\"\']', attrs, re.I)]
    ciks = [visible_text(body) for attrs, body in tags
            if re.search(r'name=[\"\']dei:EntityCentralIndexKey[\"\']', attrs, re.I)]
    return symbols, ciks


def cover_evidence(filing, client):
    url = filing["primary_document_url"]
    content, meta = client.get(url)
    text = content.decode("utf-8", errors="replace")
    symbols, ciks = cover_tags(text)
    result = {"evidence_url": url, "source_sha256": meta["sha256"],
              "primary_cover_url": url, "primary_cover_sha256": meta["sha256"],
              "identity_evidence_method": "annual_inline_cover"}
    # Some 10-K covers explicitly incorporate a securities-registration exhibit. Follow it,
    # rather than treating a missing tag on the primary cover as absence of historical identity.
    if not symbols and re.search(r"Securities registered.{0,500}See Exhibit 99\.01", visible_text(text), re.I):
        index, _ = client.get(filing["source_url"])
        parser = IndexDocuments()
        parser.feed(index.decode("utf-8", errors="replace"))
        links = [href for description, hrefs in parser.rows
                 if re.search(r"\bEX-99\.01\b", description, re.I) for href in hrefs]
        for href in links:
            exhibit_url = archive_document_url(filing["source_url"], href)
            exhibit, exhibit_meta = client.get(exhibit_url)
            exhibit_symbols, _ = cover_tags(exhibit.decode("utf-8", errors="replace"))
            if exhibit_symbols:
                symbols = exhibit_symbols
                result.update(evidence_url=exhibit_url, source_sha256=exhibit_meta["sha256"],
                              identity_evidence_method="annual_cover_explicitly_incorporated_securities_exhibit")
                break
    return symbols, ciks, result


def historical_identity(issuer, root, filings, client):
    ticker, cik = issuer["ticker"], int(issuer["cik"])
    current_ok = ticker in root.get("tickers", []) and int(root.get("cik", 0)) == cik
    evidence = []
    for year in range(2021, 2026):
        annuals = sorted([r for r in filings if r.get("form") == "10-K"
                          and r.get("filingDate", "").startswith(str(year))],
                         key=lambda r: r["accessionNumber"])
        row = {"ticker": ticker, "year": year, "current_mapping_verified": current_ok,
               "historical_cover_verified": False, "evidence_url": "", "error": "no_annual_cover_available"}
        if annuals:
            filing = annuals[0]
            row["evidence_url"] = filing["primary_document_url"]
            try:
                symbols, cover_ciks, evidence_meta = cover_evidence(filing, client)
                row.update(evidence_meta)
                row.update({"cover_symbols": "|".join(symbols),
                            "cover_ciks": "|".join(cover_ciks),
                            "historical_cover_verified": ticker in symbols and any(
                                x.isdigit() and int(x) == cik for x in cover_ciks), "error": ""})
                if not row["historical_cover_verified"]:
                    row["error"] = "annual_cover_symbol_CIK_not_corroborated"
            except SourceError as exc:
                row["error"] = str(exc)
        evidence.append(row)
    valid = current_ok and all(r["historical_cover_verified"] for r in evidence)
    return valid, evidence


def audit_filings(candidates, client, count):
    audit = []
    selected = sorted(candidates, key=lambda r: sha256(r["event_id"].encode()))[:count]
    for row in selected:
        record = {"event_id": row["event_id"], "ticker": row["ticker"],
                  "index_url": row["source_url"], "primary_document_url": row["primary_document_url"],
                  "reviewed": False, "first_public_release_verified": False,
                  "release_may_precede_filing": "unknown", "release_timestamp": "",
                  "review_status": "needs_human_review", "exhibits": [], "errors": []}
        try:
            primary, _ = client.get(row["primary_document_url"])
            primary_text = visible_text(primary.decode("utf-8", errors="replace"))
            item_match = re.search(r"\bItem\s+2\.02\b", primary_text, re.I)
            start = max(item_match.start() - 200, 0) if item_match else 0
            record["filing_excerpt"] = primary_text[start:start + 5000]
            index, _ = client.get(row["source_url"])
            parser = IndexDocuments()
            parser.feed(index.decode("utf-8", errors="replace"))
            for description, links in parser.rows:
                if re.search(r"EX-99|earnings|press.release", description, re.I):
                    for link in links:
                        url = archive_document_url(row["source_url"], link)
                        try:
                            exhibit, meta = client.get(url)
                            excerpt = visible_text(exhibit.decode("utf-8", errors="replace"))[:6000]
                            dates = re.findall(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}\b", excerpt)
                            record["exhibits"].append({"url": url, "sha256": meta["sha256"],
                                                       "excerpt": excerpt, "date_strings_for_review": dates})
                        except SourceError as exc:
                            record["errors"].append(str(exc))
        except SourceError as exc:
            record["errors"].append(str(exc))
            record["review_status"] = "source_unavailable"
        audit.append(record)
    return audit


def fetch(config, pilot=False, offline=False, prices_only=False):
    universe = validate_config(config)
    root = Path(config["root"])
    data = root / config["paths"]["data"]
    interim = data / ("interim/pilot" if pilot else "interim")
    interim.mkdir(parents=True, exist_ok=True)
    calendar = TradingCalendar()
    s = config["study"]
    chosen = universe[universe.ticker.isin(["AAPL", "JPM", "CAT"])] if pilot else universe
    all_filings, candidates, amendments, excluded_metadata, failures, identity, coverage = [], [], [], [], [], [], []
    client = None
    if not prices_only:
        try:
            client = make_client(config, offline)
        except ValueError as exc:
            failures.append({"ticker": "ALL", "stage": "SEC_configuration", "error": str(exc)})
    for issuer in chosen.to_dict("records"):
        ticker = issuer["ticker"]
        LOG.warning("Collecting %s (%s)", ticker, "three-company pilot" if pilot else "fixed universe")
        mapped, complete, count = False, False, 0
        if client:
            try:
                metadata, records, errors = client.submissions(issuer["cik"], "2020-12-01", "2026-01-31")
                normalized = normalize_records(records, issuer)
                for row in normalized:
                    row["source_company_name"] = metadata.get("name", "")
                all_filings.extend(normalized)
                complete = not errors
                failures.extend({"ticker": ticker, **err} for err in errors)
                mapped, identity_rows = historical_identity(issuer, metadata, normalized, client)
                identity.extend(identity_rows)
                for row in normalized:
                    if row["duplicate_accession"]:
                        continue
                    if row["discovery_class"] == "amendment":
                        amendments.append(row)
                        continue
                    if row["discovery_class"] == "unresolved_items":
                        try:
                            content, meta = client.get(row["primary_document_url"])
                            tokens = document_items(content.decode("utf-8", errors="replace"))
                            if "2.02" in tokens:
                                row.update({"discovery_class": "candidate", "item_tokens": "|".join(tokens),
                                            "other_economic_items": "|".join(x for x in tokens if x not in {"2.02", "9.01"}),
                                            "item_evidence_sha256": meta["sha256"],
                                            "items_verified_from_document": True})
                            else:
                                row["primary_reason"] = "unresolved_item_metadata"
                        except SourceError as exc:
                            row.update(primary_reason="unresolved_item_metadata", item_error=str(exc))
                        if row["discovery_class"] != "candidate":
                            excluded_metadata.append(dict(row))
                    if row["discovery_class"] == "candidate":
                        verified = verify_candidate(row, client, calendar)
                        verified.update(historical_identity_verified=mapped, SEC_screening_complete=complete)
                        candidates.append(verified)
                        count += 1
                        if count % 20 == 0:
                            LOG.warning("%s: %s candidate timestamps checked", ticker, count)
                # Incremental checkpoints survive a later issuer failure or interrupted collection.
            except (SourceError, ValueError) as exc:
                failures.append({"ticker": ticker, "stage": "SEC_submissions", "error": str(exc)})
        else:
            failures.append({"ticker": ticker, "stage": "SEC_submissions", "error": "SEC_unconfigured_or_disabled"})
        coverage.append({"ticker": ticker, "historical_identity_verified": mapped,
                         "SEC_screening_complete": complete, "candidates": count})
        write_csv(interim / "all_filings.csv", all_filings, ["event_id", "ticker", "form", "filingDate"])
        write_csv(interim / "candidate_events.csv", candidates, ["event_id", "ticker", "event_session", "timestamp_verified"])
        write_json(interim / "source_failures.json", failures)
        try:
            fetch_prices(ticker, s["price_start"], s["price_end_exclusive"], data / "raw/prices", offline)
        except (SourceError, Exception) as exc:
            # Vendor libraries raise heterogeneous network/format errors. Preserve exact type/message.
            failures.append({"ticker": ticker, "stage": "prices", "error": f"{type(exc).__name__}:{exc}"})
            LOG.warning("%s price collection failed: %s", ticker, exc)
    try:
        fetch_prices(s["market"], s["price_start"], s["price_end_exclusive"], data / "raw/prices", offline)
    except Exception as exc:
        failures.append({"ticker": s["market"], "stage": "prices", "error": f"{type(exc).__name__}:{exc}"})
    audit = audit_filings(candidates, client, s["audit_size"]) if client else []
    for packet in audit:
        failures.extend({"ticker": packet["ticker"], "stage": "release_timing_audit",
                         "source": packet["index_url"], "error": error} for error in packet["errors"])
    write_json(interim / "release_audit.json", audit)
    write_csv(interim / "historical_identity.csv", identity,
              ["ticker", "year", "historical_cover_verified", "evidence_url", "error"])
    write_csv(interim / "issuer_coverage.csv", coverage)
    write_csv(interim / "amendments.csv", amendments, ["event_id", "ticker", "form"])
    write_csv(interim / "unresolved_items.csv", excluded_metadata, ["event_id", "ticker", "primary_reason"])
    write_json(interim / "source_failures.json", failures)
    manifest = {"retrieval_completed_at": utc_now(), "pilot": pilot, "requested_companies": len(chosen),
                "filings_discovered": len(all_filings), "candidate_events": len(candidates),
                "verified_events": sum(bool(r.get("timestamp_verified")) for r in candidates),
                "failed_operations": len(failures), "snapshots": snapshot_manifest(data / "raw")}
    write_json(interim / "fetch_manifest.json", manifest)
    LOG.warning("Collection complete: %s filings, %s candidates, %s verified; %s failed operations",
                len(all_filings), len(candidates), manifest["verified_events"], len(failures))
    return manifest

