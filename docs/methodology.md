# Reproducible methods

## Source reconstruction

Each submissions parallel array is checked against accession-array length and reconstructed
by common index. Historical files are followed whenever their stated dates intersect a buffered
2020-12-01 to 2026-01-31 discovery interval. All forms and source duplicates are retained in
all_filings.csv; unique accessions enter classification. Original 8-K exact token 2.02 qualifies;
8-K/A is separately recorded. Missing item metadata triggers an attempted primary-document
heading check. Unresolved items remain in their own ledger and are conservatively screened
as important 8-K filings for controls. No missing metadata is labelled definitely non-earnings.

SEC current submissions CIK/ticker and five annual 10-K inline cover tags corroborate
historical identity. The annual evidence ledger retains URLs, hashes, symbols and CIKs.
If the annual cover explicitly incorporates a securities-registration Exhibit 99.01, follow
that exhibit through the filing index and use its trading-symbol tags with the primary
cover CIK. Record both source hashes and the incorporation method. This is the Citigroup
layout in all five years; it satisfies the same evidence requirement rather than waiving it.
Seed mappings are not assumed verified. A missing annual corroboration excludes the issuer
until investigated; no automatic substitution or manual assertion without evidence.

## Timestamp reconciliation and sessions

The filing-index Accepted value, or submission-header ACCEPTANCE-DATETIME fallback,
provides local Eastern authority. ZoneInfo applies DST; ambiguous/nonexistent local clocks
are rejected. Store raw API time, verified time, discrepancy in seconds, each implied session,
and whether the discrepancy changes session. No universal offset is used.

At actual XNYS close or later, align to the next session. A holiday/weekend aligns to the
next session. Before open/intraday use the current session. Intraday observations explicitly
include pre-filing trading. Missing prices never change this assignment. Return day 0 ends
at the first regular close after acceptance. Complete-window coverage is checked afterwards.

## Prices and expected returns

Fetch June 2020 through February 2026; Yahoo end date is exclusive. Persist the yfinance
returned OHLC, Adj Close, volume and actions as a CSV snapshot with full precision, hash,
download settings and retrieval time. This is the library-returned source snapshot, not a
capture of Yahoo's underlying HTTP bodies. Returns use only dividend/split-adjusted Adj Close.
Invalid/nonpositive/infinite prices become missing returns and are listed in quality output.
Reindex to exchange sessions before pct_change(fill_method=None), so a missing price also
invalidates the following session return. Never bridge the gap or substitute unadjusted Close.

For each observation fit OLS alpha/beta on [-120,-21] with exactly 100 complete pairs.
Fit includes an intercept and no risk-free subtraction (daily raw-return market model).
R-squared and residual SD use estimation data; SD denominator n−2. Arithmetic follows the
locked design. Store all observed/market/expected/abnormal returns by offset, enabling
independent recalculation. Reject a degenerate market-regressor variance.

Diagnostics flag beta difference >1 between the first/last estimation halves, observation
AR SD >2 times estimation residual SD, and stock daily adjusted-return magnitude >40%.
These are review flags and do not suppress legitimate moves or assign causal explanations.

## Control construction

Every study issuer-session is screened. For potential dates, fit strictly preceding models
with the same data rules. Event/control full [-5,+10] windows may not intersect. Nearby
important SEC forms within five sessions of the whole pseudo window disqualify the control.
Unverified filing time protects both filing-date and next-session positions. Incomplete
pagination makes that issuer's non-event screening unresolved, prohibiting its controls.
Eligible controls can still contain non-SEC news; "non-filing" is not "no information".

Greedy match same issuer and AR sign. Minimize absolute year gap, then initial-magnitude gap,
then residual-volatility gap, then calendar-day distance, then stable control ID. Events are
ordered session/ticker/ID. Same-year preferred, nearest other study year allowed and flagged.
No cross-issuer/sign fallback, no hidden caliper, no reuse or intersecting selected control
windows within issuer. Report magnitude/volatility/year gaps rather than claiming exact balance.
This estimates a conditional comparison under selection on observed movement, not a causal
treatment effect. Future pseudo-dates are permitted for retrospective matching and must not
be interpreted as a prospective trading strategy.

## Dependence-aware statistics

Let d_i = event signed CAR − control signed CAR, n pairs, G issuers. Estimate mean d.
For issuer g let s_g = sum_{i in g}(d_i − mean d).
Variance = [G/(G−1)] × sum(s_g²)/n². With an intercept-only fit this is the usual finite-sample
cluster sandwich correction. Use t = mean d/SE, df=G−1; one-sided p = t.sf(t,df), two-sided
p = 2*t.sf(abs(t),df). CI = mean d ± t.ppf(.975,df)*SE. Multiply estimates/SE/CI by 100
for percentage points. At least six clusters and positive finite variance are required.

Issuer cluster bootstrap resamples G issuers with replacement and includes all pairs from
each sampled issuer. Recalculate observation-weighted mean from drawn sums/counts. Report
the percentile CI only. Do not derive an uncentered-bootstrap sign p-value.

Quarter sensitivity has two outcome legs per pair: event outcome minus its overall event
mean, and negative(control outcome minus overall control mean). Cluster these scores by
each leg's own calendar quarter, not only the filing quarter, using Q/(Q−1), n² denominator
and t(Q−1). This does not solve all serial and cross-sectional dependence jointly and is
reported as a sensitivity. Maximum 30 issuer clusters and 20 quarters warrant caution.

## Outputs and reproduction

Each run stores configuration/design/universe/timing-review/dependency-lock/source-code hashes,
all input snapshot manifests and interim-input hashes, package/Python versions and seed.
Capture the input/code fingerprints at run start and check them after analysis. A concurrent
change invalidates the pass; never cite an interrupted or inconsistent-input build diagnostic.
Analytical CSVs use sorted deterministic inputs and fixed float formatting. Operational
retrieval timestamps may differ on a newly collected snapshot; cached analyses must not.
Tests compare complete offline output hashes. Full live reproducibility is verified separately
in the build audit when live sources are available. The changelog records implementation fixes.
Generate tables/figures from cached sources using `run` then `report`; neither fetches data.

