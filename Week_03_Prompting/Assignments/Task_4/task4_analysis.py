"""Task 4 - detailed statistical analysis, tables and graphs.

Builds on Task 2 (accuracy) and Task 3 (cost-to-correctness metrics):

1. Re-scores each prompt per question (via score_predictions.score_all) to get
   true PAIRED binary outcomes over the same 155 questions.
2. Produces summary tables (accuracy with Wilson CIs, efficiency metrics).
3. Tests statistical significance:
     - Omnibus Cochran's Q across the three paired prompts.
     - Pairwise McNemar's exact test (paired, the correct test here) with a
       Holm correction for the three comparisons.
4. Renders graphs with matplotlib (saved as PNGs).

Outputs are written next to this script.
"""

from __future__ import annotations

import json
import math
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

from scipy import stats

import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "Task_3"))

from score_predictions import score_all          # noqa: E402
from metrics_data import get_runs                 # noqa: E402
from task3_metrics import compute_metrics         # noqa: E402


PROMPTS = ["OODA", "ICIO", "RISEN"]
ALPHA = 0.05


# --------------------------------------------------------------------------- #
# Statistics helpers
# --------------------------------------------------------------------------- #
def wilson_ci(correct: int, total: int, z: float = 1.959963985) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = correct / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(a: list[int], b: list[int]) -> dict:
    """Exact (binomial) McNemar test on paired 0/1 outcomes.

    b01 = cases where a is wrong but b is right.
    b10 = cases where a is right but b is wrong.
    """
    b01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    b10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n = b01 + b10
    if n == 0:
        p = 1.0
    else:
        k = min(b01, b10)
        # two-sided exact binomial test, p = 0.5
        p = min(1.0, 2.0 * stats.binom.cdf(k, n, 0.5))
    return {"discordant_b01": b01, "discordant_b10": b10, "n_discordant": n, "p_value": float(p)}


def cochran_q(vectors: dict[str, list[int]]) -> dict:
    """Cochran's Q omnibus test for k paired binary treatments."""
    labels = list(vectors)
    k = len(labels)
    mat = [vectors[l] for l in labels]
    n = len(mat[0])
    col_totals = [sum(mat[j][i] for j in range(k)) for i in range(n)]  # per question
    row_totals = [sum(v) for v in mat]                                 # per prompt
    grand = sum(row_totals)
    sum_row_sq = sum(t * t for t in row_totals)
    sum_col = sum(l for l in col_totals)
    sum_col_sq = sum(l * l for l in col_totals)
    numerator = (k - 1) * (k * sum_row_sq - grand * grand)
    denominator = k * sum_col - sum_col_sq
    q = numerator / denominator if denominator else float("nan")
    dof = k - 1
    p = float(stats.chi2.sf(q, dof)) if denominator else float("nan")
    return {"Q": float(q), "dof": dof, "p_value": float(p) if denominator else float("nan")}


