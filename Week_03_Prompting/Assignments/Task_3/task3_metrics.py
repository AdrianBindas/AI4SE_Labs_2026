"""Task 3 - cost-per-accuracy metric family.

Original problem metric (Task 2): execution accuracy = fraction of the 155
questions whose predicted SQL returns the expected rows.

Accuracy answers "how good is the output?" but says nothing about what the
output *cost* to obtain. Two prompts can reach similar accuracy while differing
several-fold in tokens, credits, and wall-clock time. This module adds a metric
family that captures the price of correctness: cost-per-accuracy.

--------------------------------------------------------------------------------
Proposed metric: cost per correct answer (cost-per-accuracy)
--------------------------------------------------------------------------------

For each run we measure what one *correct* answer actually costs, by dividing the
consumed resource by the number of correct answers produced:

    credits_per_correct = credits_billed / correct
    tokens_per_correct  = total_tokens  / correct
    time_per_correct_s  = inference_time / correct

Equivalently these are resource-per-unit-accuracy (dividing by `correct` and
dividing by `accuracy` differ only by the constant total question count, 155),
so they rank prompts by *cost efficiency at producing correct output*. All are
"lower is better", the opposite polarity to accuracy. A composite normalised
score (credits per percentage-point of accuracy) is also reported:

    credits_per_accuracy_point = credits_billed / (accuracy * 100)

Together with accuracy these form a Quality/Cost profile: accuracy is the quality
gate, cost-per-correct is the efficiency tie-breaker.

Footnote metric (reported but deliberately minor): Expected Repeats-to-Correct,
ERC = 1/accuracy, the geometric-model expectation of how many attempts a typical
question would need if failures were re-run. Since this experiment ran exactly
one round with NO repeats, ERC is only an illustrative projection, not a measured
quantity, and is not used to rank the prompts.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from metrics_data import RunMetrics, get_runs


OUT_DIR = Path(__file__).resolve().parent


def expected_repeats_to_correct(accuracy: float) -> float:
    """Expected attempts until a typical question is answered correctly.

    Geometric-distribution expectation 1/p. Guard against p == 0.
    """
    if accuracy <= 0.0:
        return float("inf")
    return 1.0 / accuracy


def compute_metrics(run: RunMetrics) -> dict[str, float]:
    acc = run.accuracy
    erc = expected_repeats_to_correct(acc)
    correct = run.correct

    return {
        "prompt": run.prompt,
        "folder": run.folder,
        "model": run.model,
        # original metric
        "accuracy": acc,
        "correct": correct,
        "total": run.total,
        # raw cost inputs
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "total_tokens": run.total_tokens,
        "credits_billed": run.credits_billed,
        "inference_time_s": run.inference_time_s,
        # PRIMARY metric family: cost per accuracy (lower is better)
        "credits_per_correct": run.credits_billed / correct if correct else float("inf"),
        "tokens_per_correct": run.total_tokens / correct if correct else float("inf"),
        "time_per_correct_s": run.inference_time_s / correct if correct else float("inf"),
        "credits_per_accuracy_point": run.credits_billed / (acc * 100) if acc else float("inf"),
        # Footnote only (single round, no repeats): illustrative projection.
        "expected_repeats_to_correct": erc,
    }


def main() -> None:
    rows = [compute_metrics(run) for run in get_runs()]

    # Machine-readable output.
    json_path = OUT_DIR / "task3_metrics.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Flat CSV output.
    csv_path = OUT_DIR / "task3_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Console summary.
    header = (
        f"{'Prompt':6s} {'Acc':>7s} {'Cred/correct':>13s} {'Tok/correct':>12s} "
        f"{'Time/correct(s)':>16s} {'Cred/acc-pt':>12s} {'ERC(fn)':>8s}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['prompt']:6s} {r['accuracy']:7.4f} {r['credits_per_correct']:13.5f} "
            f"{r['tokens_per_correct']:12.1f} {r['time_per_correct_s']:16.2f} "
            f"{r['credits_per_accuracy_point']:12.5f} {r['expected_repeats_to_correct']:8.3f}"
        )
    print(f"\nWrote {json_path.name} and {csv_path.name}")


if __name__ == "__main__":
    main()
