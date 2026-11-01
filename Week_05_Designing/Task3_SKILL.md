---
name: architecture-proposal-adr
description: Analyze software requirements, compare distinct architecture proposals, recommend an evidence-based approach, and produce a useful Architecture Decision Record (ADR).
---

# Architecture proposals and ADRs

Use this skill when asked to propose or compare software architectures, discuss architectural trade-offs, select an architecture, or create/revise an ADR.

## Goals

- Ground architecture in the supplied requirements and constraints; distinguish facts, assumptions, and open questions.
- Offer genuinely different alternatives, not differently named versions of the same design.
- Explain both system-level structure and implementation-level consequences in language a project team can evaluate.
- Recommend a choice only when requested or useful to the deliverable, and support it with requirements and trade-offs.
- Produce an ADR that records context, decision, alternatives, consequences, and validation, without pretending unknowns have been decided.

## Workflow

### 1. Read and classify inputs

1. Locate and read the complete requirements, relevant project/task instructions, existing architecture notes, and any prior discussion records available in the workspace.
2. Extract user-visible capabilities and quality attributes. Group capabilities into candidate domain boundaries.
3. Capture explicit constraints such as stack/platform ownership, hosting, budget, team expertise, geography, privacy/security obligations, availability, traffic shape, vendor limitations, and integration contracts.
4. Maintain a short facts/assumptions/open-questions list. Do not infer jurisdiction, scale targets, provider behavior, legal basis, budget, or technology preference from a user's location, repository path, or language.
5. Ask focused clarifying questions when a decision materially changes the architecture. If work must proceed, state provisional assumptions and their impact.

### 2. Propose alternatives

Unless the user specifies otherwise, present at least three meaningfully distinct alternatives, for example:

- a layered or three-tier monolith;
- a modular monolith, optionally separating independently scaled workload roles;
- independently deployable services or another justified distributed architecture.

Do not treat deployment roles (such as API and workers) as separate domain services unless they have independent boundaries, contracts, and ownership. Explain this distinction.

For each alternative describe:

- a high-level component/deployment diagram and responsibilities;
- domain/module boundaries and data ownership;
- representative low-level API, storage, integration, and asynchronous-work patterns;
- important user flows, including failure and overload behavior;
- a plausible, mature technology stack where requested, with alternatives and operational ownership;
- scaling characteristics, especially burst absorption, pre-provisioned capacity, scale-down, and bottlenecks;
- security, privacy, regional/data-residency, and deletion implications;
- implementation and operating costs, maintainability, interoperability, lock-in, and main risks.

Keep assumptions common across proposals consistent. Avoid ungrounded dollar estimates; identify the information needed for a total-cost estimate.

### 3. Compare and recommend

Use a concise decision matrix for criteria that matter to the requirements. Explain important trade-offs in prose, not scores alone. A recommendation should:

- name the selected option and why it best fits stated constraints;
- state what is explicitly not being selected and why;
- identify residual bottlenecks, operational burdens, and risks;
- give measurable triggers for revisiting the decision (for example load-test results or team ownership needs);
- avoid promising unlimited scaling; queues/autoscalers do not create capacity or external API quota.

### 4. Specify low-level design when requested

Detail only to the level requested, which may include:

- container/process roles, network boundaries, stateful dependencies, rollout/failure domains, and local/test setup;
- source package/module organization and class responsibilities;
- stable API contracts, request/authentication flows, persistence entities/constraints/indexes, and worker/job semantics;
- timeouts, retries, rate limits, idempotency, queue age/expiry, circuit breakers, backpressure, cache freshness, and graceful degradation;
- secret handling, least privilege, data minimization, audit, retention, recovery, observability, and operational staffing.

Explain optional components and the conditions that justify them. Do not add a queue, cache, service mesh, Kubernetes, or separate database merely because it is common.

### 5. Produce an ADR

Use a clear Markdown document with:

1. Title, status, date, and decision owners (mark unknown values as TBD).
2. Context: requirements, constraints, quality priorities, and unresolved facts.
3. Decision: selected architecture and explicit boundaries.
4. Architecture view and low-level implementation detail appropriate to the request.
5. Alternatives considered, including pros, cons, and reasons rejected/deferred.
6. Consequences: benefits, costs, risks, and operational responsibilities.
7. Security/privacy/compliance considerations where relevant, carefully separated from legal advice.
8. Rollout/validation plan with tests, metrics, and decision triggers.
9. Open questions and assumptions.

Use the repository's existing ADR naming/style if one exists. Keep generated documentation in the requested location. Do not overwrite unrelated user work; inspect existing files and integrate carefully.

## Quality checks

Before delivery, verify that:

- every important requirement is addressed by at least one component/flow;
- alternatives are actually distinct and compared against the same criteria;
- stated assumptions are visible and not confused with user requirements;
- burst handling includes limits, reserved capacity, overload policy, and recovery, not only autoscaling;
- external APIs include quota/cost policy, timeout/retry behavior, and stale-data semantics;
- personal data, account deletion, data residency/transfers, and operator access are covered when applicable;
- queues and caches have clear purpose, correctness boundaries, failure behavior, and operating costs;
- the ADR records a decision and its consequences rather than acting as an unstructured design catalog;
- only supported, mature technology versions/features are suggested when the user requests conservative choices.

## Communication

Lead with the result. Be concise in the final response, but provide enough detail to explain the choice and material trade-offs. State blockers and uncertainty plainly. Do not claim legal compliance, performance, or capacity without validation.
