# Verification — 19 October 2026

**PASS: the software works in the installed environment using its cached genuine-data snapshot.**

| Check executed today | Actual outcome |
|---|---|
| Python / installed dependencies | Python 3.11.9; no broken requirements |
| CLI help and fixed-study validation | Passed; 30-company universe valid |
| Static checks | Passed |
| Automated tests | 68 passed; 0 failures, errors or skips |
| Offline end-to-end synthetic demo | Completed; 60 events and 60 matched pairs |
| Offline SEC/price source-ingestion pilot | 93,900 filing records; 64 candidates verified; 0 failed operations |
| Full cached genuine-data workflow | Completed; 30 companies, 390 qualifying events, 260 pairs |
| Exact cached reproduction | All 36 processed files byte-for-byte identical |
| Independent financial arithmetic | Three worked cases and all 260 pair calculations passed |
| Raw-source integrity | All 1,165 source snapshots passed their hash checks |
| Independent actual-data invariants | Estimation boundaries, 100 paired sessions, thresholds, 16 observation offsets, control signs/issuers and non-reuse passed |
| Independent cluster-SE calculation | statsmodels matches saved result within rounding precision |
| Report generation | Completed; five figures generated |

No code fixes or research-specification changes were needed. The test run emitted 14
existing upstream matplotlib/pyparsing deprecation warnings; these did not fail tests.

This verification reused the pinned SEC/Yahoo snapshot. Fresh network downloads were not
retested today. Software execution does not resolve the documented research limitations,
including uncertain first-public release timing and imperfect matched-control comparability.

Evidence: `tests.xml`, `summary.json`, `data_invariants.json`,
`cached_reproduction_check.json`, `manual_numerical_audit.json`, and `demo/` in this folder.
