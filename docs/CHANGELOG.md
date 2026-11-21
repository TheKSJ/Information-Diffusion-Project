# Build changes

## Final acceptance check — 29 October 2026

- A fresh full-suite run exposed a Windows connection abort when rejecting a POST before
  consuming its request body. The handler now drains a bounded body before authentication
  responses and explicitly closes the connection. Added a deterministic regression test;
  50 real rejected shutdown requests returned HTTP 403 without a connection reset.
- Retained the failed verification run and its output in Run history. The extended suite is
  now 104 cases, including the optional nine-check JavaScript regression runner.
- Added `docs/QUICK_TEST.md` with acceptance outputs, restart instructions, and the research
  review remaining before publication. Fresh evidence is in `reports/final-check-2026-10-29/`.

## Frontend repair — 19 October 2026

- Corrected the unusable handoff where the browser remained visible after its server stopped.
  Added a persistent background launcher, safe project-specific reuse, a close command and
  health/session endpoints. A running research task blocks shutdown.
- Replaced missing sidebar labels with readable workspace tabs; rebuilt contrast, text sizing,
  chart sizing and narrow-screen layouts. Event selection now reveals the inspector.
- Added visible disconnection and automatic recovery, token renewal after restart, a task
  submission latch and safe handling of lost responses without retrying task submissions.
- Corrected stale search/filter responses, loading-state pagination/export, zero-gap sorting,
  out-of-range pages and actual in-window/valid-observation funnel filters.
- A missing plot value now breaks its line; unavailable values are not converted to zero.
  Job success is announced only after data refresh finishes; interrupted history is persisted.
- Added 14 Python regression cases (one runs nine JavaScript client checks). The full suite
  now has 103 cases. Actual restart/recovery, browser controls and scientific-output preservation
  are checked separately in `reports/frontend-repair-2026-10-19/`.

## Local research desk — 19 October 2026

- Added an explicitly requested local frontend after the original command-line build. The
  fixed study design, source inputs, financial calculations and matching rules are unchanged.
- Added four connected views: overview and uncertainty; searchable event/control inspection;
  timing, identity and source evidence; and task execution with real logs and saved history.
- Added `eventstudy serve` and `Open Research Desk.cmd`, with bundled static assets and no
  additional runtime dependencies. The server binds to loopback, requires a same-origin
  session token for tasks, and serves only allowlisted evidence. No cloud services or publishing.
- Added 21 checks for evidence fidelity, filters, missing values, file/host/token boundaries,
  fixed commands, job exclusion, failures, recovery and actual test-count parsing.
- Verification results and the comparison to pre-frontend scientific outputs are recorded in
  `reports/frontend-verification-2026-10-19/`. The original 68-test verification is historical;
  the extended suite contains 89 tests.

## 0.1.0 — 18 October 2026

- Locked the requested primary design before empirical calculation.
- Implemented original 8-K discovery, historical pagination, local-time timestamp authority,
  annual-cover identity checks, explicit adjusted prices, matched controls and cluster inference.
- Preserved boundary filings, amendments, unknown metadata, failures and unmatched events.
- Corrected an initial local installation attempt made before src existed; installation was
  repeated after the package sources were created. No empirical results existed at that point.
- Removed unused imports found by the static checker. No numerical outputs changed.
- Grouped filing rows by issuer once to avoid repeated reconstruction of large SEC ledgers.
  Selection rules and arithmetic are unchanged; tested through deterministic output comparisons.
- Removed hidden inline-XBRL headers from audit excerpts and centered filing evidence on
  Item 2.02. This improves evidence review without changing metadata-based event classification.
- Moved schema generation after table creation so cached reruns include the same output schemas.
  Corrected before the first genuine numerical analysis; no genuine result was replaced.
- Citigroup's five annual covers explicitly incorporate Exhibit 99.01 for registered securities.
  Initial identity parsing did not follow that reference and excluded C. Added a bounded
  incorporated-exhibit path, tested it and verified all five genuine exhibits. The original
  failure records and initial diagnostic estimate remain in reports/initial_identity_failures.csv
  and reports/initial_build_pass/. The initial pass is a build diagnostic, not frozen final evidence.
- Added input/code fingerprints at run start and an end-of-run consistency check after an
  identity refresh overlapped the initial diagnostic. Concurrent input changes now invalidate
  the pass. Final results are produced sequentially from stable, corrected input ledgers.

