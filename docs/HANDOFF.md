# Build handoff — 18 October 2026

## 1. Build status

**Complete local implementation and genuine 30-company analysis.** Tests, offline demo,
source audit, numerical reconciliation and cached reproducibility checks were executed.
No push, deployment or publication occurred. The local repository has no remote.
This is technical evidence for Karol's audit, not final authored research conclusions.

The independently timed first-public-release sensitivity is **unavailable**, with zero
verified first-public release clocks. This is a documented evidence limitation, not synthetic
substitution or a claim that filing acceptance equals first release.

## 2. Implementation

Installable Python src package with CLI, SEC collection/pagination, caching/rate limiting/
retry handling, exact item classification, timestamp reconciliation, XNYS alignment,
historical-identity corroboration, explicit adjusted prices, validation, pre-event OLS,
AR/CAR arithmetic, screened controls, deterministic matching, issuer-cluster inference,
seeded cluster bootstrap, calendar-quarter sensitivity, robustness calculations and reporting.
Input/code fingerprints detect concurrent changes. CSV/JSON checkpoints use atomic replacement.

Separate ledgers retain all filings, amendments, unresolved metadata, candidates, verified
timestamps, included/excluded observations, screening failures, unmatched events and source
provenance. Five figures, descriptive tables, schemas and three worked numerical cases exist.

## 3. Actual data

| Observation | Count |
|---|---:|
| Fixed companies requested / with price data | 30 / 30 |
| Price series including SPY | 31 |
| SEC filing records discovered, all forms and discovery buffer | 302,816 |
| Unique original Item 2.02 candidates, including buffer | 654 |
| Authoritative acceptance timestamps verified | 654 |
| Verified candidates aligned within 2021–2025 | 634 |
| Valid unique ticker-session analytical observations | 633 |
| Qualifying observations with abs(AR0) ≥ 2% | 390 |
| Matched pairs / unique controls | 260 / 260 |
| Qualifying events left unmatched and retained descriptively | 130 |
| Issuers / calendar quarters in paired analysis | 30 / 20 |
| 8-K/A filings separately recorded, all item combinations | 33 |
| Unresolved original 8-K item metadata | 0 |
| Annual identity sources corroborated | 150 / 150 |
| Manual filing/principal-exhibit source reviews | 20 |
| Independently established first-public-release clocks | 0 |
| Raw/source snapshots checked | 1,165 |
| Recorded live source-operation failures | 0 |

The mutually exclusive 654-candidate waterfall is **20 outside the research sessions + 1
duplicate ticker-session + 243 below the initial threshold + 390 included = 654**.
The additional 130 unmatched events are a subset of the 390, not another waterfall deduction.
Zero events were lost to the 100-observation estimation requirement or missing observation
returns in this downloaded snapshot. The universe was not replaced or reduced.

## 4. Research output

Primary estimand: mean(event signed CAR[+1,+5] minus matched-control signed CAR[+1,+5]).
Returns are decimal internally; the following differences are in **percentage points**.

| Primary quantity | Actual result |
|---|---:|
| Mean paired difference | +0.501064 pp |
| Issuer-cluster two-sided 95% CI | [+0.135709, +0.866418] pp |
| One-sided continuation p-value | 0.00444573 |
| Corresponding two-sided p-value | 0.00889145 |
| Issuer clusters / t degrees of freedom | 30 / 29 |
| Issuer bootstrap percentile 95% CI, diagnostic | [+0.159776, +0.849645] pp |
| Calendar-quarter sensitivity 95% CI | [−0.010242, +1.012369] pp |
| Calendar-quarter one-sided / two-sided p-values | 0.0271526 / 0.0543052 |

The sample has a positive average conditional event-minus-control difference under the
primary specification. The quarter-based two-sided interval crosses zero. These calculations
do not establish first-release diffusion, causality, market inefficiency or a profitable strategy.

Prespecified sensitivities, all exploratory and not substitutes for the primary test:

| Specification | Pairs | Difference (pp) | Issuer-cluster one-sided p |
|---|---:|---:|---:|
| 1.5% threshold | 351 | +0.462927 | 0.00554853 |
| 2.5% threshold | 176 | +0.544079 | 0.0393383 |
| Non-overlap, no other economic 8-K items | 162 | +0.692238 | 0.00611405 |
| Simple market-adjusted model | 281 | +0.659921 | 0.0121221 |
| Independently verified first-release subset | unavailable | — | — |

