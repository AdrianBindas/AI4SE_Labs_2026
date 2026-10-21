# Agentic Requirements Network Design

## Purpose

`requirements_network.py` implements a reusable Python workflow that reads a directory of `.txt` and `.eml` evidence and produces one traceable Markdown requirements specification. It uses LangGraph and the OpenAI API. Run it against a different corpus by supplying a different input directory; no source file paths are embedded in the workflow.

## Graph and agent perspectives

The graph first extracts candidate requirements from the same complete corpus using three distinct models and responsibilities:

| Analyst | Default model | Perspective |
|---|---|---|
| Functional | `gpt-5-mini` | Reports, queries, circulation, financial, inventory, patron, and administrative workflows |
| Stakeholder | `gpt-4.1-nano` | User classes, operational use cases, consolidated decisions, usability, and priority evidence |
| Technical | `gpt-5.4-nano` | Architecture, scale, accessibility, dependencies, privacy, testability, and conflicts |

The model IDs may be overridden individually with `REQUIREMENTS_MODEL_FUNCTIONAL`, `REQUIREMENTS_MODEL_STAKEHOLDER`, and `REQUIREMENTS_MODEL_TECHNICAL`. The three analyst models must remain distinct. A **Feedback Agent** independently critiques the candidates against the source corpus, and a **Summary Agent** synthesizes the final document. Both use `gpt-5-mini` by default and have their own model override variables.

API requests default to a 180-second timeout with no automatic retries so stalled model calls fail clearly rather than hanging for a long time. Tune with `REQUIREMENTS_MODEL_TIMEOUT` and `REQUIREMENTS_MODEL_RETRIES` if needed. Model-call start and completion times are logged by the CLI.

LangGraph flow:

```text
START -> functional analyst -> stakeholder analyst -> technical analyst
       -> deterministic score -> feedback review
          -> targeted originating analyst -> score -> feedback (up to 3 revisions)
          -> summary agent -> END
```

The reviewer identifies an origin agent and actionable feedback. Conditional graph edges send a revision to that analyst; the graph stops when feedback has no findings or the configurable revision limit is reached. Remaining feedback is recorded as unresolved rather than silently dropped.

## Deterministic scoring

The non-LLM Scoring node evaluates each candidate with an explicit 100-point rubric:

| Criterion | Points |
|---|---:|
| Valid, non-empty source-document traceability | 25 |
| Supporting evidence excerpt | 15 |
| Specific statement of at least 80 characters using a normative verb | 20 (8 if unmet) |
| Valid priority assignment | 10 |
| Model-reported confidence, scaled to 0–10 | 10 |
| Not an exact duplicate of another candidate | 20 (0 if duplicate) |

The default threshold is 70. The node records its score breakdown and flags deterministically. Exact text matching is only a warning signal; semantic deduplication and contradiction analysis are assigned to the Feedback and Summary Agents. Scores are quality-review signals, not a substitute for stakeholder priority.

## RISEN prompts and evidence handling

All model-backed nodes use prompts organized as Role, Instructions, Steps, End Goal, and Narrowing. Prompts explicitly include the assignment's network and output criteria, require schema-constrained handoffs, distinguish consolidated decisions from proposals, and prohibit invented consensus or unsupported requirements. The analyst roles differ by viewpoint; the Feedback Agent targets issues to an originating node; the Summary Agent preserves citations and accounts for every source document.

Input files are found recursively. Text documents use UTF-8; email documents are parsed with Python's email parser, retaining subject/date and textual body while omitting sender/recipient headers. Document IDs are relative paths. Each final requirement cites its source document IDs. The final output explains its priority scale, assigns unique IDs, groups requirements by type, contains an explained discarded-requirements section, lists unresolved conflicts and assumptions, and reports coverage for each input file.

For the supplied data, the agents should account for the draft SRS and Evergreen reference, technical and working-group minutes, interviews, survey, feature emails, finance thread, and PINES conversations. Particularly important review points include privacy versus patron-address outreach; historical reporting versus the relational/no-warehouse preference; proposed versus consolidated transfer behavior; and capacity/shelf-space definitions. Irrelevant email asides should not be converted into requirements. The Summary Agent should prefer later consolidated decisions when they resolve a disagreement and disclose unresolved policy or technical choices.

## Output and execution

The API key is loaded from a local `.env` file or the `OPENAI_API_KEY` environment variable; it is never written to source files. Keep `.env` out of version control. Install dependencies and run from the task directory:

```powershell
python -m pip install -r .\requirements.txt
python .\requirements_network.py .\data\corpus --output .\requirements_output.md --max-revisions 3
```

The retry limit defaults to three and can also be set through `REQUIREMENTS_MAX_REVISIONS`. Errors for invalid input directories, decoding, unknown model source references, incomplete source coverage, missing credentials, and failed structured output are surfaced rather than replaced by success-shaped output.

## Validation strategy

The unit suite checks recursive text/email loading, malformed input conditions, repeatable deterministic scoring, duplicate flags, feedback routing and retry exhaustion, and the rendered document's IDs, traceability, and required sections. Run it from the task directory:

```powershell
python -m unittest discover -s .\tests -v
```

An API-backed corpus run is the final integration check and requires working model access for all configured model IDs.