def holm_correction(pairs: list[tuple[str, float]]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values."""
    ordered = sorted(pairs, key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running_max = 0.0
    for rank, (name, p) in enumerate(ordered):
        adj = min(1.0, (m - rank) * p)
        running_max = max(running_max, adj)  # enforce monotonicity
        adjusted[name] = running_max
    return adjusted


# --------------------------------------------------------------------------- #
# Plots
# --------------------------------------------------------------------------- #
def plot_accuracy(metrics: dict[str, dict], outcomes: dict[str, list[int]]) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = range(len(PROMPTS))
    accs = [metrics[p]["accuracy"] * 100 for p in PROMPTS]
    errs_low, errs_high = [], []
    for p in PROMPTS:
        lo, hi = wilson_ci(sum(outcomes[p]), len(outcomes[p]))
        errs_low.append((metrics[p]["accuracy"] - lo) * 100)
        errs_high.append((hi - metrics[p]["accuracy"]) * 100)
    colors = ["#d9534f", "#5cb85c", "#428bca"]
    bars = ax.bar(xs, accs, yerr=[errs_low, errs_high], capsize=6, color=colors)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(PROMPTS)
    ax.set_ylabel("Execution accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Accuracy by prompt (95% Wilson CI)")
    for b, a in zip(bars, accs):
        ax.text(b.get_x() + b.get_width() / 2, a + 1.5, f"{a:.2f}%", ha="center")
    fig.tight_layout()
    out = HERE / "fig_accuracy.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def plot_efficiency(metrics: dict[str, dict]) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    colors = ["#d9534f", "#5cb85c", "#428bca"]
    panels = [
        ("credits_per_correct", "Credits per correct answer"),
        ("tokens_per_correct", "Tokens per correct answer"),
        ("credits_per_accuracy_point", "Credits per accuracy point"),
    ]
    for ax, (key, title) in zip(axes, panels):
        vals = [metrics[p][key] for p in PROMPTS]
        bars = ax.bar(range(len(PROMPTS)), vals, color=colors)
        ax.set_xticks(range(len(PROMPTS)))
        ax.set_xticklabels(PROMPTS)
        ax.set_title(title)
        for b, v in zip(bars, vals):
            label = f"{v:,.0f}" if v > 100 else f"{v:.3f}"
            ax.text(b.get_x() + b.get_width() / 2, v, label, ha="center", va="bottom")
        ax.margins(y=0.18)
    fig.suptitle("Cost-to-correctness efficiency (lower is better)")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = HERE / "fig_efficiency.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def plot_accuracy_vs_cost(metrics: dict[str, dict]) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {"OODA": "#d9534f", "ICIO": "#5cb85c", "RISEN": "#428bca"}
    for p in PROMPTS:
        x = metrics[p]["credits_per_correct"]
        y = metrics[p]["accuracy"] * 100
        ax.scatter(x, y, s=160, color=colors[p], zorder=3)
        ax.annotate(p, (x, y), textcoords="offset points", xytext=(8, 6))
    ax.set_xlabel("Credits per correct answer (lower = cheaper)")
    ax.set_ylabel("Execution accuracy (%)")
    ax.set_title("Quality vs cost trade-off\n(top-left is best)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = HERE / "fig_accuracy_vs_cost.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    outcomes = score_all()
    runs = {r.prompt: r for r in get_runs()}
    metrics = {p: compute_metrics(runs[p]) for p in PROMPTS}

    # Significance
    q_result = cochran_q({p: outcomes[p] for p in PROMPTS})
    pairwise = {}
    raw_pairs = []
    for a, b in combinations(PROMPTS, 2):
        res = mcnemar_exact(outcomes[a], outcomes[b])
        pairwise[f"{a} vs {b}"] = res
        raw_pairs.append((f"{a} vs {b}", res["p_value"]))
    holm = holm_correction(raw_pairs)
    for name in pairwise:
        pairwise[name]["p_value_holm"] = float(holm[name])
        pairwise[name]["significant_holm"] = bool(holm[name] < ALPHA)

    # Wilson CIs
    cis = {p: wilson_ci(sum(outcomes[p]), len(outcomes[p])) for p in PROMPTS}

    summary = {
        "alpha": ALPHA,
        "accuracy_ci_wilson": {p: {"low": cis[p][0], "high": cis[p][1]} for p in PROMPTS},
        "cochran_q": q_result,
        "pairwise_mcnemar": pairwise,
        "metrics": metrics,
    }
    (HERE / "task4_stats.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Plots
    p1 = plot_accuracy(metrics, outcomes)
    p2 = plot_efficiency(metrics)
    p3 = plot_accuracy_vs_cost(metrics)

    # Console report
    print("=== Accuracy (95% Wilson CI) ===")
    for p in PROMPTS:
        lo, hi = cis[p]
        print(f"{p:6s} {metrics[p]['accuracy']*100:6.2f}%  CI[{lo*100:5.2f}, {hi*100:5.2f}]")

    print("\n=== Cochran's Q (omnibus, paired) ===")
    print(f"Q={q_result['Q']:.3f}  dof={q_result['dof']}  p={q_result['p_value']:.3e}")

    print("\n=== Pairwise McNemar exact (Holm-corrected) ===")
    for name, r in pairwise.items():
        print(
            f"{name:16s} b01={r['discordant_b01']:3d} b10={r['discordant_b10']:3d} "
            f"p={r['p_value']:.3e} p_holm={r['p_value_holm']:.3e} "
            f"{'SIGNIFICANT' if r['significant_holm'] else 'n.s.'}"
        )

    print("\nFigures written:")
    for pth in (p1, p2, p3):
        print(f"  {pth.name}")
    print("Stats written: task4_stats.json")


if __name__ == "__main__":
    main()
