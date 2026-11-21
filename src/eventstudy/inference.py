"""Cluster-aware inference. One/two-sided tests and CI share one reference distribution."""
import numpy as np
import pandas as pd
from scipy import stats


def cluster_t(mean, cluster_scores, n, minimum_clusters=6):
    scores = np.asarray(cluster_scores, dtype=float)
    groups = len(scores)
    base = {"clusters": groups, "se_pp": None, "ci95_pp": None,
            "p_one_sided": None, "p_two_sided": None, "t_stat": None, "df": None}
    if groups < minimum_clusters or n < 2:
        return {**base, "status": "insufficient_clusters"}
    variance = groups / (groups - 1) * np.sum(scores**2) / n**2
    if variance <= 1e-24 or not np.isfinite(variance):
        return {**base, "status": "degenerate_cluster_variance"}
    se = np.sqrt(variance)
    t = mean / se
    df = groups - 1
    critical = stats.t.ppf(.975, df)
    return {**base, "status": "estimated_few_clusters" if groups < 30 else "estimated",
            "se_pp": float(100 * se), "ci95_pp": [float(100 * (mean - critical * se)),
                                                    float(100 * (mean + critical * se))],
            "p_one_sided": float(stats.t.sf(t, df)),
            "p_two_sided": float(2 * stats.t.sf(abs(t), df)), "t_stat": float(t), "df": df}


def infer(pairs, seed=20261018, draws=5000, minimum_clusters=6):
    result = {"n_pairs": len(pairs), "n_issuers": 0, "n_calendar_quarters": 0,
              "estimate_pp": None, "issuer_cluster": {"status": "empty"},
              "quarter_cluster_sensitivity": {"status": "empty"},
              "issuer_bootstrap": {"status": "empty"},
              "hypothesis": "H0: mean event-minus-control signed post CAR <= 0; H1: > 0"}
    if pairs.empty:
        return result
    if not np.isfinite(pairs.difference).all():
        raise ValueError("Non-finite pair differences cannot enter inference")
    n = len(pairs)
    mean = float(pairs.difference.mean())
    residuals = pairs.assign(residual=pairs.difference - mean)
    scores = residuals.groupby("ticker", sort=True).residual.sum()
    result.update(n_issuers=len(scores), estimate_pp=100 * mean,
                  issuer_cluster=cluster_t(mean, scores, n, minimum_clusters))
    # Control outcomes are assigned to their own quarter, never the event quarter by convenience.
    legs = pd.concat([
        pd.DataFrame({"quarter": pairs.event_quarter,
                      "score": pairs.event_signed_post_car - pairs.event_signed_post_car.mean()}),
        pd.DataFrame({"quarter": pairs.control_quarter,
                      "score": -(pairs.control_signed_post_car - pairs.control_signed_post_car.mean())})])
    quarter_scores = legs.groupby("quarter", sort=True).score.sum()
    result["n_calendar_quarters"] = len(quarter_scores)
    result["quarter_cluster_sensitivity"] = cluster_t(mean, quarter_scores, n, minimum_clusters)
    result["quarter_cluster_sensitivity"]["method"] = "centered event/control legs at own calendar quarter"
    if len(scores) >= minimum_clusters:
        sums = pairs.groupby("ticker", sort=True).difference.sum().to_numpy()
        counts = pairs.groupby("ticker", sort=True).size().to_numpy()
        rng = np.random.default_rng(seed)
        indices = rng.integers(0, len(sums), size=(draws, len(sums)))
        bootstrap = sums[indices].sum(axis=1) / counts[indices].sum(axis=1)
        result["issuer_bootstrap"] = {"status": "diagnostic_percentile_CI", "draws": draws, "seed": seed,
                                      "ci95_pp": (100 * np.quantile(bootstrap, [.025, .975])).tolist(),
                                      "method": "pairs cluster bootstrap, all observations of sampled issuers"}
    else:
        result["issuer_bootstrap"] = {"status": "insufficient_clusters"}
    result["reliability_note"] = ("At most 30 deliberately selected issuers; small-cluster t and bootstrap "
                                   "approximations may be fragile. Quarter check is a sensitivity. "
                                   "No causal, first-release, intraday-speed or profitability interpretation.")
    return result

