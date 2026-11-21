"""SEC collection: aligned arrays, historical pagination, cache, identity and fair access."""
import json
import logging
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from .storage import sha256, utc_now, write_json

LOG = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


def validate_user_agent(value):
    if not value or not re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", value):
        raise ValueError("Set SEC_USER_AGENT to a project identifier and your actual contact email")
    if any(x in value.lower() for x in ("example.com", "your@email", "test@", "placeholder")):
        raise ValueError("SEC_USER_AGENT must contain real contact details")
    if len(value.split()) < 2:
        raise ValueError("SEC_USER_AGENT must also identify the project")
    return value


def reconstruct_arrays(arrays):
    if "accessionNumber" not in arrays:
        raise SourceError("missing_accession_array")
    n = len(arrays["accessionNumber"])
    for key, value in arrays.items():
        if isinstance(value, list) and len(value) != n:
            raise SourceError(f"parallel_array_length_mismatch:{key}:{len(value)}!={n}")
    return [{key: value[i] for key, value in arrays.items() if isinstance(value, list)} for i in range(n)]


def item_tokens(value):
    if value is None or not str(value).strip():
        return None
    tokens = re.split(r"[,;\s]+", str(value).strip())
    if any(not re.fullmatch(r"\d+\.\d{2}", token) for token in tokens):
        return None
    return tuple(sorted(set(tokens)))


def filing_urls(cik, accession, document):
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise SourceError("invalid_accession")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}"
    return {"source_url": f"{base}/{accession}-index.html",
            "primary_document_url": f"{base}/{document}" if document else "",
            "submission_url": f"{base}/{accession}.txt"}


class SECClient:
    _lock = threading.Lock()
    _last_request = 0.0
    _blocked_hosts = set()

    def __init__(self, cache, user_agent, rate=2, timeout=30, retries=3, backoff=2,
                 session=None, offline=False, sleep=time.sleep, clock=time.monotonic):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.user_agent = validate_user_agent(user_agent) if not offline else user_agent
        if not 0 < rate <= 2:
            raise ValueError("project_SEC_rate_must_be_in_(0,2]")
        self.rate, self.timeout, self.retries, self.backoff = rate, timeout, retries, backoff
        self.session = session or requests.Session()
        self.offline, self.sleep, self.clock = offline, sleep, clock

    def get(self, url):
        if urlparse(url).hostname not in {"www.sec.gov", "data.sec.gov"}:
            raise SourceError("non_SEC_URL_rejected")
        path = self.cache / (sha256(url.encode()) + ".body")
        meta_path = path.with_name(path.name + ".meta.json")
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            content = path.read_bytes()
            if sha256(content) != meta["sha256"]:
                raise SourceError(f"corrupt_cached_source:{path.name}")
            return content, meta
        if self.offline:
            raise SourceError(f"offline_cache_miss:{url}")
        host = urlparse(url).hostname
        if host in self._blocked_hosts:
            raise SourceError(f"SEC_host_blocked_after_403:{host}")
        last = None
        for attempt in range(self.retries + 1):
            with self._lock:
                delay = 1 / self.rate - (self.clock() - SECClient._last_request)
                if delay > 0:
                    self.sleep(delay)
                SECClient._last_request = self.clock()
            try:
                response = self.session.get(url, headers={"User-Agent": self.user_agent,
                                                        "Accept-Encoding": "gzip, deflate"},
                                            timeout=self.timeout)
                if response.status_code == 403:
                    self._blocked_hosts.add(host)
                    raise SourceError(f"SEC_HTTP_403_access_denied:{host}; collection stopped for host")
                if response.status_code == 429 or response.status_code >= 500:
                    last = f"SEC_HTTP_{response.status_code}:{url}"
                    if attempt < self.retries:
                        retry_after = response.headers.get("Retry-After", "0")
                        delay = max(self.backoff * 2**attempt,
                                    float(retry_after) if retry_after.isdigit() else 0)
                        self.sleep(min(delay, 60))
                        continue
                    raise SourceError(last)
                response.raise_for_status()
                content = response.content
                meta = {"url": url, "retrieved_at": utc_now(), "sha256": sha256(content),
                        "bytes": len(content), "status": response.status_code,
                        "etag": response.headers.get("ETag"),
                        "last_modified": response.headers.get("Last-Modified")}
                # No silent replacement of an existing pinned snapshot.
                path.write_bytes(content)
                write_json(meta_path, meta)
                return content, meta
            except requests.RequestException as exc:
                last = f"{type(exc).__name__}:{exc}"
                if getattr(exc.response, "status_code", None) in (400, 404):
                    break
                if attempt < self.retries:
                    self.sleep(self.backoff * 2**attempt)
        raise SourceError(last or "unknown_SEC_error")

    def json(self, url):
        content, meta = self.get(url)
        try:
            return json.loads(content), meta
        except ValueError as exc:
            raise SourceError(f"invalid_SEC_JSON:{url}") from exc

    def submissions(self, cik, start, end):
        url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
        root, meta = self.json(url)
        rows, failures = [], []
        pages = [(root.get("filings", {}).get("recent", {}), meta)]
        for page in root.get("filings", {}).get("files", []):
            if page.get("filingTo", "9999") < start or page.get("filingFrom", "0000") > end:
                continue
            try:
                data, page_meta = self.json("https://data.sec.gov/submissions/" + page["name"])
                pages.append((data.get("filings", {}).get("recent", data), page_meta))
            except SourceError as exc:
                failures.append({"stage": "pagination", "source": page["name"], "error": str(exc)})
        for arrays, page_meta in pages:
            try:
                for record in reconstruct_arrays(arrays):
                    if start <= record.get("filingDate", "") <= end:
                        record.update({"metadata_url": page_meta["url"],
                                       "metadata_sha256": page_meta["sha256"],
                                       "retrieved_at": page_meta["retrieved_at"]})
                        rows.append(record)
            except SourceError as exc:
                failures.append({"stage": "parallel_arrays", "source": page_meta["url"], "error": str(exc)})
        return root, rows, failures

