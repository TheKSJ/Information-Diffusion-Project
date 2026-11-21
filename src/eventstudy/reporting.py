"""Technical evidence tables/figures. Never generates publication-ready research conclusions."""
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .inference import cluster_t
from .storage import read_csv, write_csv


def mean_interval(frame, value, issuer="ticker"):
    if frame.empty:
        return np.nan, None
    mean = float(frame[value].mean())
    scores = frame.assign(residual=frame[value] - mean).groupby(issuer).residual.sum()
    inference = cluster_t(mean, scores, len(frame))
    return mean, inference.get("ci95_pp")


def secondary_tables(events, long, output):
    rows = []
    for dimension in ["initial_sign", "timing_class", "sector"]:
        if dimension not in events:
            continue
        for name, group in events.groupby(dimension, dropna=False):
            rows.append({"dimension": dimension, "group": name, "n": len(group),
                         "issuers": group.ticker.nunique(), "mean_ar0_percent": group.ar0.mean() * 100,
                         "mean_pre_car_percent": group.car_pre_5_1.mean() * 100,
                         "mean_post_car_percent": group.car_post_1_5.mean() * 100,
                         "mean_signed_post_car_percent": group.signed_post_car.mean() * 100,
                         "mean_post10_car_percent": group.car_post_1_10.mean() * 100,
                         "classification": "descriptive; no confirmatory secondary p-values"})
    write_csv(output / "secondary_descriptive.csv", rows,
              ["dimension", "group", "n", "issuers", "mean_ar0_percent", "mean_signed_post_car_percent"])
    trajectory = []
    if not long.empty:
        long = long.sort_values(["event_id", "offset"]).copy()
        long["cumulative_ar"] = long.groupby("event_id").abnormal_return.cumsum()
        for offset, group in long.groupby("offset"):
            aar, aar_ci = mean_interval(group, "abnormal_return")
            caar, caar_ci = mean_interval(group, "cumulative_ar")
            trajectory.append({"offset": offset, "n": len(group), "issuers": group.ticker.nunique(),
                               "aar_percent": aar * 100, "caar_percent": caar * 100,
                               "aar_ci_low": aar_ci[0] if aar_ci else np.nan,
                               "aar_ci_high": aar_ci[1] if aar_ci else np.nan,
                               "caar_ci_low": caar_ci[0] if caar_ci else np.nan,
                               "caar_ci_high": caar_ci[1] if caar_ci else np.nan})
    trajectory = pd.DataFrame(trajectory)
    write_csv(output / "event_time_trajectory.csv", trajectory,
              ["offset", "n", "issuers", "aar_percent", "caar_percent"])
    return trajectory


