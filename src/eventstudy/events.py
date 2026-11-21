"""Candidate classification and authoritative timestamp reconciliation."""
import html
import re
from datetime import datetime

import pandas as pd

from .calendar import EASTERN
from .sec_client import SourceError, filing_urls, item_tokens


def visible_text(text):
    text = re.sub(r"<(?:ix:header|script|style)\b[^>]*>.*?</(?:ix:header|script|style)>", " ", text,
                  flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def authoritative_time(text):
    header = re.search(r"<ACCEPTANCE-DATETIME>\s*(\d{14})", text, re.I)
    if header:
        value = datetime.strptime(header[1], "%Y%m%d%H%M%S")
    else:
        match = re.search(r"\bAccepted\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\b",
                          visible_text(text), re.I)
        if not match:
            raise SourceError("authoritative_acceptance_not_found")
        value = datetime.fromisoformat(match[1] + "T" + match[2])
    # EDGAR normally accepts weekdays at unambiguous hours; reject ambiguous/nonexistent local times.
    fold0 = value.replace(tzinfo=EASTERN, fold=0)
    fold1 = value.replace(tzinfo=EASTERN, fold=1)
    if fold0.utcoffset() != fold1.utcoffset():
        raise SourceError("ambiguous_or_nonexistent_Eastern_acceptance")
    return pd.Timestamp(fold0)


def timestamp_comparison(raw, verified, calendar):
    result = {"raw_acceptance_timestamp": raw, "verified_acceptance_timestamp": verified.isoformat(),
              "api_minus_verified_seconds": None, "timestamp_discrepancy": None,
              "discrepancy_changes_session": None, "raw_api_session": None}
    if raw:
        try:
            api = pd.Timestamp(raw)
            if api.tzinfo is None:
                result["raw_timestamp_parse_issue"] = "timezone_missing"
            else:
                delta = (api - verified).total_seconds()
                api_session = calendar.align(api)["event_session"]
                result.update({"api_minus_verified_seconds": delta, "timestamp_discrepancy": delta != 0,
                               "raw_api_session": api_session,
                               "discrepancy_changes_session": api_session != calendar.align(verified)["event_session"]})
        except (ValueError, TypeError):
            result["raw_timestamp_parse_issue"] = "unparseable"
    return result


def classify_filing(record):
    form = record.get("form", "")
    tokens = item_tokens(record.get("items"))
    if form == "8-K/A":
        return "amendment"
    if form != "8-K":
        return "other_form"
    if tokens is None:
        return "unresolved_items"
    return "candidate" if "2.02" in tokens else "not_202"


def document_items(text):
    # Exact heading number; no inference from an isolated narrative mention of '2.02'.
    matches = re.findall(r"\bItem\s+(\d+\.\d{2})(?!\d)\s*[.:\-]?", visible_text(text), re.I)
    return tuple(sorted(set(matches)))


def verify_candidate(record, client, calendar):
    row = dict(record)
    row.setdefault("timestamp_verified", False)
    row.setdefault("primary_reason", "")
    try:
        body, meta = client.get(row["source_url"])
        accepted = authoritative_time(body.decode("utf-8", errors="replace"))
        row["timestamp_source"] = row["source_url"]
    except SourceError as index_error:
        if "403" in str(index_error) or "blocked_after_403" in str(index_error):
            row.update(primary_reason="timestamp_unverified", timestamp_error=str(index_error))
            return row
        try:
            body, meta = client.get(row["submission_url"])
            accepted = authoritative_time(body.decode("utf-8", errors="replace"))
            row["timestamp_source"] = row["submission_url"]
        except SourceError as exc:
            row.update(primary_reason="timestamp_unverified", timestamp_error=f"{index_error}; {exc}")
            return row
    row.update(timestamp_comparison(row.get("acceptanceDateTime", ""), accepted, calendar))
    row.update(calendar.align(accepted))
    row.update({"timestamp_verified": True, "timestamp_source_sha256": meta["sha256"]})
    return row


def normalize_records(records, issuer):
    result = []
    seen = set()
    for record in records:
        row = dict(record)
        accession = row.get("accessionNumber", "")
        row.update({"ticker": issuer["ticker"], "cik": int(issuer["cik"]),
                    "sector": issuer["sector"], "company": issuer["company"],
                    "event_id": f"{int(issuer['cik']):010d}_{accession}",
                    "duplicate_accession": accession in seen})
        row.update(filing_urls(issuer["cik"], accession, row.get("primaryDocument", "")))
        row["discovery_class"] = classify_filing(row)
        row["item_tokens"] = "|".join(item_tokens(row.get("items")) or ())
        row["other_economic_items"] = "|".join(x for x in (item_tokens(row.get("items")) or ())
                                                  if x not in {"2.02", "9.01"})
        row["release_timing_uncertain"] = True
        seen.add(accession)
        result.append(row)
    return result

