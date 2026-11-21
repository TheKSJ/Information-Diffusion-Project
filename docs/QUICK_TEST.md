# Test the research desk — 29 October 2026

The software check and the research review are separate. Passing these steps verifies the
local workflow; it does not establish causality, first-public information timing or profitability.

## Open the app

Double-click **Open Research Desk.cmd** in the project folder. It starts the local service and
opens `http://127.0.0.1:8765`. Wait for **Connected**. You can close the launcher window.
Opening the launcher again reuses the existing service. After restarting your computer,
run the launcher again; this is a local application, not a public hosted website.

## Quick acceptance check

| Action | Expected result |
|---|---|
| Overview | Paired difference **+0.501 pp**; issuer CI **+0.136 to +0.866 pp**; **260 pairs / 30 issuers**; **130 unmatched**. |
| Switch Average → Cumulative | Plot, subtitle and legend change; the primary estimate stays fixed. |
| Event explorer → Qualifying events → search `AAPL` | **10 observations**. |
| Select AAPL, 2 May 2025 | Initial AR approximately **−4.99%**; signed post CAR **+3.09%**; control signed post CAR **+4.06%**; pair difference **−0.970 pp**. |
| Inspect a row on a narrow screen | The inspector comes into view. **Back to event list** returns to the ledger. |
| Export filtered AAPL events | CSV contains one header plus ten event rows. Returns in CSV are decimal fractions: `.03` means `3%`. |
| Search `no-such-company` | **0 observations** and a cleared inspector. No old event is presented as a new result. |
| Overview → In research window | **634 observations**. |
| Overview → Valid observations | **633 observations**. |
| Evidence & timing | **487** timestamp discrepancies, **2** session changes, **150/150** identity sources, **20** reviewed disclosures, **0** verified first-release clocks. |
| Read full report | Technical report opens with its five figures. |

## Run the four workflow checks

Use **Run center**, one task at a time. Keep the browser open to watch; logs persist even if
you navigate to another view. The other task buttons disable while a task is running.

| Button | Passing output | What it verifies |
|---|---|---|
| Run verification | **PASSED · EXIT 0**, **104 tests** | Fixed configuration, financial logic, APIs, jobs and client regression checks. Nine JavaScript checks run inside one Python test when the optional local Node QA tool is available. |
| Run demo | **PASSED · EXIT 0**, **60 synthetic matched pairs** | Complete offline workflow on clearly labelled, isolated fixtures. It does not replace the genuine 260-pair study. |
| Run report | **PASSED · EXIT 0**, **5 figures** | Regeneration from saved calculations. Open the report to inspect it. |
| Run reproduction | **PASSED · EXIT 0**, **36 files**, `identical: true`, no differences | Genuine cached inputs reproduce every processed output. Allow several minutes; visible progress is normal. |

A result marked **Failed** needs its execution output inspected. Do not treat a queued or
running task as a pass. Earlier failed runs remain in history as an audit trail; use the newest
run to assess the current version. Do not edit source files, the design or input ledgers during reproduction.

## Check restart recovery

After all tasks finish, double-click **Close Research Desk.cmd**. The page should show
**Disconnected** and disable task/export controls. Double-click **Open Research Desk.cmd**:
the same page should return to **Connected** automatically. **Run report** is a short way to
check that the restarted service accepts a task with a fresh session token.

The close command refuses shutdown while a task is running. Do not forcibly kill an active
calculation merely because its other buttons are disabled.

## What still needs Karol's review

1. Independently check the AAPL arithmetic and explain alpha, beta, AR, additive CAR and the
   sign adjustment. Explain why its filing response can continue (+3.09%) yet have a negative
   paired difference (−0.970 pp) when its control continued more (+4.06%). Use
   `docs/numerical_walkthrough.md` and the event inspector.
2. Review both COST timing discrepancies and selected exhibits. No first-public release clocks
   are independently verified; a date on an exhibit is not a timestamp. The clean-release
   sensitivity is intentionally unavailable.
3. Inspect the weakest matches: median initial-magnitude gap **1.18 pp**, maximum **32.72 pp**,
   **125** year fallbacks and **130** unmatched events. Decide what claims the comparison supports.
4. Write the interpretation and limitations yourself before publication. The quarter-based
   interval crosses zero; the positive primary issuer estimate is not a trading or causal claim.
5. Prepare the public repository/presentation only after reviewing source/vendor redistribution
   constraints. Nothing has been published, pushed or hosted by this local build.

The local software can be finished today with these acceptance checks. Improving information
timing or revising matching is a separately justified research change, not a cosmetic fix to
make the result look stronger.
