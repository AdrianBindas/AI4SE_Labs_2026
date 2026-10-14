"""Shared measurement data for Task 3 and Task 4.

All raw numbers are transcribed from Week_03_Prompting/Solution.md, which records
the session telemetry for each of the three prompt runs (OODA, ICIO, RISEN).

Canonical choices (documented so the analysis is reproducible):

* Token counts come from the CLI/GUI session-summary line
  ("Tokens  up X ... down Y ..."). These are measured by the tooling itself and
  are the reliable, billing-side figure available for ALL three runs. The
  separate "Reported input/output tokens" fields are self-reported by the agent
  inside its own text output (only present for OODA, and not independently
  trustworthy), so they are kept here as `reported_*` for reference only and are
  NOT used in the comparison.
* Credits use "Credits billed" because it is reported for all three runs, whereas
  "Reported credits used" is missing for ICIO and RISEN.
* Inference time is converted to seconds.

The dataset for every run is the same 155 natural-language -> SQL questions.
"""

from __future__ import annotations

from dataclasses import dataclass


TOTAL_QUESTIONS = 155


@dataclass(frozen=True)
class RunMetrics:
    prompt: str              # framework name
    folder: str              # Task_2_* folder the predictions live in
    inference_time_s: float  # wall-clock generation time, seconds
    credits_billed: float    # credits actually billed for the run
    input_tokens: int        # CLI/GUI up-arrow total (prompt tokens, tool-measured)
    output_tokens: int       # CLI/GUI down-arrow total (completion tokens, tool-measured)
    correct: int             # number of correct queries (execution match)
    total: int               # number of questions attempted
    model: str               # underlying model
    # Reference-only fields, self-reported by the agent (not used in comparison):
    reported_credits: float | None = None
    reported_input_tokens: int | None = None
    reported_output_tokens: int | None = None

    @property
    def accuracy(self) -> float:
        return self.correct / self.total

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# Numbers transcribed from Task_1_Report.md.
RUNS: list[RunMetrics] = [
    RunMetrics(
        prompt="OODA",
        folder="Task_2_1",
        inference_time_s=8 * 60 + 15,          # 8m 15s
        credits_billed=4.43,
        input_tokens=1_100_000,                 # up 1.1m
        output_tokens=37_400,                   # down 37.4k
        correct=43,
        total=155,
        model="gpt-6-luna",
        reported_credits=2.98,
        reported_input_tokens=626_372,
        reported_output_tokens=31_331,
    ),
    RunMetrics(
        prompt="ICIO",
        folder="Task_2_2",
        inference_time_s=15 * 60 + 1,           # 15m 1s
        credits_billed=8.04,
        input_tokens=2_600_000,                 # up 2.6m
        output_tokens=66_400,                   # down 66.4k
        correct=154,
        total=155,
        model="gpt-6-luna",
        reported_credits=None,
        reported_input_tokens=None,
        reported_output_tokens=None,
    ),
    RunMetrics(
        prompt="RISEN",
        folder="Task_2_3",
        inference_time_s=17 * 60 + 59,          # 17m 59s
        credits_billed=3.21,
        input_tokens=756_900,                   # up 756.9k
        output_tokens=33_100,                   # down 33.1k
        correct=145,
        total=155,
        model="gpt-6-luna",
        reported_credits=None,
        reported_input_tokens=None,
        reported_output_tokens=None,
    ),
]


def get_runs() -> list[RunMetrics]:
    return list(RUNS)


if __name__ == "__main__":
    for run in RUNS:
        print(
            f"{run.prompt:6s} acc={run.accuracy:.4f} "
            f"in={run.input_tokens} out={run.output_tokens} "
            f"credits={run.credits_billed} time_s={run.inference_time_s}"
        )
