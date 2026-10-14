# Task 3 Report — A Cost-per-Accuracy Metric for Text-to-SQL Prompts

## 1. Context

Task 2 generates one SQLite query for each of **155** natural-language questions
against the restaurants database, for three prompting frameworks:

| Prompt | Framework | Folder    | Accuracy (Task 2) |
|--------|-----------|-----------|-------------------|
| OODA   | Observe-Orient-Decide-Act | Task_2_1 | 27.74 % (43/155)  |
| ICIO   | Instruction-Context-Input-Output | Task_2_2 | 99.35 % (154/155) |
| RISEN  | Role-Instructions-Steps-End goal-Narrowing | Task_2_3 | 93.55 % (145/155) |

All three ran on the same model (`gpt-6-luna`) via the same coding agent.

The **original metric is execution accuracy**: the fraction of questions whose
predicted query returns exactly the expected rows. It answers *"how good is the
output?"* but is silent about what that output **cost** — tokens, credits, and
time. Two prompts can land at similar accuracy while differing several-fold in
price. That blind spot motivates the new metric.

## 2. Proposed metric — Cost per Accuracy

### 2.1 Definition

Instead of counting correct answers in the abstract, measure what one *correct*
answer actually costs, by dividing each consumed resource by the number of
correct answers the prompt produced:

```
credits_per_correct = credits_billed  / correct
tokens_per_correct  = total_tokens    / correct
time_per_correct_s  = inference_time  / correct
```

and a single normalised composite — credits spent per percentage point of
accuracy achieved:

```
credits_per_accuracy_point = credits_billed / (accuracy * 100)
```

(Dividing by `correct` and dividing by `accuracy` differ only by the constant
question count 155, so "per correct answer" and "per unit accuracy" rank the
prompts identically; both are reported for readability.) All of these are
**"lower is better"**, the opposite polarity to accuracy.

### 2.2 Why this is a good and applicable metric

- **It measures what teams actually pay for.** In an agentic SQL workflow you do
  not pay for "accuracy"; you pay credits, tokens, and wall-clock time to obtain
  correct queries. `credits_per_correct` and `credits_per_accuracy_point` express
  exactly that, in billed units.
- **It rewards efficiency that accuracy hides.** A prompt that is marginally less
  accurate but dramatically cheaper per correct answer can be the better
  engineering choice — accuracy alone cannot reveal this; cost-per-accuracy can.
- **It is computable from already-captured telemetry** (tokens, credits, time,
  correct count), so it needs no new experiments.
- **It is robust to batch size.** Normalising by `correct` (or by accuracy)
  makes the numbers comparable across runs of different sizes or question mixes.

### 2.3 Does it complement or replace the original metric?

**It complements, it does not replace.** Cost-per-accuracy has `correct`
(equivalently accuracy) in its denominator, so it cannot stand alone — a prompt
that outputs garbage cheaply would still score poorly because its `correct` count
collapses. Accuracy remains the quality anchor; the new family adds the **cost
axis**. The intended use is a two-axis decision: *accuracy first as a gate,
cost-per-accuracy second as the tie-breaker.*

## 3. Implementation

- `metrics_data.py` — raw measurements transcribed from `Task_1_Report.md`.
  Token counts use the **CLI/GUI session-summary** (`up`/`down`) line, which is
  tool-measured and present for all three runs; the agent's own
  "reported tokens" are self-reported, only present for OODA, and are kept as
  reference-only. Credits use **credits billed** (reported for all three).
- `task3_metrics.py` — computes the cost-per-accuracy family and writes
  `task3_metrics.csv` and `task3_metrics.json`.

Run:

```
python task3_metrics.py
```

## 4. Results

Measured inputs (canonical sources):

| Prompt | Accuracy | Correct | Input tok | Output tok | Credits billed | Inference time |
|--------|----------|---------|-----------|------------|----------------|----------------|
| OODA   | 0.2774   | 43      | 1,100,000 | 37,400     | 4.43           | 495 s (8m15s)  |
| ICIO   | 0.9935   | 154     | 2,600,000 | 66,400     | 8.04           | 901 s (15m01s) |
| RISEN  | 0.9355   | 145     | 756,900   | 33,100     | 3.21           | 1079 s (17m59s)|

Cost-per-accuracy (lower is better):

| Prompt | Accuracy | Credits / correct | Tokens / correct | Time / correct | Credits / accuracy point |
|--------|----------|-------------------|------------------|----------------|--------------------------|
| OODA   | 0.2774   | 0.1030            | 26,451           | 11.51 s        | 0.1597                   |
| ICIO   |**0.9935**| 0.0522            | 17,314           | **5.85 s**     | 0.0809                   |
| RISEN  | 0.9355   | **0.0221**        | **5,448**        | 7.44 s         | **0.0343**               |

## 5. Interpretation

- **OODA is dominated on every axis.** Lowest accuracy *and* the most expensive
  per correct answer (0.1030 credits, 26,451 tokens). It is both the worst and
  the costliest.
- **ICIO vs RISEN is the real trade-off.** ICIO is marginally more accurate
  (99.35 % vs 93.55 %, one extra question). But RISEN is **~2.4× cheaper per
  correct answer** (0.0221 vs 0.0522 credits), uses **~3.2× fewer tokens per
  correct answer** (5,448 vs 17,314), and costs **less than half** per accuracy
  point (0.0343 vs 0.0809). RISEN's tighter, step-scoped prompt simply does far
  more with far fewer tokens.
- **Decision.** If accuracy is a hard gate, both ICIO and RISEN clear it (>93 %);
  on the cost-per-accuracy tie-breaker **RISEN is the better engineering choice**,
  a conclusion accuracy alone could not surface. ICIO is preferable only when the
  single extra correct question is worth roughly doubling the cost.

The new metric therefore changes the ranking: by raw accuracy the order is
ICIO > RISEN > OODA, but by cost-per-accuracy the order is
**RISEN > ICIO > OODA**.

---

> **Footnote — Expected Repeats-to-Correct.** One can also project a retry
> burden via a geometric model, `ERC = 1/accuracy` (OODA 3.61, ICIO 1.01, RISEN
> 1.07), interpreting it as the mean attempts a typical question would need if
> failures were re-run. This experiment ran exactly **one round with no
> repeats**, so ERC is only an illustrative projection — not a measured quantity
> — and is deliberately not used to rank the prompts. It is reported in
> `task3_metrics.csv` for completeness.
