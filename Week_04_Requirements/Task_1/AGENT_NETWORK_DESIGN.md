# Agent Network Design

## Purpose

The network turns a folder of emails, meeting notes, interviews, surveys, and draft specifications into one organized software requirements document. Its main design choice is to have different agents read the same evidence from different viewpoints, then check their combined results before writing the final document.

## How the network works

Three analyst agents independently review every source document:

| Agent | Default model | What it looks for |
|---|---|---|
| Functional analyst | `gpt-5-mini` | Reports, queries, circulation, finance, inventory, and patron tasks |
| Stakeholder analyst | `gpt-4.1-nano` | Who needs each feature, how it is used, and which requests were agreed |
| Technical analyst | `gpt-5.4-nano` | System constraints, privacy, accessibility, performance, and unanswered questions |

Using different models and viewpoints reduces reliance on one reading of a large, mixed collection of documents. Each agent records where its proposed requirements came from, so the final document can be checked against the evidence.

A regular deterministic Scoring node checks basic qualities such as whether a requirement has a valid source, supporting evidence, a clear statement, and a priority. This score helps find weak entries; it does not decide how important a feature is to library staff.

Next, a Feedback Agent checks for missing topics, duplicate requests, unclear statements, and disagreements. When it finds an issue, the relevant analyst can revise its entry. The process stops when the reviewer has no further objections or reaches the configured limit. Remaining issues are shown in the final document rather than being quietly treated as resolved.

Finally, a Summary Agent combines the reviewed entries into one Markdown document. It assigns requirement IDs, combines duplicate requests while retaining their sources, explains the priority scale, and lists discarded items and unresolved decisions.

## Why this design fits the corpus

The example material includes both detailed specifications and informal email conversations. Some email threads contain a final agreed summary alongside earlier suggestions and unrelated asides. Separate readings help capture different types of needs; the review step helps distinguish an agreed requirement from a tentative idea or an irrelevant comment.

The network gives particular attention to source disagreements—for example, requests for historical reports alongside concerns about database impact, or requests for patron outreach alongside privacy requirements. It prefers a clear consolidated decision when the documents provide one. Otherwise, it calls out the open question for people to decide.

The result is easier to review than a raw collection of notes: each requirement has a name, priority, explanation, and source; duplicate entries are combined; and uncertainty remains visible. It is also reusable: provide another input directory instead of changing file paths in the program.

## Models, privacy, and running

The three analyst model IDs are deliberately different and can be changed through `REQUIREMENTS_MODEL_FUNCTIONAL`, `REQUIREMENTS_MODEL_STAKEHOLDER`, and `REQUIREMENTS_MODEL_TECHNICAL`. The Feedback and Summary Agents use `gpt-5-mini` by default.

The loader accepts `.txt` and `.eml` files recursively and uses their relative paths as source references. Email sender and recipient headers are omitted from the text given to the models. Prompts also instruct the agents not to repeat incidental personal details.

From the `Task_1` directory, install the listed packages and run:

```powershell
python -m pip install -r .\requirements.txt
python .\requirements_network.py .\data\corpus --output .\requirements_output.md --max-revisions 3
```

The revision limit can be lowered for a quick test. The pipeline logs model-call start and completion times and stops a stalled request after its configured timeout.
