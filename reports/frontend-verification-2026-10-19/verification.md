# Local research desk verification — 19 October 2026

**Result: passed.** The requested local frontend connects to the existing study and can
execute all four supported research tasks. The study's scientific outputs are preserved.

## Open and try it

Double-click `Open Research Desk.cmd` in the repository folder. It opens the default browser
at `http://127.0.0.1:8765`. Keep the launcher window open; close it or press Ctrl+C when done.
The development preview server is stopped after verification, leaving this port available.

Start with **Run center → Run verification**, then use **Event explorer** to search `AAPL`.
Select an observation and inspect its real matched pair, return window and SEC evidence.
**Run demo** uses isolated synthetic fixtures. **Run reproduction** uses the genuine cached
inputs and can take several minutes. **Run report** regenerates the technical report and
its five figures. Output and history remain under `reports/ui-runs/`.

## Checks completed

| Check | Observed result |
|---|---|
| Full suite, launched through the browser | 89 passed; 0 failed, errors or skips |
| New desk/backend cases | 21 passed |
| Configuration validation | 30 fixed companies; 100 estimation observations |
| Offline demonstration button | Passed; 60 synthetic matched pairs in its own run folder |
| Report button | Passed; technical report plus five figures |
| Cached reproduction button | Passed; all 36 processed files byte-identical |
| Pre-frontend versus updated analysis | 35 scientific outputs unchanged; only source-code provenance in run_manifest.json changed |
| Static Python checks and JavaScript syntax | Passed |
| Installed runtime dependency consistency | Passed |
| Build distribution | Passed; all four bundled web assets match final source |

The 14 test warnings originate from existing matplotlib/pyparsing integration; the suite
still exits successfully. An initial packaging check without build isolation failed because
the local environment lacked `bdist_wheel`. Repeating with the project's declared isolated
build requirements succeeded; runtime dependencies were not changed.

## Browser verification

All four views were opened in the local in-app browser. The AAPL search returned 10 qualifying
events, with its latest pair showing signed post CARs of approximately +3.09% and +4.06%, a
−0.970 percentage-point pair difference. Filters, empty results, exclusions and unavailable
returns were inspected. The excluded filter returned 264 observations, including retained
out-of-window filings with missing analytical returns displayed as unavailable.

The evidence view displayed 487 timestamp discrepancies, both session-changing COST cases,
150/150 annual identity sources, 20 issuer-labelled disclosure reviews, and seven vendor
action flags. Methods and report dialogs rendered; the report exposed all five figure
references. The average/cumulative control updated the plot, subtitle and legend together.

Each task was launched using its actual browser control and observed to pass with an exit
code of zero. Other task controls were disabled while work was active. The narrow preview
layout, table scrolling and chart display were inspected. The browser console reported no
JavaScript errors during checks. Desktop layouts are implemented in CSS; this verification
does not claim a separate browser/device compatibility matrix.

## Evidence files

- `summary.json`: task records, source/asset hashes, reproduction result and browser checklist.
- `tests.xml`: complete extended-suite result.
- `live_api_checks.json`: genuine-data API counts and primary-value equality.
- `before_frontend_analysis.json` and `numerical_preservation.json`: preserved baseline and comparison.
- `cached_reproduction_check.json`: second genuine-data run, all 36 hashes equal.
- `packaging.json` and `wheel/`: distribution/asset verification, including the failed first attempt.
- `research-desk-preview.png`: captured local interface preview.

The interface does not resolve first-public release timing or weak matching. Those limitations
remain visible beside the result. No publication, deployment or repository push occurred.
