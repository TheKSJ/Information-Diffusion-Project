"""Local research desk: read-only evidence APIs and allowlisted background research tasks.

The calculation modules remain the authority. This interface never re-estimates a filtered
headline, edits the locked design, fetches new vendor data, or exposes the workspace as files.
"""
import csv
import hashlib
import hmac
import io
import json
import logging
import math
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

LOG = logging.getLogger(__name__)
ASSETS = Path(__file__).with_name("web")
APPLICATION = "information-diffusion-research-desk"
SCALAR_NUMBERS = {
    "cik", "alpha", "beta", "r_squared", "residual_std", "ar0", "car_pre_5_1", "car_0_1",
    "car_minus1_1", "car_post_1_5", "car_post_1_10", "signed_post_car", "initial_sign",
    "estimation_valid", "observation_valid", "api_minus_verified_seconds", "event_volatility_ratio",
    "offset", "stock_return", "market_return", "expected_return", "abnormal_return", "year_gap",
    "magnitude_gap", "volatility_gap", "difference", "event_signed_post_car", "control_signed_post_car",
    "event_ar0", "control_ar0", "estimate_pp", "ci95_low_pp", "ci95_high_pp", "p_one_sided",
    "p_two_sided", "n_pairs", "n_issuers", "n_calendar_quarters", "n", "issuers", "count", "year",
    "aar_percent", "caar_percent", "aar_ci_low", "aar_ci_high", "caar_ci_low", "caar_ci_high",
    "mean_signed_post_car_percent", "mean_ar0_percent", "mean_post_car_percent", "candidates",
}
BOOLEAN_FIELDS = {
    "timestamp_verified", "historical_identity_verified", "SEC_screening_complete", "clean_release_timing",
    "timestamp_discrepancy", "discrepancy_changes_session", "intraday_prefiling_activity",
    "release_timing_uncertain", "nonstandard_disclosure_flag", "disclosure_reviewed",
    "first_public_release_verified", "overlapping_event_window", "model_instability_flag",
    "event_induced_volatility_flag", "extreme_return_flag", "above_primary_threshold", "year_fallback",
    "reviewed", "historical_cover_verified", "current_mapping_verified",
}
EVENT_FIELDS = {
    "event_id", "ticker", "company", "sector", "cik", "accessionNumber", "form", "items", "item_tokens",
    "other_economic_items", "filingDate", "reportDate", "retrieved_at", "source_company_name",
    "source_url", "primary_document_url", "timestamp_source", "timestamp_source_sha256", "metadata_sha256",
    "raw_acceptance_timestamp", "verified_acceptance_timestamp", "raw_api_session", "event_session", "timing_class",
    "primary_reason", "release_review_notes", "release_date", "release_reviewer", "release_evidence_url",
    "disclosure_review_notes", "release_may_precede_filing", "estimation_first", "estimation_last", "model",
    *SCALAR_NUMBERS, *BOOLEAN_FIELDS,
}
DOWNLOADS = {
    "events.csv": "data/processed/event_ledger.csv",
    "matched-pairs.csv": "data/processed/matched_pairs.csv",
    "unmatched-events.csv": "data/processed/unmatched_events.csv",
    "results.csv": "data/processed/results_table.csv",
    "timestamps.csv": "data/processed/timestamp_ledger.csv",
    "universe.csv": "data/processed/universe_resolved.csv",
    "primary-results.json": "data/processed/primary_inference.json",
    "run-manifest.json": "data/processed/run_manifest.json",
    "technical-report.md": "reports/live/technical_report.md",
}
DOCUMENTS = {
    "report": "reports/live/technical_report.md", "design": "docs/research_design.md",
    "methods": "docs/methodology.md", "limitations": "docs/limitations.md",
    "audit": "docs/source_audit.md", "arithmetic": "docs/numerical_walkthrough.md",
    "dictionary": "docs/data_dictionary.md", "handoff": "docs/HANDOFF.md",
}
TASKS = {
    "tests": {"title": "Verify installation and tests", "detail": "Validate the fixed design and run the automated test suite."},
    "demo": {"title": "Run the offline demonstration", "detail": "Run an isolated end-to-end study using labelled synthetic fixtures."},
    "reproduce": {"title": "Reproduce the cached study", "detail": "Rebuild the genuine-data study and compare every processed output hash."},
    "report": {"title": "Refresh the research report", "detail": "Regenerate tables and five figures from the saved calculations."},
}


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(item) for item in value]
    return value


