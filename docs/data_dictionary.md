# Dataset dictionary

All dates use ISO 8601. Analytical decimal returns are not percentages. All `*_pp` inferential
outputs are percentage points; `*_percent` descriptive/plot values equal 100 times the return.
Empty CSVs retain required headers. JSON uses null, never NaN or an invented zero estimate.
`source_company_name` is the name returned by the captured current SEC submissions root;
it is not asserted to be the issuer's name at every historical date. Historical filing bodies,
cover tags, URLs and raw metadata remain pinned independently.

| File | Grain and key | Important fields |
|---|---|---|
| configs/universe.csv | Fixed ticker | company, seed CIK, assigned sector, mapping provenance, historical status |
| all_filings.csv | Source row; duplicate flags preserved | accessionNumber, ticker, CIK, form, items, filingDate, reportDate, acceptanceDateTime, source_company_name, metadata_url/hash, source/index/primary/submission URLs, retrieval time |
| candidate_events.csv | Unique CIK + accession (`event_id`) | exact item tokens, other_economic_items, authoritative timestamp status, identity status |
| amendments.csv | 8-K/A accession | amendment excluded from original-filing discovery |
| unresolved_items.csv | Unresolved original 8-K accession | primary_reason, item_error; not treated as definitely non-2.02 |
| historical_identity.csv | Ticker / calendar filing year | current_mapping_verified, cover_symbols/CIKs, historical_cover_verified, evidence_url, source_sha256, error |
| issuer_coverage.csv | Ticker | historical_identity_verified, SEC_screening_complete, candidate count |
| release_audit.json | Deterministic hash-selected candidate | index, primary and exhibit evidence URLs/hashes/excerpts, date strings for review, reviewed, first_public_release_verified, errors |
| configs/timing_review.csv | Editable event_id | evidenced reviewed/first_public flags, timezone-aware release_timestamp, release_date separately, may-precede flag, notes |
| timestamp_ledger.csv | Candidate event_id | raw and verified timestamps, authoritative source, api_minus_verified_seconds, timestamp_discrepancy, discrepancy_changes_session, aligned event_session, timing_class; raw_api_session remains in candidate_events.csv and event_ledger.csv |
| event_ledger.csv | Candidate event_id | mutually exclusive primary_reason and independent secondary quality flags |
| analytical_events.csv | Valid unique ticker/session | arithmetic-complete events including those below threshold |
| included_events.csv | Qualifying arithmetic-complete ticker/session | abs(ar0)>=.02; unmatched observations remain here |
| excluded_events.csv | Candidate excluded from primary large-move sample | one primary_reason plus flags and exact coverage counts where relevant |
| adjusted_prices_returns.csv | Ticker / exchange session | adj_close, unadjusted_close, adjusted simple return, corporate actions if supplied |
| price_quality.csv | Ticker / session / issue | missing/invalid price, extreme return or vendor-reported split; no invented explanation |
| event_abnormal_returns.csv | event_id / offset | exchange session, stock_return, market_return, expected_return, abnormal_return |
| control_screening.csv | control_id / pseudo-session | reason for eligibility/rejection, model statistics where computed |
| control_candidates.csv | Qualifying eligible control_id | same event arithmetic, including prespecified .015 lower-threshold pool |
| control_abnormal_returns.csv | control_id / offset | exact stock/market/expected/abnormal returns; controls not only matched selections |
| matched_pairs.csv | event_id / unique control_id | both sessions and quarters, outcomes, difference, initial ARs, year/magnitude/volatility gaps |
| unmatched_events.csv | event_id | no eligible same-issuer/sign or non-overlapping control reason |
| exclusion_waterfall.json | Candidate sample | mutually exclusive reason counts plus unmatched count; unresolved metadata and amendments are separate discovery ledgers |
| coverage_by_issuer_year.csv | Ticker / filing year / primary reason | count; boundary candidates remain visible |
| primary_inference.json | Primary matched sample | estimate_pp, n_pairs/issuers/quarters, issuer-cluster SE/CI/t/p/df/status, issuer-bootstrap CI and quarter sensitivity |
| robustness.json | Prespecified sensitivity | threshold/model/clean subset, result, unmatched count, availability and classification |
| secondary_descriptive.csv | Sign, timing or sector group | n, issuers, mean AR0/pre/post/signed-post/post10; descriptive only |
| event_time_trajectory.csv | Event offset | n, issuers, AAR, additive CAAR from −5, pointwise issuer-cluster CI |
| source_failures.json | Failed operation | ticker, stage, exact source/error; retained in partial run |
| fetch_manifest.json | Collection attempt | completion time, requested company count, source snapshot hashes/URLs/retrieval times |
| run_manifest.json | Analysis | complete input/config/design/lock/code hashes and fixed seeds |
| environment.json | Execution environment | Python, platform, exact installed package versions |

Event statistics: alpha and beta are pre-event OLS coefficients; r_squared is estimation fit;
residual_std uses n−2. `car_pre_5_1` = CAR[-5,-1], `car_0_1` = CAR[0,+1],
`car_minus1_1` = CAR[-1,+1], `car_post_1_5` and `car_post_1_10` omit day 0.
`signed_post_car` = sign(ar0)*car_post_1_5; it is not standardized CAR.
`model_instability_flag`, `event_induced_volatility_flag`, `extreme_return_flag`,
`intraday_prefiling_activity`, `overlapping_event_window`, `other_economic_items`,
`release_timing_uncertain`, `clean_release_timing` preserve separate concerns.
`disclosure_reviewed` distinguishes an inspected disclosure from an unreviewed one;
`nonstandard_disclosure_flag=False` means no identified flag, not proven ordinary earnings.
The 20 source reviews identify their builder reviewer and leave Karol's own audit pending.

`matching_diagnostics.json` reports year fallback counts, median/95th/max initial-magnitude
gaps in percentage points and pairs by issuer. No hidden caliper or balance claim is applied.
`dataset_schema.json` records observed columns, data types and row counts for analytical CSVs.
`universe_resolved.csv` adds official SEC mapping provenance and historical evidence status
while retaining the original design CSV's seed provenance.