The 2.5% threshold's two-sided interval crosses zero. Exact intervals, quarter checks,
bootstrap diagnostics and unmatched counts are in `reports/live/robustness.json` and
`results_table.csv`. No final publication narrative was generated.

## 5. Validation

- **68 tests passed, 0 failed.** Fourteen upstream matplotlib/pyparsing deprecation warnings;
  no suppressed failures. `reports/test_results.xml` and `coverage.json` preserve test evidence.
- Static checks passed; installed dependency checks reported no broken requirements.
- Offline end-to-end demo ran with six synthetic issuers, 60 simulated events and 60 pairs.
  Network access is prohibited in the integration tests; fixture outputs are explicitly isolated.
- Full genuine cached rerun: **36 processed files identical, zero differences**, including
  analytical datasets, inference, schemas, manifests and figures. See
  `reports/cached_reproduction_check.json`.
- Independent closed-form OLS/price/AR/CAR calculations passed for AAPL, JPM and CAT.
  All 260 matched pair differences were independently resummed; maximum decimal-return
  residual 6.01×10⁻¹³. Three-case coefficient residuals remain below 4.33×10⁻¹² and are
  visible, consistent with 12-significant-digit analytical CSV serialization.
- All 1,165 raw snapshot hashes passed. Inspected five Citigroup incorporated identity
  exhibits, 20 Item 2.02/principal-exhibit passages, and actual timestamp alignment cases.
  Both COST day-changing discrepancies were checked against cached index Accepted text.
- HTTP 403/429/5xx, partial network failures, missing prices, malformed metadata, empty
  samples, early closes, DST, null/continuation/reversal simulations and insufficient-cluster
  behavior were tested with fixtures; those are not claimed as observed live incidents.

Read `docs/numerical_walkthrough.md` and `reports/manual_numerical_audit.json` for calculations.
All five genuine-data figures were visually inspected for sample labels, axes, units and CIs.

## 6. Data issues and preserved failures

There are **487 API-versus-index timestamp discrepancies** among 654 candidates: 331 differ
by 14,400 seconds, 156 by 18,000 seconds, and 167 agree. Two COST discrepancies would
change the assigned session from Friday to Monday if the raw API value were trusted.
Authoritative Eastern time is used per filing; no universal offset correction is applied.

The seven price-quality records are vendor-reported corporate split/action flags, not missing
prices or failed downloads. No unadjusted-price substitution or forward fill was used.
The detailed quality ledger is retained; do not infer that all corporate-action lineage has
been independently adjudicated.

The timing audit flags a nonstandard BMY Item 2.02 disclosure revising prior results'
presentation, plus examples containing guidance/dividend news. That filing remains under
the locked item-based rule. Unreviewed Item 2.02 filings may also be heterogeneous.

Initial identity parsing left C unresolved because its annual covers refer registered
securities to Exhibit 99.01. The repair followed those explicit references and corroborated
all five years. Original failures and initial diagnostic results remain in
`reports/initial_identity_failures.csv` and `reports/initial_build_pass/`. That diagnostic
overlapped an input refresh and is explicitly not a frozen final research run. The final
sequential run is reproducible. The initial estimate was +0.457907 pp on 258 pairs; the final
is +0.501064 pp on 260 pairs. See `docs/CHANGELOG.md` and `docs/source_audit.md`.

## 7. Repository and implementation choices

```text
pyproject.toml, requirements-lock.txt, README.md, .env.example, .gitignore
configs/       study.yaml, universe.csv, timing_review.csv
src/eventstudy/
  cli, collection, sec_client, prices, calendar, events, validation,
  market_model, controls, inference, robustness, pipeline, reporting,
  storage, demo, __init__, __main__
tests/         68 passing deterministic cases; clearly labelled synthetic fixtures
scripts/       cached replay, numerical audit, identity/timing audit, pilot analysis
data/raw/      immutable SEC/vendor snapshots, locally pinned and ignored by Git
data/interim/  discovery, identity, audit, amendments and source-failure ledgers
data/processed/ 36 verified analytical/reporting files
reports/live/  genuine-source evidence and five figures
reports/demo/  isolated synthetic evidence and five figures
docs/          design, methods, dictionary, limitations, audits, changelog, handoff
```

Use simple pandas/numpy/scipy calculations; statsmodels supplies an independent cluster-SE
test reference. No ML, trading engine, database service, frontend, cloud or paid API.
Same issuer/sign matching is mandatory; year fallback, no reuse, full-window screening and
no hidden caliper are documented. `.env`, raw/vendor datasets and the environment are ignored
by Git. No remote is configured and no commit or publication was made.