def csv_rows(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        result = []
        for row in csv.DictReader(handle):
            for key, value in row.items():
                if value in ("", None):
                    row[key] = None
                elif key in BOOLEAN_FIELDS:
                    row[key] = str(value).lower() in {"true", "1", "yes"}
                elif key in SCALAR_NUMBERS:
                    try:
                        row[key] = float(value)
                        if not math.isfinite(row[key]):
                            row[key] = None
                    except ValueError:
                        row[key] = None
            result.append(row)
        return result


def json_file(path, default=None):
    if not Path(path).exists():
        return default
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ResearchData:
    """A consistent in-memory view; refresh explicitly after a successful calculation job."""
    def __init__(self, config):
        self.config = config
        self.root = Path(config["root"])
        self.processed = self.root / config["paths"]["data"] / "processed"
        self.interim = self.root / config["paths"]["data"] / "interim"
        self.lock = threading.RLock()
        self.reload()

    def reload(self):
        with self.lock:
            self.summary = json_file(self.processed / "run_summary.json", {})
            self.primary = json_file(self.processed / "primary_inference.json", {})
            self.manifest = json_file(self.processed / "run_manifest.json", {})
            self.fetch_manifest = json_file(self.interim / "fetch_manifest.json", {})
            self.matching = json_file(self.processed / "matching_diagnostics.json", {})
            self.waterfall = json_file(self.processed / "exclusion_waterfall.json", {})
            self.pairs = csv_rows(self.processed / "matched_pairs.csv")
            self.pair_by_event = {row["event_id"]: row for row in self.pairs}
            self.events = csv_rows(self.processed / "event_ledger.csv")
            for row in self.events:
                pair = self.pair_by_event.get(row["event_id"])
                row["sample_status"] = ("excluded" if row.get("primary_reason") else "matched" if pair else "unmatched")
                row["initial_magnitude_gap_pp"] = pair["magnitude_gap"] * 100 if pair else None
            self.by_id = {row["event_id"]: row for row in self.events}
            self.trajectory = csv_rows(self.processed / "event_time_trajectory.csv")
            self.results = csv_rows(self.processed / "results_table.csv")
            self.secondary = csv_rows(self.processed / "secondary_descriptive.csv")
            self.universe = csv_rows(self.processed / "universe_resolved.csv")
            self.windows = self._group(csv_rows(self.processed / "event_abnormal_returns.csv"), "event_id")
            self.control_windows = self._group(csv_rows(self.processed / "control_abnormal_returns.csv"), "control_id")
            self.controls = {row["control_id"]: row for row in csv_rows(self.processed / "control_candidates.csv")}
            self.verification = self._latest_verification()
            self.revision = hashlib.sha256(json.dumps([self.manifest, self.summary, self.primary],
                                                     sort_keys=True).encode()).hexdigest()[:20]

    @staticmethod
    def _group(rows, key):
        grouped = {}
        for row in rows:
            grouped.setdefault(row[key], []).append(row)
        return {key: sorted(value, key=lambda row: row.get("offset", 0)) for key, value in grouped.items()}

    def _latest_verification(self):
        folders = sorted((self.root / "reports").glob("verification-*/summary.json"), reverse=True)
        return json_file(folders[0], {}) if folders else {}

    def overview(self):
        with self.lock:
            snapshots = self.manifest.get("source_snapshots", [])
            return clean({"ready": bool(self.summary), "revision": self.revision,
                          "summary": self.summary, "primary": self.primary,
                          "matching": self.matching, "waterfall": self.waterfall, "trajectory": self.trajectory,
                          "results": self.results, "secondary": self.secondary, "universe": self.universe,
                          "verification": self.verification, "study": self.config["study"],
                          "snapshot": {"retrieved_at": self.fetch_manifest.get("retrieval_completed_at"),
                                       "source_count": len(snapshots), "config_sha256": self.manifest.get("config_sha256"),
                                       "design_sha256": self.manifest.get("design_sha256"),
                                       "universe_sha256": self.manifest.get("universe_sha256")},
                          "facets": {"tickers": sorted({row["ticker"] for row in self.events}),
                                     "sectors": sorted({row["sector"] for row in self.events if row.get("sector")}),
                                     "years": sorted({row["event_session"][:4] for row in self.events if row.get("event_session")})}})

    def filtered_events(self, params):
        query = params.get("q", "").strip().lower()[:200]
        status, sector, year = (params.get(key, "all") for key in ("status", "sector", "year"))
        sign, timing = params.get("sign", "all"), params.get("timing", "all")
        if status not in {"all", "qualified", "matched", "unmatched", "excluded", "in_window", "valid"}:
            raise ValueError("Unknown sample status")
        if sign not in {"all", "positive", "negative"}:
            raise ValueError("Unknown response direction")
        filtered = []
        for row in self.events:
            if query and query not in " ".join(str(row.get(key) or "") for key in ("ticker", "company", "accessionNumber", "event_id")).lower():
                continue
            if status == "qualified" and row["sample_status"] == "excluded":
                continue
            if status == "in_window" and not (self.config["study"]["start"] <= (row.get("event_session") or "")
                                              <= self.config["study"]["end"]):
                continue
            if status == "valid" and row.get("primary_reason") not in {None, "below_initial_threshold"}:
                continue
            if status not in {"all", "qualified", "in_window", "valid"} and row["sample_status"] != status:
                continue
            if sector != "all" and row.get("sector") != sector:
                continue
            if year != "all" and not str(row.get("event_session") or "").startswith(year):
                continue
            if sign != "all" and ((row.get("ar0") is None) or (sign == "positive" and row["ar0"] <= 0)
                                  or (sign == "negative" and row["ar0"] >= 0)):
                continue
            if timing != "all" and row.get("timing_class") != timing:
                continue
            filtered.append(row)
        sort = params.get("sort", "recent")
        if sort == "magnitude":
            filtered.sort(key=lambda row: (abs(row.get("ar0") or 0), row["event_id"]), reverse=True)
        elif sort == "gap":
            filtered.sort(key=lambda row: (row["initial_magnitude_gap_pp"]
                                          if row.get("initial_magnitude_gap_pp") is not None else -1,
                                          row["event_id"]), reverse=True)
        else:
            filtered.sort(key=lambda row: (row.get("event_session") or "", row["event_id"]), reverse=True)
        return filtered

    def event_page(self, params):
        with self.lock:
            page, limit = int(params.get("page", "1")), int(params.get("limit", "12"))
            if page < 1 or not 1 <= limit <= 100:
                raise ValueError("Invalid page or page size")
            rows = self.filtered_events(params)
            page = min(page, max(1, math.ceil(len(rows) / limit)))
            fields = {"event_id", "ticker", "company", "sector", "event_session", "ar0", "signed_post_car",
                      "sample_status", "primary_reason", "timing_class", "initial_magnitude_gap_pp",
                      "nonstandard_disclosure_flag", "discrepancy_changes_session", "initial_sign"}
            return {"total": len(rows), "page": page, "limit": limit,
                    "items": [{key: row.get(key) for key in fields} for row in rows[(page-1)*limit:page*limit]]}

    def event(self, event_id):
        with self.lock:
            if event_id not in self.by_id:
                raise KeyError("Event not found")
            row = self.by_id[event_id]
            pair = self.pair_by_event.get(event_id)
            return clean({"event": {key: value for key, value in row.items() if key in EVENT_FIELDS or key == "sample_status"},
                          "returns": self.windows.get(event_id, []), "pair": pair,
                          "control": self.controls.get(pair["control_id"]) if pair else None,
                          "control_returns": self.control_windows.get(pair["control_id"], []) if pair else []})

    def evidence(self):
        with self.lock:
            discrepant = [row for row in self.events if row.get("timestamp_discrepancy")]
            changed = [row for row in discrepant if row.get("discrepancy_changes_session")]
            fields = ("event_id", "ticker", "raw_acceptance_timestamp", "verified_acceptance_timestamp",
                      "api_minus_verified_seconds", "raw_api_session", "event_session", "timestamp_source")
            identity = csv_rows(self.interim / "historical_identity.csv")
            return clean({"discrepancy_count": len(discrepant), "session_change_count": len(changed),
                          "session_changes": [{key: row.get(key) for key in fields} for row in changed],
                          "identity_total": len(identity),
                          "identity_verified": sum(bool(row.get("historical_cover_verified")) for row in identity),
                          "amendments": len(csv_rows(self.interim / "amendments.csv")),
                          "unresolved_items": len(csv_rows(self.interim / "unresolved_items.csv")),
                          "reviews": csv_rows(self.root / self.config["paths"]["timing_review"]),
                          "failures": json_file(self.processed / "source_failures.json", []),
                          "price_issues": csv_rows(self.processed / "price_quality.csv")})


class JobManager:
    """Single worker, fixed command arguments, persisted logs. Never executes browser-supplied code."""
    def __init__(self, config, runner=None, on_complete=None):
        self.config, self.root = config, Path(config["root"])
        self.folder = self.root / "reports/ui-runs"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = []
        self.active = None
        self.runner = runner or self._subprocess
        self.on_complete = on_complete
        for path in sorted(self.folder.glob("*/job.json"), reverse=True)[:20]:
            try:
                job = json_file(path)
                if job["status"] in {"queued", "running"}:
                    job.update(status="interrupted", detail="The previous server session ended during this task.",
                               finished_at=datetime.now(timezone.utc).isoformat())
                    self._persist(job)
                job["lines"] = []
                self.jobs.append(job)
            except (OSError, ValueError, KeyError):
                continue

    def commands(self, action, folder):
        config = str(self.config["config_path"])
        if action == "tests":
            return [[sys.executable, "-m", "eventstudy", "validate", "--config", config],
                    [sys.executable, "-m", "pytest", "-q", f"--junitxml={folder / 'tests.xml'}"]]
        if action == "demo":
            return [[sys.executable, "-m", "eventstudy", "demo", "--offline", "--output", str(folder / "demo")]]
        if action == "reproduce":
            return [[sys.executable, str(self.root / "scripts/check_cached_reproduction.py")]]
        if action == "report":
            return [[sys.executable, "-m", "eventstudy", "report", "--config", config]]
        raise ValueError("Unknown research task")

    def start(self, action):
        if action not in TASKS:
            raise ValueError("Unknown research task")
        with self.lock:
            if self.active is not None:
                raise RuntimeError("A task is already running. Wait for it to finish.")
            job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(3)
            folder = self.folder / job_id
            folder.mkdir()
            job = {"id": job_id, "action": action, **TASKS[action], "status": "queued",
                   "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None,
                   "exit_code": None, "lines": [], "tests": None}
            self.jobs.insert(0, job)
            self.active = job
            self._persist(job)
            threading.Thread(target=self._work, args=(job, folder), daemon=True).start()
            return self._public(job)

    def _persist(self, job):
        path = self.folder / job["id"] / "job.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({k: v for k, v in job.items() if k != "lines"}, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _line(self, job, text):
        with self.lock:
            job["lines"].append(text.rstrip())
            job["lines"] = job["lines"][-500:]
        with (self.folder / job["id"] / "output.log").open("a", encoding="utf-8") as handle:
            handle.write(text.rstrip() + "\n")

    def _subprocess(self, command, emit):
        environment = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        process = subprocess.Popen(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace", env=environment, **options)
        for line in process.stdout:
            emit(line)
        return process.wait()

    def _work(self, job, folder):
        try:
            with self.lock:
                job["status"] = "running"
                self._persist(job)
            code = 0
            for step, command in enumerate(self.commands(job["action"], folder), 1):
                self._line(job, f"Step {step}: {TASKS[job['action']]['title']}")
                code = self.runner(command, lambda line: self._line(job, line))
                if code:
                    break
            if job["action"] == "tests" and (folder / "tests.xml").exists():
                import xml.etree.ElementTree as ET
                tree = ET.parse(folder / "tests.xml").getroot()
                suites = [tree] if tree.tag == "testsuite" else list(tree)
                job["tests"] = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
                                for key in ("tests", "failures", "errors", "skipped")}
            if code == 0 and self.on_complete:
                self.on_complete()
            with self.lock:
                job.update(status="passed" if code == 0 else "failed", exit_code=code)
        except Exception as exc:
            self._line(job, f"{type(exc).__name__}: {exc}")
            with self.lock:
                job.update(status="failed", exit_code=1)
        finally:
            with self.lock:
                job["finished_at"] = datetime.now(timezone.utc).isoformat()
                self._persist(job)
                self.active = None

    def _public(self, job):
        result = {key: value for key, value in job.items() if key != "lines"}
        lines = job.get("lines", [])
        if not lines:
            path = self.folder / job["id"] / "output.log"
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:] if path.exists() else []
        result["lines"] = list(lines[-200:])
        return result

    def list(self):
        with self.lock:
            return {"active_id": self.active["id"] if self.active else None,
                    "tasks": TASKS, "jobs": [self._public(job) for job in self.jobs[:20]]}


class ResearchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, config, runner=None):
        if address[0] != "127.0.0.1":
            raise ValueError("The research desk binds only to 127.0.0.1")
        self.config = config
        self.data = ResearchData(config)
        self.jobs = JobManager(config, runner=runner, on_complete=self.data.reload)
        self.token = secrets.token_urlsafe(32)
        self.instance_id = secrets.token_hex(12)
        self.project_id = project_id(config)
        self.closing = False
        super().__init__(address, DeskHandler)


class DeskHandler(BaseHTTPRequestHandler):
    server_version = "ResearchDesk/1.0"
    timeout = 10

    def log_message(self, message, *args):
        LOG.debug(message, *args)

    def _same_host(self):
        port = self.server.server_port
        return self.headers.get("Host", "") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _send(self, status, content, mime="application/json", filename=None):
        if isinstance(content, (dict, list)):
            content = json.dumps(clean(content), allow_nan=False).encode("utf-8")
        elif isinstance(content, str):
            content = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Research-App", APPLICATION)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self._same_host():
            return self._send(421, {"error": "Use the local research-desk address"})
        path = unquote(urlparse(self.path).path)
        params = {key: value[0] for key, value in parse_qs(urlparse(self.path).query).items()}
        try:
            if path == "/":
                html = (ASSETS / "index.html").read_text(encoding="utf-8").replace("__SESSION_TOKEN__", self.server.token)
                return self._send(200, html, "text/html")
            if path in {"/static/app.js", "/static/style.css", "/static/mark.svg"}:
                mime = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}[Path(path).suffix]
                return self._send(200, (ASSETS / Path(path).name).read_bytes(), mime)
            if path == "/api/overview":
                return self._send(200, self.server.data.overview())
            if path == "/api/health":
                return self._send(200, {"application": APPLICATION, "status": "ready",
                                        "project_id": self.server.project_id,
                                        "instance_id": self.server.instance_id, "pid": os.getpid()})
            if path == "/api/session":
                return self._send(200, {"token": self.server.token, "instance_id": self.server.instance_id})
            if path == "/api/events":
                if params.get("format") == "csv":
                    with self.server.data.lock:
                        rows = self.server.data.filtered_events(params)
                        fields = ["event_id", "ticker", "company", "sector", "event_session", "ar0", "signed_post_car",
                                  "sample_status", "primary_reason", "initial_magnitude_gap_pp"]
                        output = io.StringIO(newline="")
                        writer = csv.DictWriter(output, fields, extrasaction="ignore")
                        writer.writeheader()
                        writer.writerows(rows)
                    return self._send(200, output.getvalue(), "text/csv", "filtered-events.csv")
                return self._send(200, self.server.data.event_page(params))
            if path.startswith("/api/event/"):
                return self._send(200, self.server.data.event(path.removeprefix("/api/event/")))
            if path == "/api/evidence":
                return self._send(200, self.server.data.evidence())
            if path == "/api/jobs":
                return self._send(200, {**self.server.jobs.list(), "session_token": self.server.token,
                                        "instance_id": self.server.instance_id,
                                        "data_revision": self.server.data.revision})
            if path.startswith("/api/document/") and path.removeprefix("/api/document/") in DOCUMENTS:
                key = path.removeprefix("/api/document/")
                file = self.server.data.root / DOCUMENTS[key]
                return self._send(200, {"key": key, "text": file.read_text(encoding="utf-8")})
            if path.startswith("/download/") and path.removeprefix("/download/") in DOWNLOADS:
                key = path.removeprefix("/download/")
                file = self.server.data.root / DOWNLOADS[key]
                mime = "text/csv" if key.endswith(".csv") else "application/json" if key.endswith(".json") else "text/markdown"
                return self._send(200, file.read_bytes(), mime, key)
            if path.startswith("/figures/") and re.fullmatch(r"[a-z_]+\.png", path.removeprefix("/figures/")):
                file = self.server.data.root / self.server.config["paths"]["reports"] / "figures" / Path(path).name
                return self._send(200, file.read_bytes(), "image/png")
            return self._send(404, {"error": "Not found"})
        except (FileNotFoundError, KeyError):
            return self._send(404, {"error": "This evidence is not available in the saved study"})
        except (ValueError, TypeError):
            return self._send(400, {"error": "Invalid request parameters"})

    def do_POST(self):
        # Drain a bounded request before replying, including authentication failures.
        # Closing a Windows socket with unread POST bytes can reset it before the
        # client receives the intended 403/400 response.
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024:
                raise ValueError("Invalid body length")
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("Incomplete body")
        except (ValueError, OSError):
            return self._send(400, {"error": "Invalid task request body"})
        port = self.server.server_port
        origin = self.headers.get("Origin")
        if (not self._same_host() or origin not in {None, f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
                or not hmac.compare_digest(self.headers.get("X-Research-Token", ""), self.server.token)):
            return self._send(403, {"error": "Open the local desk and retry the task"})
        if self.path not in {"/api/jobs", "/api/shutdown"} or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._send(400, {"error": "Invalid task request"})
        try:
            payload = json.loads(body)
            if self.path == "/api/shutdown":
                if payload != {}:
                    raise ValueError("Invalid shutdown request")
                with self.server.jobs.lock:
                    if self.server.jobs.active:
                        raise RuntimeError("Wait for the current research task to finish before closing the desk.")
                    self.server.closing = True
                    self._send(200, {"status": "closing"})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return None
            if not isinstance(payload, dict) or set(payload) != {"action"} or not isinstance(payload["action"], str):
                raise ValueError("Invalid task")
            with self.server.jobs.lock:
                if self.server.closing:
                    raise RuntimeError("The desk is closing. Reopen it before starting another task.")
                return self._send(202, self.server.jobs.start(payload["action"]))
        except (ValueError, TypeError, UnicodeError):
            return self._send(400, {"error": "Choose one of the available research tasks"})
        except RuntimeError as exc:
            return self._send(409, {"error": str(exc)})


def project_id(config):
    return hashlib.sha256(os.path.normcase(str(Path(config["root"]).resolve())).encode()).hexdigest()[:20]


def running_desk(config, port):
    """Identify this project's service; never reuse an unrelated listener on the chosen port."""
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}/api/health", timeout=.7) as response:
            status = json.load(response)
    except HTTPError as exc:
        raise ValueError(f"Port {port} is in use by another app. Use --port 8766.") from exc
    except (URLError, TimeoutError, ConnectionError, OSError):
        return None
    except ValueError as exc:
        raise ValueError(f"Port {port} is not serving this research desk. Use --port 8766.") from exc
    if (not isinstance(status, dict) or status.get("application") != APPLICATION
            or status.get("project_id") != project_id(config)):
        raise ValueError(f"Port {port} belongs to another app or project. Use --port 8766.")
    return status


