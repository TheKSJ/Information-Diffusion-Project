# Final acceptance — 29 October 2026

**Local software status: passed; ready for Karol's acceptance review.** All four workflow
buttons were launched through the browser and finished successfully. The service was left
running locally. No deployment, publication or repository push occurred.

## Observed results

| Check | Result |
|---|---|
| Full automated suite | 104 passed; 0 failures, errors or skips |
| Client regression checks | Nine checks executed inside the Python suite |
| Offline demo button | Passed; 60 labelled synthetic matched pairs, isolated from genuine data |
| Report button | Passed; technical report and five figures |
| Cached reproduction button | Passed; all 36 processed files byte-identical |
| Immutable raw inputs | 1,165 source snapshot hashes verified |
| Genuine API sample counts | 654 candidates; 634 in-window; 633 analytical; 390 qualifying; 260 matched; 130 unmatched; 264 excluded |
| Filtered CSV download | Actual browser download contained ten qualifying AAPL event rows |
| Empty search | Cleared the ledger and inspector |
| Source evidence and methods reader | Opened successfully |
| Stop/restart | Disconnected banner appeared; task buttons disabled; page reconnected without reload |
| New session after restart | Report task accepted and passed using the renewed token |
| Repeated launcher | Reopened the same service PID rather than starting a second instance |
| Static Python, JavaScript syntax, installed dependencies | Passed |

The study's primary estimate remains +0.501063715884276 percentage points. This is technical
evidence, not Karol's final authored interpretation.

## Failure retained and corrected

The first fresh verification run failed one of 103 cases with a Windows connection abort on
an unauthorized shutdown POST. That failed job, XML and output are preserved in the
`preserved-failure-*` folder and in the interface's Run history.

The handler now reads the bounded request body before rejection and explicitly closes its
connection. A new test checks that ordering. Fifty real unauthorized requests then returned
HTTP 403 without connection resets, and the complete 104-case suite passed. The original
14 matplotlib/pyparsing deprecation warnings remain visible in the test output.

## Numerical preservation and environment provenance

The first rebuilt run changed only `run_manifest.json` and `environment.json`; all 34 other
processed files were unchanged. The manifest records the corrected handler. The Windows
platform identifier changed from 10.0.26200 to 10.0.26300; Python 3.11.9 and every recorded
package version were unchanged. A preserved 19 October demo environment exactly matches
the pre-run environment hash, so this explanation is supported by retained evidence.

The next full cached run reproduced all 36 files in the current environment exactly.
No threshold, hypothesis, universe, matching rule or financial formula was changed.

## What is still missing before publication

- Karol's independent arithmetic and source review. Start with the AAPL worked example and
  explain its negative matched difference despite a positive signed post response.
- Independently verified first-public release clocks: currently zero. The clean-release
  sensitivity remains unavailable. These are filing-timed comparisons.
- A judgment about match quality: 130 qualifying events are unmatched; the median initial
  magnitude gap is 1.18 pp, the maximum 32.72 pp, and 125 controls use a different study year.
- Karol's own written interpretation and a reviewed public-release package. Nothing has
  been published, and vendor/raw data redistribution has not been authorized.

These are research/audit and publication tasks, not concealed interface failures. Daily data,
the selected universe and the dependence sensitivities also limit the permissible claims.

## Test it yourself

Use `docs/QUICK_TEST.md` for exact clicks and expected outputs. Open `Open Research Desk.cmd`,
wait for Connected, run verification, inspect/export AAPL events, then try demo/report/reproduction.
Stop with `Close Research Desk.cmd` when idle. After a computer restart, run the launcher again.

Today tested the pinned genuine-data snapshot, its interfaces and cached reproduction.
It did not collect a fresh vendor snapshot or claim that future live API access is guaranteed.

## Evidence

`summary.json` records successful task IDs and exit codes. Adjacent JSON files retain data
integrity, downloaded CSV checks, HTTP rejection checks, numerical preservation, environment
changes and cached reproduction. Per-task XML/logs and the original failed run are copied
alongside them. The quick guide separates software acceptance from Karol's research signoff.