def numerical_cases(events, long, output, synthetic):
    label = "SYNTHETIC FIXTURES, not live source verification" if synthetic else "Cached-source arithmetic; independently inspect source URLs"
    lines = ["# Numerical verification cases", "", label, ""]
    if events.empty or long.empty:
        lines += ["No valid real event arithmetic is available. See the separately labelled offline demo."]
    else:
        # Deterministic examples, with both initial signs represented where possible.
        chosen = events.sort_values(["initial_sign", "event_id"]).head(2)
        chosen = pd.concat([chosen, events.sort_values("event_id").tail(1)]).drop_duplicates("event_id")
        for _, event in chosen.iterrows():
            group = long[long.event_id == event.event_id].sort_values("offset")
            zero = group[group.offset == 0].iloc[0]
            post = group[group.offset.between(1, 5)]
            recomputed = float(post.abnormal_return.sum())
            lines += [f"## {event.event_id}", "",
                      f"Ticker/session: {event.ticker}, {event.event_session}.",
                      f"Estimation: {event.estimation_first} through {event.estimation_last}; {int(event.estimation_valid)} observations.",
                      f"Expected R[0] = {event.alpha:.12f} + {event.beta:.12f} × {zero.market_return:.12f} = {zero.expected_return:.12f}.",
                      f"AR[0] = {zero.stock_return:.12f} − {zero.expected_return:.12f} = {zero.abnormal_return:.12f}.",
                      "CAR[+1,+5] = " + " + ".join(f"({x:.12f})" for x in post.abnormal_return) + f" = {recomputed:.12f}.",
                      f"sign(AR[0]) × CAR[+1,+5] = {int(event.initial_sign)} × {recomputed:.12f} = {event.signed_post_car:.12f}.",
                      f"Stored-minus-recomputed CAR residual: {event.car_post_1_5 - recomputed:.3g}.",
                      f"Source: {event.get('source_url', 'synthetic fixture')}", ""]
    (output / "worked_verifications.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_report(output, synthetic=False):
    output = Path(output)
    summary = json.loads((output / "run_summary.json").read_text())
    primary = json.loads((output / "primary_inference.json").read_text())
    events = read_csv(output / "included_events.csv")
    long = read_csv(output / "event_abnormal_returns.csv")
    pairs = read_csv(output / "matched_pairs.csv")
    robustness = json.loads((output / "robustness.json").read_text()) if (output / "robustness.json").exists() else []
    result_rows = []
    for name, result in [("primary", primary)] + [(r["specification"], r) for r in robustness]:
        inference = result.get("issuer_cluster", {})
        interval = inference.get("ci95_pp") or [None, None]
        result_rows.append({"specification": name, "classification": "primary" if name == "primary" else "prespecified exploratory sensitivity",
                            "n_pairs": result.get("n_pairs", 0), "n_issuers": result.get("n_issuers", 0),
                            "n_calendar_quarters": result.get("n_calendar_quarters", 0),
                            "estimate_pp": result.get("estimate_pp"), "ci95_low_pp": interval[0],
                            "ci95_high_pp": interval[1], "p_one_sided": inference.get("p_one_sided"),
                            "p_two_sided": inference.get("p_two_sided"),
                            "inference_status": inference.get("status", result.get("status"))})
    write_csv(output / "results_table.csv", result_rows)
    if not long.empty and not events.empty:
        long = long[long.event_id.isin(events.event_id)].copy()
    else:
        long = long.iloc[0:0]
    trajectory = secondary_tables(events, long, output)
    numerical_cases(read_csv(output / "analytical_events.csv"), read_csv(output / "event_abnormal_returns.csv"), output, synthetic)
    label = "SYNTHETIC DEMO — NOT EMPIRICAL FINDINGS" if synthetic else "Filing-timed reactions — technical evidence"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.grid": True, "grid.alpha": .18})
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    for name, value, low, high, ylabel in [
        ("mean_abnormal_return", "aar_percent", "aar_ci_low", "aar_ci_high", "Mean abnormal return (%)"),
        ("cumulative_abnormal_return", "caar_percent", "caar_ci_low", "caar_ci_high", "Additive CAAR from session −5 (%)")]:
        fig, ax = plt.subplots(figsize=(8, 4.4))
        if not trajectory.empty:
            ax.plot(trajectory.offset, trajectory[value], marker="o", markersize=4, color="#185a6f")
            ax.fill_between(trajectory.offset, trajectory[low], trajectory[high], color="#185a6f", alpha=.15,
                            label="Pointwise issuer-cluster 95% CI where estimable")
            ax.axvline(0, color="#b56a39", linestyle="--")
            ax.axhline(0, color="#555555", linewidth=.8)
            ax.legend(fontsize=8)
        else:
            ax.text(.5, .5, "No eligible events — no curve estimated", ha="center", transform=ax.transAxes)
        ax.set(xlabel="Trading-session offset from verified acceptance alignment", ylabel=ylabel,
               title=f"{label}\nn={len(events)} qualifying events")
        fig.tight_layout()
        fig.savefig(figures / f"{name}.png", dpi=160, metadata={"Software": "eventstudy"})
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    estimate = primary["estimate_pp"]
    interval = primary["issuer_cluster"].get("ci95_pp")
    if estimate is not None:
        ax.scatter([estimate], [0], color="#185a6f", zorder=3)
        if interval:
            ax.hlines(0, interval[0], interval[1], color="#185a6f", linewidth=3)
        ax.axvline(0, color="#777", linestyle="--")
        ax.set_yticks([0], ["Event minus matched control"])
    else:
        ax.text(.5, .5, "No matched sample — primary hypothesis untestable", ha="center", transform=ax.transAxes)
        ax.set_yticks([])
    ax.set(xlabel="Difference in mean signed CAR[+1,+5] (percentage points)",
           title=f"{label}\nn={len(pairs)} pairs; issuer-cluster 95% CI where estimable")
    fig.tight_layout()
    fig.savefig(figures / "continuation_vs_reversal.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    if not pairs.empty:
        for i, col in enumerate(["event_signed_post_car", "control_signed_post_car"]):
            mean, interval = mean_interval(pairs, col)
            ax.bar(i, mean * 100, color=["#185a6f", "#b56a39"][i], width=.55)
            if interval:
                ax.errorbar(i, mean * 100, yerr=[[mean * 100 - interval[0]], [interval[1] - mean * 100]],
                            color="#333", capsize=4)
        ax.set_xticks([0, 1], ["Filing events", "Matched controls"])
    else:
        ax.text(.5, .5, "Comparison unavailable", ha="center", transform=ax.transAxes)
        ax.set_xticks([])
    ax.set(ylabel="Mean signed CAR[+1,+5] (%)", title=f"{label}\nSame paired sample, n={len(pairs)}; issuer-cluster 95% CI")
    fig.tight_layout()
    fig.savefig(figures / "filing_vs_control.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    axes[0].bar(["Requested", "With prices"], [summary["companies_requested"], summary["companies_with_prices"]], color="#185a6f")
    axes[0].set_ylabel("Companies")
    axes[1].bar(["Candidate", "Verified", "Large move", "Matched"],
                [summary["candidate_events"], summary["verified_events"], summary["included_large_move_events"], summary["matched_controls"]], color="#b56a39")
    axes[1].set_ylabel("Events / pairs")
    fig.suptitle(f"{label}\nCoverage; full exclusion reasons in exclusion_waterfall.json")
    fig.tight_layout()
    fig.savefig(figures / "sample_coverage.png", dpi=160)
    plt.close(fig)
    lines = [f"# {label}", "", "Generated technical evidence for Karol's audit. Not final publication prose.", "",
             f"Run status: **{summary['status']}**.", "", "| Count | Observed |", "|---|---:|"]
    for key, value in summary.items():
        if isinstance(value, int):
            lines.append(f"| {key} | {value} |")
    lines += ["", "Primary output: `primary_inference.json`; sensitivities: `robustness.json`.",
              f"Mean paired difference (percentage points): {primary['estimate_pp']}.",
              f"Issuer inference: {json.dumps(primary['issuer_cluster'])}.", "",
              "No event sample or significance is inferred when sources or cluster counts are insufficient.",
              "A date on a release does not establish its time. Daily returns include unrelated within-day trading.",
              "Threshold selection is retrospective. The selected surviving-stock universe limits generalization.",
              "Quarter-cluster sensitivity and issuer bootstrap do not eliminate all dependence or selection bias.", "",
              "## Evidence figures", ""]
    for path in sorted(figures.glob("*.png")):
        lines += [f"![{path.stem}](figures/{path.name})", ""]
    (output / "technical_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"report": str(output / "technical_report.md"), "figures": 5}


def report_from_config(config):
    root = Path(config["root"])
    source = root / config["paths"]["data"] / "processed"
    output = root / config["paths"]["reports"]
    output.mkdir(parents=True, exist_ok=True)
    if not (source / "run_summary.json").exists():
        raise FileNotFoundError("Run analysis before rendering the report")
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, output / path.name)
    interim = root / config["paths"]["data"] / "interim"
    for name in ["release_audit.json", "historical_identity.csv", "issuer_coverage.csv", "fetch_manifest.json",
                 "amendments.csv", "unresolved_items.csv", "all_filings.csv", "candidate_events.csv"]:
        if (interim / name).exists():
            shutil.copy2(interim / name, output / name)
    return render_report(output)