def open_desk(config, port=8765, open_browser=True, timeout=30):
    """Launch a persistent local service, or reopen the same running project."""
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    status = running_desk(config, port)
    reused = bool(status)
    if not status:
        log_path = Path(config["root"]) / "reports/ui-server.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        options = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
                   if os.name == "nt" else {"start_new_session": True})
        command = [sys.executable, "-m", "eventstudy", "serve", "--config", str(config["config_path"]),
                   "--port", str(port), "--no-browser"]
        with log_path.open("a", encoding="utf-8") as output:
            process = subprocess.Popen(command, cwd=config["root"], stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, **options)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = running_desk(config, port)
            if status:
                break
            if process.poll() is not None:
                raise ValueError("The research desk could not start. See reports/ui-server.log.")
            time.sleep(.15)
        if not status:
            process.terminate()
            raise ValueError("The research desk did not become ready. See reports/ui-server.log and retry.")
    address = f"http://127.0.0.1:{port}"
    if open_browser:
        webbrowser.open(address)
    return {"status": "reopened" if reused else "started", "url": address, "pid": status["pid"]}


def close_desk(config, port=8765):
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    if not running_desk(config, port):
        return {"status": "already_closed"}
    address = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))
    with opener.open(address + "/api/session", timeout=5) as response:
        token = json.load(response)["token"]
    request = Request(address + "/api/shutdown", data=b"{}", method="POST",
                      headers={"Content-Type": "application/json", "Origin": address, "X-Research-Token": token})
    try:
        with opener.open(request, timeout=5) as response:
            return json.load(response)
    except HTTPError as exc:
        payload = json.loads(exc.read())
        raise ValueError(payload.get("error", "The research desk could not close.")) from exc


def serve(config, port=8765, open_browser=True):
    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535")
    try:
        server = ResearchServer(("127.0.0.1", port), config)
    except OSError as exc:
        raise ValueError(f"Could not open local port {port}. Close the existing desk or use --port 8766.") from exc
    address = f"http://127.0.0.1:{server.server_port}"
    print(f"Research desk: {address}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
    if open_browser:
        threading.Timer(.5, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return {"status": "closed", "url": address}

