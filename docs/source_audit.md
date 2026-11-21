# Filing and release-timing source inspection — 18 October 2026

Twenty candidate event IDs were selected deterministically by ascending SHA-256(event_id),
before inspecting their post-event outcomes. The cached packet is
`data/interim/release_audit.json`. It preserves the original filing's Item 2.02 text, SEC
index/primary URLs and associated exhibit URLs, hashes and text excerpts. The packet fetched
91 linked source documents across the 20 filings; not all are the earnings release itself.
There were no retrieval errors in this packet.

The build agent inspected the 20 Item 2.02 passages and their principal results exhibits.
The evidence-backed findings are recorded in `configs/timing_review.csv`, including reviewer
identity. This does not stand in for Karol's independent source review. Date statements in
the filing/exhibit are recorded separately from any timestamp. No conference-call time,
webcast time, filing time or date-only dateline was promoted to first-public release time.

**Independently established first-public release clocks: zero.** The clean-timing sensitivity
is unavailable. This remains a filing-timed study. Same-day release dates do not establish
whether the release preceded EDGAR acceptance.

## Specific findings that affect interpretation

- BMY accession 0001140361-22-014868, filed 18 April 2022: the Item 2.02 text describes a
  revised presentation of previous GAAP/non-GAAP results and acquired-IPRD classifications.
  It is not a standard new quarterly-results announcement. The primary rule includes original
  Item 2.02 filings, so retain it and set the nonstandard-disclosure flag. Do not quietly remove
  it after observing returns. This issue can also occur among unreviewed filings.
- WMT accession 0000104169-25-000010: accepted at 06:57 Eastern on 20 February 2025; the
  filing says the company “will issue” the press release that day. This does not establish
  the first-public clock or prove that the release preceded the filing.
- UPS accession 0001090727-24-000004: the results exhibit also announces an increased
  quarterly dividend. BMY 0000014272-25-000129, JNJ 0000200406-22-000012 and HON
  0000773840-21-000055 also contain guidance/expectations in the results exhibits.
  Absence of an additional 8-K item does not prove absence of concurrent news.
- GS accession 0001193125-23-257291 includes Item 7.01 and an associated presentation.

Full linked evidence and the remaining reviewed IDs are in the timing-review CSV and packet.
The primary inclusion rules and hypotheses were not changed because of these findings.

## Actual timestamp discrepancies that change trading sessions

The genuine ledger identifies two COST filings for which trusting the API's Z timestamp
would move day zero from Friday to Monday:

| Accession | Raw API value | Authoritative index value, Eastern | Verified session | Raw-API implied session |
|---|---|---|---|---|
| 0001193125-22-065629 | 2022-03-04T22:47:58.000Z | 2022-03-04 12:47:58−05:00 | 2022-03-04 | 2022-03-07 |
| 0001193125-22-249988 | 2022-09-23T21:38:33.000Z | 2022-09-23 13:38:33−04:00 | 2022-09-23 | 2022-09-26 |

Both authoritative times are intraday and precede that Friday's actual regular close.
Their raw API values imply times after the close. The complete candidate/event ledgers
preserve both assigned sessions and the exact index source URLs and hashes. These cases
demonstrate why a fixed four/five-hour correction is not applied universally.

## Historical identity parsing failure and repair

The initial parser corroborated 145/150 annual covers and left all five C covers unresolved.
Each Citigroup primary 10-K explicitly refers registered securities to Exhibit 99.01. Following
that index link and reading the exhibit's inline trading symbol established C in all five years;
the primary cover establishes CIK 831001. Both hashes and source URLs are retained.
The original five failure records remain in `reports/initial_identity_failures.csv`.
The initial numerical pass is separately labelled as a build diagnostic. See CHANGELOG.md.

