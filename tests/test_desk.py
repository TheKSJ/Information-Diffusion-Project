"""Research desk boundaries, evidence fidelity, and task lifecycle."""
import csv
import http.client
import io
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from eventstudy.desk import DeskHandler, JobManager, ResearchData, ResearchServer, clean, csv_rows, open_desk, running_desk
from eventstudy.storage import write_csv, write_json


@pytest.fixture
def desk_config(tmp_path):
    config = {"root": tmp_path, "config_path": tmp_path / "configs/study.yaml",
              "paths": {"data": "data", "reports": "reports/live", "timing_review": "configs/timing_review.csv"},
              "study": {"start": "2021-01-01", "end": "2025-12-31"}}
    processed = tmp_path / "data/processed"
    events = [
        {"event_id": "a", "ticker": "AAA", "company": "Alpha", "sector": "Tech", "event_session": "2024-01-02",
         "ar0": .03, "signed_post_car": -.01, "primary_reason": None, "timestamp_discrepancy": True,
         "discrepancy_changes_session": True, "raw_api_session": "2024-01-03", "timestamp_verified": True},
        {"event_id": "b", "ticker": "BBB", "company": "Beta", "sector": "Bank", "event_session": "2025-02-03",
         "ar0": -.04, "signed_post_car": .02, "primary_reason": None},
        {"event_id": "c", "ticker": "AAA", "company": "Alpha", "sector": "Tech", "event_session": "2023-02-01",
         "ar0": .005, "primary_reason": "below_initial_threshold"},
    ]
    write_csv(processed / "event_ledger.csv", events)
    write_csv(processed / "matched_pairs.csv", [{"event_id": "a", "control_id": "ctrl", "magnitude_gap": .005,
                                                "difference": .012, "year_fallback": False}])
    write_csv(processed / "event_abnormal_returns.csv", [{"event_id": "a", "offset": 1, "abnormal_return": .008}])
    write_csv(processed / "control_abnormal_returns.csv", [{"control_id": "ctrl", "offset": 1, "abnormal_return": -.004}])
    write_json(processed / "run_summary.json", {"candidate_events": 3, "matched_controls": 1})
    write_json(processed / "primary_inference.json", {"estimate_pp": 1.2})
    write_csv(tmp_path / "configs/timing_review.csv", [{"event_id": "a", "reviewed": True}])
    return config


