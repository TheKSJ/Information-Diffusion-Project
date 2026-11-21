# Research design lock — version 1, 18 October 2026

Written before empirical calculation. Configuration and this document are hashed in every run.
Technical evidence for Karol's review; this is not authored publication prose.

## Question and population

Following original Form 8-K Item 2.02 filings, do large filing-timed initial abnormal returns
continue over the next five NYSE sessions relative to matched non-filing large movements?
The 30 tickers in configs/universe.csv are fixed, including exclusions. No replacement.
Event session 0 must fall within 2021-01-01 through 2025-12-31 inclusive. Discovery includes
buffer dates to capture boundary filings and screen controls. The surviving, large-cap,
sector-balanced selection does not represent the historical US equity population.

## Fixed formulas and sample

R[t] = adjusted_close[t] / adjusted_close[t-1] - 1, with no filling of missing prices.
Fit R_stock = alpha + beta R_SPY + error by OLS over offsets [-120,-21], inclusive,
requiring all 100 paired observations. No forward or event-window fitting.
AR[t] = R_stock[t] - alpha - beta R_SPY[t]. CAR[a,b] = sum(AR[a:b]).
Observation offsets [-5,+10] must all have valid stock and SPY returns. This conservative
complete-window rule is applied identically to events and controls and loses observations.
Primary large movement: abs(AR[0]) >= .02. signed_post_car = sign(AR[0])*CAR[+1,+5].
Returns are decimal internally; differences are reported in percentage points (100*D).

Primary exclusions in order: amendment; unresolved item metadata; unverified authoritative
timestamp; outside research sessions; unresolved historical security identity; missing stock/SPY
prices; insufficient estimation coverage; incomplete observation returns; degenerate model;
duplicate ticker-session analytical observation. Unmatched large-move events remain descriptive.
Duplicate filings stay in the ledger; lexicographically first accession represents a session.
Overlapping events remain flagged in primary analysis; a non-overlap sensitivity removes all
overlapping observations, avoiding a retrospective outcome-dependent choice.

SEC index Accepted time or submission-header ACCEPTANCE-DATETIME is interpreted with
America/New_York daylight-saving rules. Raw submissions time is preserved and compared.
At/after the actual XNYS close maps to the next session, including early closes. Intraday
filings use that session and carry a pre-filing-activity flag. Dates never move for missing prices.
EDGAR acceptance is not evidence of first earnings-information release.

## Matched controls and estimand

All issuer-session pseudo-dates within the research interval use identical fitting and windows.
Exclude any pseudo observation whose [-5,+10] window intersects a candidate earnings-filing
[-5,+10] window (unresolved timing uses conservative filing-date session and next session).
Exclude pseudo-dates with any 8-K, 8-K/A, 10-Q, 10-Q/A, 10-K or 10-K/A within five sessions
of the FULL pseudo observation window. Incomplete issuer submissions pagination prohibits
its controls. SEC screening does not establish absence of other news.

Greedy matching order: ascending event session, ticker, stable event ID. Same issuer and
initial AR sign mandatory. Same year first; otherwise nearest calendar year within 2021–2025.
Then smallest absolute-AR magnitude gap, residual-volatility gap, calendar distance, stable ID.
No caliper imposed; report gaps explicitly. No cross-issuer or sign fallback. No control reuse
across the entire primary run; controls whose full windows overlap an already selected control
for that issuer are also unavailable. Events can remain unmatched. Each robustness specification
rebuilds its own candidate pool and matches from scratch using the same algorithm.

D_i = signed_post_car_event_i - signed_post_car_control_i. Primary estimand is mean D_i.
H0: E[D] <= 0. H1: E[D] > 0. A negative/insignificant difference is a valid outcome.
Conditioning on observed day-zero moves makes this retrospective conditional analysis.

## Inference and sensitivities

Primary inference: intercept-only OLS with finite-sample-corrected issuer-cluster sandwich SE,
t reference with G-1 degrees of freedom; one-sided upper-tail p-value and two-sided p-value
and 95% CI from the SAME t statistic. Minimum six issuers; below that, point estimate only.
Even 6–29 clusters can give fragile inference; all reports flag this.
Issuer pairs bootstrap: resample issuers with replacement retaining ALL their pairs, compute
the observation-weighted mean in each draw; 5,000 draws, seed 20261018. Percentile CI is a
secondary uncertainty diagnostic (no invalid percentile-sign p-value).

Calendar sensitivity aggregates each pair into two legs, +event outcome and -control outcome,
at their OWN calendar quarters. Use quarter-cluster sandwich variance of centered legs,
divided by number-of-pairs squared, corrected by Q/(Q-1), t(Q-1). This captures cross-issuer
co-movement in either event or control quarter. It remains a sensitivity, not an independent
confirmatory test or a full serial-and-cross-sectional dependence solution.

Descriptive: AR[0], AAR/CAAR [-5,+10], pre-CAR [-5,-1], CAR[+1,+10], sign/timing/sector.
Prespecified robustness: thresholds .015 and .025; simple market-adjusted returns; all
non-overlapping single-economic-item filings (Item 9.01 exhibits alone is not a confounder);
verified first-public-release subset only if >=20 evidence-verified releases with the SAME
aligned session as acceptance. Missing release-time evidence never becomes a fabricated time.
No additional confirmatory secondary tests; sensitivity p-values are exploratory and must not
be used to select the headline result. Output no final authored interpretation.

## Reproduction and rights

Immutable hashed source cache, fixed configuration, package lock, deterministic order and seeds.
Missing/failed sources retained; no synthetic fallback for live analysis. Offline demo is isolated
and visibly labelled synthetic. Yahoo price files remain local and ignored by Git; review vendor
licensing before sharing. Public materials should use derived analysis and source links.