## 8. Exact commands

Run from the project directory. The local environment and contact file are already configured.
For a fresh copy, create `.venv`, install the lock, then install the package; fill `.env` with
your real SEC identity. Do not overwrite the existing private `.env` with the blank example.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ".[dev]"
.\.venv\Scripts\python.exe -m eventstudy --help
.\.venv\Scripts\python.exe -m eventstudy validate --config configs/study.yaml
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m eventstudy demo --offline
.\.venv\Scripts\python.exe -m eventstudy fetch --config configs/study.yaml --pilot
.\.venv\Scripts\python.exe -m eventstudy fetch --config configs/study.yaml
.\.venv\Scripts\python.exe -m eventstudy run --config configs/study.yaml
.\.venv\Scripts\python.exe -m eventstudy report --config configs/study.yaml
.\.venv\Scripts\python.exe scripts/audit_cached_analysis.py
.\.venv\Scripts\python.exe scripts/check_cached_reproduction.py
```

For raw-cache reconstruction use `fetch --offline`, then `run` and `report`. Neither `run`
nor `report` downloads data. Only run one SEC collector at a time; the limiter is process-global.
Exit codes: 0 success, 1 invalid/missing prerequisite, 2 partial collection or no matched sample.

## 9. Reproducibility

Python **3.11.9** on Windows; exact direct/transitive package versions in
`requirements-lock.txt`, with execution versions in `reports/live/environment.json`.
Key versions: pandas 2.2.3, numpy 2.2.6, scipy 1.15.3, statsmodels 0.14.4,
yfinance 0.2.66, exchange_calendars 4.11.2. Seed **20261018**; **5,000** bootstrap draws.

Raw bodies/snapshots have SHA-256 hashes and retrieval metadata. The run manifest records
configuration, fixed design, universe, timing reviews, dependency lock, implementation and
interim input hashes. Cached input/code stability was checked before finalization. The replay
compared all 36 processed files byte-for-byte successfully. Source snapshots are local;
review Yahoo's data licensing/personal-use restrictions before sharing vendor data. Share
derived analysis/source links rather than assuming redistribution rights.

## 10. Known limitations, in validity order

1. No independent first-public release clocks; daily prices cannot identify intraday diffusion.
2. Controls can be poorly matched: median initial-magnitude gap **1.1834 pp**, 95th percentile
   **8.6652 pp**, maximum **32.7248 pp**. **125/260** matches use another study year.
   These are serious comparability limits, not hidden successes. **130/390** qualifying events
   remain unmatched. No outcome-dependent rematching or silent new caliper was introduced.
3. Issuer/quarter dependence, overlapping announcements, concurrent guidance/dividends and
   unobserved news remain; the calendar sensitivity does not jointly solve all dependence.
4. Conditioning on realized AR0 and selecting 30 surviving large stocks limits identification
   and generalization. This is a retrospective conditional study, not a prospective strategy.
5. Model error/instability, SPY proxy limits, vendor revisions, corporate actions, annual-point
   identity evidence and unreviewed nonstandard disclosures remain. Do not invent explanations.
6. Sensitivities are exploratory. Quarter-based intervals and the higher threshold are weaker
   than the primary issuer test. No significance claim implies profitability or causality.

See `docs/limitations.md` for the full prioritized discussion.

## 11. Karol's next review

1. **Defend the arithmetic.** Reproduce the AAPL example from the raw adjusted closes, identify
   all 100 estimation sessions, and explain alpha/beta, AR0, additive post CAR and its sign.
   Explain why the JPM/CAT examples shown are below the primary threshold.
2. **Audit information timing and event meaning.** Inspect both COST index discrepancies,
   several original releases, the nonstandard BMY disclosure and concurrent-news examples.
   Distinguish release date, first-public time, EDGAR acceptance and aligned daily return.
3. **Evaluate the comparison before writing.** Inspect the worst magnitude gaps, year fallback
   and unmatched issuers/events; then reconcile issuer/quarter inference and sensitivities.
   Decide whether a separately versioned, justified design revision is warranted before making
   publication claims. Write the research argument and limitations yourself.

## 12. Requested local frontend — 19 October 2026

Karol explicitly requested a frontend for trying and inspecting this study after the initial
command-line delivery. This extends the original delivery scope; it does not change the
research design or calculation architecture. Nothing was published, deployed or pushed.

Double-click `Open Research Desk.cmd` in the repository. The desk opens at
`http://127.0.0.1:8765`. After the repair described below, it runs in the background and
reopens an existing instance. The equivalent command is `.venv\Scripts\python.exe -m
eventstudy open-desk --config configs/study.yaml`. Double-click `Close Research Desk.cmd`
to stop it after any current task completes. An occupied port can be changed with `--port 8766`.