@pytest.fixture
def http_desk(desk_config):
    server = ResearchServer(("127.0.0.1", 0), desk_config, runner=lambda command, emit: 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, method="GET", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    yield server, request
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def wait_done(manager):
    deadline = time.monotonic() + 5
    while manager.list()["active_id"] and time.monotonic() < deadline:
        time.sleep(.01)
    assert manager.list()["active_id"] is None
    return manager.list()["jobs"][0]


def test_snapshot_preserves_values_and_exploration_does_not_refit(desk_config):
    data = ResearchData(desk_config)
    assert data.event("a")["event"]["ar0"] == .03
    assert data.event("a")["pair"]["difference"] == .012
    assert data.event("a")["control_returns"][0]["abnormal_return"] == -.004
    assert data.event("a")["event"]["timestamp_verified"] is True
    data.event_page({"q": "BBB"})
    assert data.overview()["primary"]["estimate_pp"] == 1.2
    assert data.evidence()["session_changes"][0]["raw_api_session"] == "2024-01-03"


@pytest.mark.parametrize("params,ids", [
    ({"status": "qualified"}, ["b", "a"]), ({"status": "matched"}, ["a"]),
    ({"status": "unmatched"}, ["b"]), ({"status": "excluded"}, ["c"]),
    ({"q": "alpha", "year": "2024"}, ["a"]), ({"sector": "Bank", "sign": "negative"}, ["b"]),
    ({"q": "no-such-company"}, []), ({"sort": "magnitude", "page": "2", "limit": "1"}, ["a"]),
])
def test_filters_pagination_and_empty_results(desk_config, params, ids):
    assert [row["event_id"] for row in ResearchData(desk_config).event_page(params)["items"]] == ids


def test_missing_is_not_zero_and_nonfinite_json_is_valid(tmp_path):
    path = tmp_path / "values.csv"
    path.write_text("ar0,beta,timestamp_verified\n,0,False\nNaN,1,True\n", encoding="utf-8")
    rows = csv_rows(path)
    assert rows[0] == {"ar0": None, "beta": 0, "timestamp_verified": False}
    assert rows[1]["ar0"] is None
    assert clean({"x": [float("nan"), float("inf"), 0]}) == {"x": [None, None, 0]}


def test_http_assets_csv_and_evidence(http_desk):
    server, request = http_desk
    status, headers, body = request("/")
    assert status == 200 and server.token.encode() in body and b"__SESSION_TOKEN__" not in body
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    for path in ("/static/app.js", "/static/style.css", "/static/mark.svg", "/api/overview"):
        assert request(path)[0] == 200
    status, headers, body = request("/api/events?status=matched&format=csv")
    rows = list(csv.DictReader(body.decode().splitlines()))
    assert status == 200 and rows[0]["ar0"] == "0.03" and len(rows) == 1
    assert "attachment" in headers["Content-Disposition"]
    assert json.loads(request("/api/event/a")[2])["event"]["sample_status"] == "matched"


@pytest.mark.parametrize("path", ["/.env", "/download/../../.env", "/static/../desk.py",
                                 "/api/document/../../.env", "/figures/../../.env", "/api/event/unknown"])
def test_private_files_and_unknown_evidence_not_served(http_desk, path):
    assert http_desk[1](path)[0] == 404


def test_http_task_token_origin_payload_and_host_boundaries(http_desk):
    server, request = http_desk
    payload = json.dumps({"action": "tests"})
    headers = {"Content-Type": "application/json", "X-Research-Token": server.token}
    assert request("/api/jobs", "POST", payload, {"Content-Type": "application/json"})[0] == 403
    assert request("/api/jobs", "POST", payload, {**headers, "Origin": "https://outside.example"})[0] == 403
    assert request("/api/overview", headers={"Host": "outside.example"})[0] == 421
    assert request("/api/jobs", "POST", '{"action":"tests","command":"whoami"}', headers)[0] == 400
    assert request("/api/jobs", "POST", '{"action":"arbitrary-code"}', headers)[0] == 400
    assert request("/api/jobs", "POST", payload, headers)[0] == 202
    assert wait_done(server.jobs)["status"] == "passed"
    assert request("/api/events?page=0")[0] == 400


def test_task_failure_exclusion_logs_and_restart_history(desk_config):
    entered, release = threading.Event(), threading.Event()

    def runner(command, emit):
        entered.set()
        assert release.wait(5)
        emit("A real failure message")
        return 7

    manager = JobManager(desk_config, runner=runner)
    manager.start("tests")
    assert entered.wait(5)
    with pytest.raises(RuntimeError, match="already running"):
        manager.start("demo")
    release.set()
    job = wait_done(manager)
    assert job["status"] == "failed" and job["exit_code"] == 7
    assert "A real failure message" in job["lines"]
    restarted = JobManager(desk_config)
    assert restarted.list()["jobs"][0]["status"] == "failed"
    assert restarted.list()["jobs"][0]["lines"] == job["lines"]
    with pytest.raises(ValueError):
        manager.start("shell")


def test_task_success_summary_is_from_junit_and_fixed_commands(desk_config):
    calls, completed = [], []

    def runner(command, emit):
        calls.append(command)
        if "pytest" in command:
            path = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--junitxml=")))
            path.write_text('<testsuites><testsuite tests="9" failures="0" errors="0" skipped="1"/></testsuites>')
        return 0

    manager = JobManager(desk_config, runner=runner, on_complete=lambda: completed.append(True))
    manager.start("tests")
    job = wait_done(manager)
    assert job["status"] == "passed" and job["tests"] == {"tests": 9, "failures": 0, "errors": 0, "skipped": 1}
    assert completed == [True] and calls[0][1:4] == ["-m", "eventstudy", "validate"]
    assert "demo" in manager.commands("demo", manager.folder)[0]
    assert manager.commands("reproduce", manager.folder)[0][-1].endswith("check_cached_reproduction.py")
    assert "report" in manager.commands("report", manager.folder)[0]


def test_server_cannot_listen_on_external_interface(desk_config):
    with pytest.raises(ValueError, match="127.0.0.1"):
        ResearchServer(("0.0.0.0", 8765), desk_config)


def test_health_reopen_and_session_after_restart(http_desk, desk_config, monkeypatch):
    server, request = http_desk
    monkeypatch.setattr("eventstudy.desk.subprocess.Popen", lambda *a, **k: pytest.fail("Reopen spawned a second desk"))
    health = json.loads(request("/api/health")[2])
    assert health["application"] == "information-diffusion-research-desk"
    assert "root" not in health and "token" not in health
    assert open_desk(desk_config, server.server_port, open_browser=False)["status"] == "reopened"
    old_token = server.token
    server.token = "rotated-token"
    session = json.loads(request("/api/session")[2])
    jobs = json.loads(request("/api/jobs")[2])
    assert session["token"] == jobs["session_token"] == "rotated-token"
    assert session["instance_id"] == jobs["instance_id"] == health["instance_id"]
    assert jobs["data_revision"] == server.data.overview()["revision"]
    headers = {"Content-Type": "application/json", "X-Research-Token": old_token}
    assert request("/api/jobs", "POST", '{"action":"tests"}', headers)[0] == 403
    headers["X-Research-Token"] = session["token"]
    assert request("/api/jobs", "POST", '{"action":"tests"}', headers)[0] == 202
    wait_done(server.jobs)


def test_reopen_rejects_another_project(http_desk, desk_config):
    server, _ = http_desk
    server.project_id = "another-project"
    with pytest.raises(ValueError, match="another app or project"):
        running_desk(desk_config, server.server_port)


def test_funnel_filters_and_out_of_range_pagination(desk_config):
    data = ResearchData(desk_config)
    assert data.event_page({"status": "in_window"})["total"] == 3
    assert data.event_page({"status": "valid"})["total"] == 3
    outside = dict(data.events[0], event_id="outside", event_session="2026-01-01",
                   primary_reason="outside_research_sessions", initial_magnitude_gap_pp=None)
    data.events.append(outside)
    assert data.event_page({"status": "all"})["total"] == 4
    assert data.event_page({"status": "in_window"})["total"] == 3
    assert data.event_page({"status": "valid"})["total"] == 3
    page = data.event_page({"page": "999", "limit": "2"})
    assert page["page"] == 2 and len(page["items"]) == 2
    data.events[0]["initial_magnitude_gap_pp"] = 0
    assert data.event_page({"sort": "gap"})["items"][0]["event_id"] == "a"


@pytest.mark.parametrize("params", [{"status": "unknown"}, {"sign": "unknown"}])
def test_invalid_filters_are_rejected(desk_config, params):
    with pytest.raises(ValueError):
        ResearchData(desk_config).event_page(params)


def test_success_is_not_announced_until_snapshot_refresh_finishes(desk_config):
    entered, release = threading.Event(), threading.Event()

    def refresh():
        entered.set()
        assert release.wait(5)

    manager = JobManager(desk_config, runner=lambda *a: 0, on_complete=refresh)
    manager.start("report")
    assert entered.wait(5)
    during = manager.list()
    assert during["active_id"] and during["jobs"][0]["status"] == "running"
    release.set()
    assert wait_done(manager)["status"] == "passed"


def test_interrupted_history_is_persisted(desk_config):
    folder = desk_config["root"] / "reports/ui-runs/old-job"
    folder.mkdir(parents=True)
    write_json(folder / "job.json", {"id": "old-job", "status": "running", "started_at": "old"})
    first = JobManager(desk_config).list()["jobs"][0]
    second = JobManager(desk_config).list()["jobs"][0]
    assert first["status"] == second["status"] == "interrupted"
    assert first["finished_at"] == second["finished_at"]
    assert json.loads((folder / "job.json").read_text())["status"] == "interrupted"


def test_shutdown_requires_token_and_refuses_an_active_task(http_desk):
    server, request = http_desk
    headers = {"Content-Type": "application/json", "X-Research-Token": server.token}
    assert request("/api/shutdown", "POST", "{}", {"Content-Type": "application/json"})[0] == 403
    server.jobs.active = {"id": "busy"}
    try:
        assert request("/api/shutdown", "POST", "{}", headers)[0] == 409
        assert request("/api/health")[0] == 200
    finally:
        server.jobs.active = None


def test_background_launcher_waits_for_its_own_health(desk_config, monkeypatch):
    statuses = iter([None, {"pid": 1234}])
    launches = []
    monkeypatch.setattr("eventstudy.desk.running_desk", lambda *a: next(statuses))
    monkeypatch.setattr("eventstudy.desk.subprocess.Popen", lambda *a, **k: launches.append((a, k)))
    result = open_desk(desk_config, 8765, open_browser=False)
    assert result["status"] == "started" and result["pid"] == 1234
    command = launches[0][0][0]
    assert command[1:4] == ["-m", "eventstudy", "serve"] and "--no-browser" in command
    assert launches[0][1]["cwd"] == desk_config["root"]


def test_background_launcher_failure_is_actionable(desk_config, monkeypatch):
    class FailedProcess:
        def poll(self):
            return 1

    monkeypatch.setattr("eventstudy.desk.running_desk", lambda *a: None)
    monkeypatch.setattr("eventstudy.desk.subprocess.Popen", lambda *a, **k: FailedProcess())
    with pytest.raises(ValueError, match="reports/ui-server.log"):
        open_desk(desk_config, 8765, open_browser=False)


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_launcher_rejects_invalid_port(desk_config, port):
    with pytest.raises(ValueError):
        open_desk(desk_config, port, open_browser=False)


def test_rejected_post_is_drained_before_responding():
    handler = DeskHandler.__new__(DeskHandler)
    handler.server = SimpleNamespace(server_port=8765, token="valid-token")
    handler.headers = {"Host": "127.0.0.1:8765", "Content-Length": "2", "Content-Type": "application/json"}
    handler.rfile = io.BytesIO(b"{}")
    responses = []
    handler._send = lambda status, body: responses.append((status, handler.rfile.tell()))
    handler.do_POST()
    assert responses == [(403, 2)], "The 403 must be sent only after consuming the request body"
