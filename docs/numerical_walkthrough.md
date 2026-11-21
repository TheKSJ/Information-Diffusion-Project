# Three genuine-source arithmetic checks

These are calculation examples, not authored research conclusions. Independently recomputed
from pinned adjusted prices using closed-form covariance/variance OLS, separately from the
project's least-squares implementation. Full precision and source evidence are preserved in
`reports/manual_numerical_audit.json`. All figures in this table are percentages except beta.

| Ticker / session 0 | Estimation sessions | alpha (%) | beta | SPY R0 (%) | Stock R0 (%) | AR0 (%) | CAR[+1,+5] (%) | Signed post CAR (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AAPL / 2021-01-28 | 100 | 0.0428998 | 1.6290819 | 0.8600063 | −3.4985299 | −4.9424504 | −3.6064614 | +3.6064614 |
| JPM / 2021-01-15 | 100 | 0.0985545 | 0.9001380 | −0.7292624 | −1.7921238 | −1.2342414 | −7.3540154 | +7.3540154 |
| CAT / 2021-01-29 | 100 | 0.2086230 | 0.7590260 | −2.0019661 | −0.8137127 | +0.4972086 | +0.9024569 | +0.9024569 |

JPM and CAT in these examples are below the 2% initial-response threshold and therefore
do not enter the primary large-move sample. They remain valid arithmetic-complete observations.

For AAPL, the adjusted close goes from 137.913238525391 to 133.088302612305:

```text
Stock R0 = 133.088302612305 / 137.913238525391 − 1 = −0.03498529919735
Expected R0 = 0.00042899797359 + 1.62908186375568 × 0.00860006297215
            = 0.01443920458867
AR0 = −0.03498529919735 − 0.01443920458867 = −0.04942450378602

CAR[+1,+5] = (−0.00523601449778) + (−0.01102568222722)
           + (−0.01712742142796) + (−0.00948843819347)
           + 0.00681294254370
           = −0.03606461380273
Signed post CAR = (−1) × (−0.03606461380273) = +0.03606461380273
```

Day zero is not in the five terms of post CAR. Positive signed post CAR denotes continuation
in the initial direction, including continuing negative abnormal returns after an initial fall.
CAR is the sum of abnormal returns; it is not compounded wealth.

The authority checks for these cases are:

- [AAPL index, accepted 27 January 2021 at 16:30:35 Eastern](https://www.sec.gov/Archives/edgar/data/320193/000032019321000009/0000320193-21-000009-index.html): next session, 28 January.
- [JPM index, accepted 15 January 2021 at 06:45:52 Eastern](https://www.sec.gov/Archives/edgar/data/19617/000001961721000071/0000019617-21-000071-index.html): same session, before open.
- [CAT index, accepted 29 January 2021 at 06:30:47 Eastern](https://www.sec.gov/Archives/edgar/data/18230/000001823021000026/0000018230-21-000026-index.html): same session, before open.

Raw and adjusted daily returns were inspected separately; adjusted prices were used for all
models. No unadjusted-price substitution occurred. Across all 260 matched pairs, independently
resumming the five event/control abnormal returns produced a maximum stored-minus-recomputed
pair-difference residual of 6.01×10⁻¹³ in decimal returns. The largest coefficient residual in
the three worked cases is 4.33×10⁻¹², consistent with the analytical CSV's 12-significant-digit
serialization. Residuals remain visible in the audit JSON; no reconciliation plug is inserted.

