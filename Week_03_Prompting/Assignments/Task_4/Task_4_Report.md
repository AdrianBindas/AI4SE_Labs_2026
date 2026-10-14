# Task 4 Report — Detailed Analysis of Prompt Comparison (OODA vs ICIO vs RISEN)

## 1. Scope

All three runs share the same setup — model `gpt-6-luna`, the same coding agent,
and the same 155 natural-language → SQLite questions — so the only varying
factor across runs is the prompt framework.

Reproduce everything with:

```
python task4_analysis.py
```

which re-scores predictions per question (`score_predictions.py`), runs the
significance tests, writes `task4_stats.json`, and renders the three figures.

## 2. Consolidated results table

| Prompt |   Accuracy  | Correct |   95% Wilson CI  | Credits/correct | Tokens/correct | Time/correct | Credits/acc-point |
|--------|-------------|---------|------------------|-----------------|----------------|--------------|-------------------|
| OODA   |   27.74 %   | 43/155  | [21.30, 35.26] % |   0.1030   |   26,451   | 11.51 s |   0.1597   |
| ICIO   | **99.35 %** | 154/155 | [96.44, 99.89] % |   0.0522   |   17,314   | 5.85 s  |   0.0809   |
| RISEN  |   93.55 %   | 145/155 | [88.53, 96.46] % | **0.0221** |  **5,448** | 7.44 s  | **0.0343** |

Raw inputs: OODA 1.10M in / 37.4k out tok, 4.43 credits, 495 s; ICIO 2.60M in /
66.4k out tok, 8.04 credits, 901 s; RISEN 756.9k in / 33.1k out tok, 3.21
credits, 1079 s. Token counts are the CLI/GUI tool-measured figures; the agent's
self-reported token numbers are not used.

## 3. Graphs

- `fig_accuracy.png` — accuracy per prompt with 95 % Wilson confidence intervals.
  The OODA interval sits far below and does not overlap ICIO or RISEN; the ICIO
  and RISEN intervals overlap only slightly at the top.
- `fig_efficiency.png` — three cost-per-accuracy panels (credits/correct,
  tokens/correct, credits per accuracy point). RISEN is lowest (best) in all
  three; OODA is highest (worst) in all three.
- `fig_accuracy_vs_cost.png` — the quality-vs-cost trade-off scatter. RISEN sits
  top-left (high accuracy, low cost), ICIO top-centre (highest accuracy, ~2.4×
  the cost), OODA bottom-right (low accuracy, highest cost).

## 4. Analysis

The `b10 = 0` entries are the key structural finding — the relationship is
perfectly **nested**:

- OODA solved **zero** questions that ICIO or RISEN got wrong. Everything OODA
  solved, both others also solved.
- RISEN solved **zero** questions that ICIO got wrong, while ICIO solved **9**
  that RISEN missed.

So the correct sets are strictly ordered by containment:
`OODA ⊂ RISEN ⊂ ICIO`. ICIO's advantage over RISEN is real but tiny (9 of 155
questions) and one-directional; RISEN never compensates with a question of its
own. This nesting is why even the narrow ICIO-vs-RISEN gap reaches significance:
McNemar sees a 9-vs-0 split with no noise in the other direction.

## 5. Why the differences look the way they do

The experiment isolates the **prompt** as the only varying factor,
which results in different ways the agent computed the answers.

### 5.1 Prompt

- **OODA (27.74 %)** is a decision-making loop (Observe-Orient-Decide-Act)
  borrowed from a non-software domain. Its phases tell the agent *how to think*
  but never pin down the concrete output contract — result column shape, join
  conventions, how to treat rating thresholds and "best". The agent orients
  freely and commits early ("Act"), so most queries are plausible but return the
  wrong rows. The failures are not random: the strict nesting shows OODA fails on
  exactly the harder questions the structured prompts handle, i.e. it lacks the
  specification that resolves ambiguity. 
- **ICIO (99.35 %)** spells out Instruction-Context-Input-Output. The explicit
  Output contract and Context (schema, joins, dump) remove exactly the ambiguity
  OODA left open, so almost every query matches. Its one miss is Q66 ("the life's
  greatest illusion"), an unanswerable question whose label contains 2,696 rows —
  effectively impossible to reproduce from the wording. ICIO reaches it by
  spending the most: 2.6M input tokens and 8.04 credits.
- **RISEN (93.55 %)** adds Role + explicit Steps + a Narrowing section of hard
  constraints ("use only verified tables/columns", strict `>`, one query per
  question). This tight scoping is why RISEN is by far the most token- and
  credit-efficient (5,448 tokens/correct vs ICIO's 17,314), but the same brevity
  gives it slightly less latitude to brute-force the 9 awkward edge cases ICIO
  catches by exploring more.

The core trade-off: ICIO buys the last few questions with large context
expansion; RISEN gets 93 % of the way at roughly a third of the token cost.

### 5.2 Computation
- **OODA** Model followed the OODA prompt, analyzed database schema and dump,
and proceeded to reason about each question and output a single SQL query without running SQL engine.
The model did not engage in any self-reflection or going over it's input multiple times.
- **ICIO** Model followed the ICIO prompt, did not run SQL engine, used regex to fetch relevant data
from the db dump. Extensive self-reflection and large amount of regex queries resulted in large costs.
- **RISEN** Model followed the RISEN prompt loosely, did not run SQL engine, used regex to fetch
relevant data from the db dump. Model placed large importance on effectivity and on analyzing
the SQL database and drew conclusions. Used regex and PowerShell to read files.

## 6. Conclusion

- The prompt choice produces **statistically significant** differences in
  accuracy (Cochran Q p ≈ 2.4e-45; all pairwise McNemar comparisons significant
  after Holm correction).
- By **accuracy** the ranking is **ICIO > RISEN > OODA**, with a strictly nested
  correct-set structure (OODA ⊂ RISEN ⊂ ICIO).
- By **cost-per-accuracy** (Task 3) the ranking flips to **RISEN > ICIO >
  OODA**: RISEN reaches 93.5 % at ~2.4× lower credits-per-correct and ~3× fewer
  tokens-per-correct than ICIO (and ~2.4× lower credits per accuracy point).
- **Recommendation:** use ICIO when the single hardest question matters and cost
  is secondary; use **RISEN as the default** for its near-equal accuracy at a
  fraction of the cost. OODA is dominated on every axis and is unsuitable for
  this task. The underlying driver is specificity of the output contract and
  constraints, not the model or agent, which were constant across runs.
