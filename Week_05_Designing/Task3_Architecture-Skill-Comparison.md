# Architecture Skill Comparison

## What was compared

- **Direct work:** The OneSport architecture discussion and ADR in `ADR-001-onesport-architecture.md`, refined over multiple user turns. It includes three architecture options, then incorporates full platform ownership, burst handling, provider quotas, GDPR/regional concerns, freshness-over-availability priorities, queue/security/24/7 operations, and container-to-class-level design.
- **Skill-guided subagent:** An independent proposal and ADR outline generated after reading `.github/skills/architecture-proposal-adr/SKILL.md`, the OneSport requirements, and focused portions of the prior discussion records. The agent did not edit repository files.

The comparison is qualitative, not a controlled benchmark. The direct work received constraints incrementally in conversation; the agent received those already consolidated in its prompt and existing ADR. No reliable runtime, token, or cost measurements were available, so no numerical speedup is claimed.

## Comparison

| Dimension | Direct work | Skill-guided subagent |
|---|---|---|
| Requirements and constraints | Very high coverage after iterative clarification; the ADR was corrected when the user challenged an unsupported jurisdiction assumption. | High coverage in one response; explicitly identified unknown controller jurisdiction and distinguished requirements from assumptions. |
| Architecture alternatives | Three options and a clarified middle ground: modular monolith with separate workload roles and optional coarse catalog-read extraction. | Three structurally distinct options; correctly distinguished workload roles from independently deployed domain services. |
| Low-level implementation | More detailed: container/process topology, packages/classes, API routes, PostgreSQL constraints, job leasing, and named request/worker/deletion flows. | Useful component and flow descriptions, but mostly at proposal/ADR-outline level; less specific on class responsibilities, schema constraints, and deployment hardening. |
| Trade-off analysis | Deeper treatment of burst behavior, freshness budgets, queue age/expiry, provider quotas, GDPR deletion, and self-operated platform cost. | Clear and concise treatment of alternatives, queue limitations, staffing, security, and legal uncertainty; less exhaustive operational specification. |
| Communication efficiency | High detail, but required a long sequence of follow-up turns to capture evolving constraints and explain terms. | Compact, structured synthesis in a single agent response, benefiting from a pre-consolidated prompt. |
| Evidence of correctness | Architecture is reasoned from the requirements, but is still a proposal requiring load tests, provider contracts, platform capacity planning, and legal review. | Same limitation; independent analysis is not implementation or legal validation. |

## Assessment

The skill appears useful for **consistency and omission prevention**: it led the subagent to identify facts and unknowns, compare genuinely different designs, discuss burst limits and external quotas, and avoid inferring a jurisdiction. The subagent was more concise and efficient in producing a high-level comparison and ADR outline.

The direct ADR is stronger as an implementation-oriented deliverable because the conversation continued into low-level details and the design was revised based on the user's corrections and preferences. The skill-guided result did not reach comparable container-to-class depth, so its shorter response is not evidence that it completed the same total scope faster. Its accuracy also depends on the prompt carrying forward prior decisions; the skill cannot recover requirements that are not provided or found in project records.

**Conclusion:** Use the skill to bootstrap structured architecture analysis and an ADR. For detailed designs, continue with targeted follow-up questions and review the resulting architecture against measurable SLOs, provider terms, platform capacity, security operations, and legal advice. The experiment demonstrates better structure and concise synthesis, but does not establish a quantitative efficiency gain.

**Isolation:** The rerun was deliberately isolated. The subagent received only:

1. `.github/skills/architecture-proposal-adr/SKILL.md`
2. `Tasks/data/OneSport.txt`
3. `Tasks/Task_1.md`
4. `Tasks/Task_2.md`
5. The user's own statements about architecture alternatives, cost/maintainability/technology support, team ownership and no serverless, wave-shaped scaling, unknown provider APIs/quotas/pricing, GDPR, Europe/Middle East, mature technology choices, freshness/latency priority, jurisdiction question/correction, low-level detail, and RabbitMQ.

It was explicitly told **not** to inspect or use the existing ADR, discussion records, comparison report, session files, or prior assistant/subagent conclusions. It did not edit repository files. Its one response included the requirements and uncertainty inventory, three high-/low-level architecture proposals, a comparison/recommendation, queue/security/operations analysis, and an ADR draft. It correctly left jurisdiction open and explained that the actual controller entity and legal review are needed.

**Quality:** Includes an ADR draft and useful low-level details without access to the prior design. It explains the catalog-read extraction concretely and addresses provider limits, burst behavior, security, and human versus AI operations. Some implementation choices remain provisional, as they should. There are also consistency points to review before adopting it: the response mentions both team-operated Keycloak and locally stored password hashes in different passages, and suggests RabbitMQ in its selected design without first establishing that a database-backed job mechanism is insufficient. Its stale-data policy also needs to be reconciled with the user's strict freshness priority. These are review findings, not claims that the architecture is validated.

**Efficiency:** Compared with the direct iterative discussion, the subagent produced a broad architecture comparison and ADR draft in one invocation, while the direct work achieved more detailed class/container specification through follow-up turns. This is a qualitative process observation only - there are no measured time, token, or cost figures. The restricted run gives better evidence that the skill and raw inputs can elicit a useful independent result without giving the agent the prior conclusions.