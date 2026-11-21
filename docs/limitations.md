# Validity limitations, in priority order

1. **Filing clock versus information clock.** An earnings press release may precede EDGAR
   acceptance. Date-only exhibits do not establish a first-public timestamp. Only a separately
   evidenced first-release review can support the timing sensitivity; an unavailable subset
   remains unavailable. This study estimates filing-timed associations.
2. **Retrospective conditioning and non-causal comparison.** The 2% threshold conditions on
   realized AR0. Same-issuer/sign matching is not randomization, and news/background
   differences can remain. This is not a prospective signal, causal inefficiency or trading edge.
3. **Dependence and sample size.** Repeated events, earnings seasons, macro shocks and common
   sectors can defeat simple independence. Issuer clustering, bootstrap and quarter-leg
   sensitivity help but do not jointly eliminate all dependence. Maximum 30 issuers/20 quarters
   makes approximations fragile; fewer than six clusters is explicitly untestable here.
4. **Control scarcity and imperfect comparability.** Full-window SEC screening is deliberately
   conservative. Some financial issuers file frequently, so eligible controls may be scarce.
   No cross-issuer/sign fallback or quiet relaxation. Unmatched losses and matching gaps must
   be reviewed; the paired estimand may represent a selected subset of qualifying filing events.
5. **SEC timestamp/data uncertainty.** API bad-Z clocks can change sessions. Authoritative
   index/header reconciliation and DST/early-close tests mitigate this; missing verification
   excludes the candidate. Primary filings can themselves contain mixed corporate news.
6. **Daily resolution.** Intraday day-zero returns include pre-filing trading and other news;
   after-hours responses combine information arriving before the next close. Daily data
   cannot measure intraday diffusion speed or isolate the precise price response.
7. **Universe and security identity.** Thirty deliberately selected surviving large stocks,
   five equal assigned sectors, no failed/delisted firms: survivorship/size/selection biases.
   Annual cover tags corroborate ticker and issuer continuity but are not an exhaustive
   historical share-class, merger, spinoff or listing audit. Review actions, notably splits
   and major issuer restructurings. Findings cannot represent all US equities.
8. **Prices and snapshot rights.** Yahoo adjusted history and corporate-action records can
   change. Hash-pinned snapshots support local reproducibility, not independent price truth.
   No filling/substitution, but adjustments/vendor errors can remain. Licensing/personal-use
   restrictions must be reviewed before publishing or redistributing vendor data.
9. **Expected-return model.** SPY is an ETF market proxy, not the whole market; alpha/beta
   estimation error, omitted factors, structural changes and event-induced volatility remain.
   Model diagnostics are flags, not reasons invented for residuals. Complete 100/16-session
   coverage requirements may introduce additional selection.
10. **Concurrent information and overlaps.** Other 8-K items flag possible guidance/dividends/
    corporate disclosures, but earnings exhibits may contain additional news under Item 2.02
    alone. SEC screening misses media, analyst and economic releases. The non-overlap,
    less-confounded sensitivity is not a clean causal identification strategy.
11. **Multiple comparisons.** Prespecified sensitivities remain exploratory. No secondary
    significance should replace the primary test or become a selected publication claim.
12. **Engineering audit scope.** Automated source parsing/tests and numerical checks do not
    replace Karol's independent review. The handoff distinguishes source checks, fixture-only
    tests, observed failures and remaining uncertainties. Never infer unperformed validation.