The four views connect directly to the saved genuine-data outputs:

- **Study overview:** fixed primary estimate, issuer and quarter uncertainty, AAR/CAAR,
  source-to-sample counts, sector descriptives and all fixed sensitivity specifications.
- **Event explorer:** company/accession search, year/sector/status/sign filters, deterministic
  sorting, pagination and filtered CSV export. Each observation exposes its actual matched
  pair, cumulative AR window, model inputs, filing clock and SEC evidence links. Filtering
  never refits the study or changes the primary hypothesis.
- **Evidence & timing:** timestamp discrepancies and session changes, annual security identity,
  source fingerprints, all 20 disclosure reviews, vendor action flags and the research library.
- **Run center:** configuration plus tests; isolated offline synthetic demo; genuine cached
  reproduction; and saved-calculation report generation. Fixed commands execute one at a
  time. Actual exit codes, test counts, output and history persist under `reports/ui-runs/`.

The server uses the Python standard library and bundled HTML/CSS/JavaScript, adding no runtime
dependencies. It binds only to loopback, does not serve raw/vendor inputs or `.env`, and checks
host, origin and a per-session task token. The browser cannot submit commands or change design
inputs. Live collection remains a deliberate command-line workflow.

The extended suite has 89 passing tests, including 21 new interface/backend checks. Browser
verification and before/after analytical hashes are recorded in
`reports/frontend-verification-2026-10-19/`. Earlier sections describe the original build;
their dated 68-test result remains preserved as historical verification.

## 13. Frontend failure review and repair — 19 October 2026

Karol reported errors after delivery. The earlier browser page could remain visible after
the development server was stopped; task clicks then failed to fetch. Navigation labels in
the original sidebar were not visibly rendering in the in-app preview. The first verification
emphasized backend correctness and did not adequately cover this usable handoff failure.

The repaired desk uses a persistent, project-identified background service and readable tabs
within the workspace. It reports disconnection, disables task/export controls while offline,
reconnects automatically, renews rotated tokens after restart and prevents rapid duplicate
submissions. It never automatically retries a task POST whose response was lost.

Search updates state immediately, invalidates late responses and disables pagination/export
while loading. Selecting a row reveals the inspector on narrow screens. Funnel links now
filter to the actual in-window/valid sample. Missing plot points break the path rather than
being connected across a gap. The figure width and labels adjust to available screen space.
All numerical outputs and the original research limitations remain governed by the pipeline.

Added backend and dependency-free JavaScript regression coverage for these failure modes.
The extended suite contains 103 Python test cases, including a check running nine client
regressions when the optional local Node QA tool is available. Node is not a desk runtime
dependency. Repair evidence, real service restart checks and analytical comparisons are in
`reports/frontend-repair-2026-10-19/`. Earlier verification reports remain historical records.

## 14. Final acceptance — 29 October 2026

A fresh acceptance run found a Windows connection abort while rejecting a POST with an
unread request body. The handler now consumes the bounded body before rejection and sends
an explicit close header. A new regression covers response ordering; the first failed run
remains in Run history rather than being erased.

The current extended suite has 104 passing cases, including the runner for nine JavaScript
client checks. Rejected-request checks, genuine-data hashes, fresh task runs, restart recovery,
CSV export and final reproduction evidence are in `reports/final-check-2026-10-29/`.
Use `docs/QUICK_TEST.md` for exact clicks and expected outputs.

The fixed numerical study is unchanged. The Windows platform identifier changed between
19 and 29 October; Python and recorded package versions remain the same. The environment
and source-code manifests record this change. A second run in the current environment
reproduced all 36 processed files byte-for-byte.

The remaining work before publication is Karol's independent arithmetic/source review,
assessment of matching and timing limitations, and his own authored interpretation. No
first-public release clocks have been independently verified. These gaps are explicitly
disclosed; the software must not invent evidence or strengthen its claims to meet a deadline.
The project remains local, with no deployment, publication or repository push.

