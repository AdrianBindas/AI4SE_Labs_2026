# ADR-001: OneSport application architecture

- **Status:** Proposed
- **Date:** 2026-11-01
- **Decision owners:** OneSport project team

## Context

OneSport provides current sports news and event/ticket discovery, personal saved lists, user accounts, and friend relationships. The requirements include signup/login/logout, profile and credential changes, account deletion, country-filtered news and events, saving/removing/clearing items, ticket purchase handoff, user lookup by email, and friend-request workflows.

The team requires full ownership of the application stack and platform. Serverless and managed runtime, database, queue, and identity services are out of scope. The intended audience is primarily in Europe and the Middle East. Average growth is expected to be slow, but traffic can arrive in sharp waves and then recede. News and ticket providers, API quotas, available offers, and pricing are not yet known. GDPR applies.

The product priority is **low response latency and fresh content, even if lower-priority functions become temporarily unavailable during a burst**. This is not a request to serve arbitrarily stale content or to exceed provider quotas. The repository currently contains requirements and architecture research, not a deployed OneSport system. Traffic envelopes, numeric latency/freshness targets, team/platform capacity, provider terms, and data-location decisions remain to be established. This ADR records a proposed starting architecture, not a claim that arbitrary traffic spikes can be handled without provisioned capacity.

## Decision

Adopt a **modular monolith with independently provisioned workload roles** as the recommended starting architecture:

- Keep the domain modules in one codebase and one application release initially.
- Run stateless interactive API replicas separately from asynchronous news/ticket ingestion workers. They may scale to different replica counts and have separate resource limits, while using in-process module calls rather than service-to-service calls.
- Use a team-operated PostgreSQL primary as the system of record. Add a self-operated cache for public catalog reads where useful; add a read replica only after load tests show the primary is pressured by suitable read workloads.
- Buffer ingestion work in durable queues when needed. Queue depth controls worker concurrency only within pre-provisioned compute, database connection budgets, and provider-specific quotas.
- Keep provider integrations behind replaceable adapters. Treat the ticket purchase as an external handoff unless a booking/payment requirement is later approved.
- Maintain a path to deploy a coarse-grained catalog-read application from the same codebase if measurements show public catalog reads are crowding out account, library, or social operations. This is a later scaling step, not an initial microservice decomposition.
- Use explicit freshness budgets and fast load shedding. Prefer a quick, honest unavailable response for a function whose freshness/latency target cannot be met over a slow response or misleading stale ticket offer.
- Use queues only for asynchronous work that may wait (primarily provider ingestion). Do not queue synchronous user reads or writes merely to hide overload.

### High-level view

```text
 Web / mobile clients
          |
 Team-operated load balancer / reverse proxy
          |
   +------+--------------------------+
   |                                 |
   v                                 v
Stateless API pool             Ingestion worker pool
accounts, catalog,              scheduled/queued provider
library, social                 refresh and normalization
   |                                 |
   +---------------+-----------------+
                   |
         PostgreSQL primary
        + optional read replica
                   |
      self-operated catalog cache
                   |
          provider adapters
             /         \
         News APIs   Ticket APIs
```

The API and worker roles are separate processes/deployments for capacity and workload isolation, but are not independent domain services: they share the modular codebase, release version, and initial relational database. A self-operated queue such as RabbitMQ can be introduced for durable refresh jobs; it is not required if a simpler database-backed job mechanism meets measured needs.

### Domain and data boundaries

Organize the application into modules with explicit public interfaces and owned persistence access:

1. **Identity and profile** — account lifecycle, credentials, profile settings, and deletion state.
2. **News catalog** — normalized news items, country filters, provider adapters, freshness.
3. **Events and tickets** — events, offers, availability freshness, and purchase handoff.
4. **Personal library** — saved news/tickets and clear/remove operations.
5. **Social graph** — email lookup boundary, requests, acceptance/refusal, friendships.

Use PostgreSQL tables/entities such as `User`, `Profile`, `NewsArticle`, `SportEvent`, `TicketOffer`, `SavedNews`, `SavedTicket`, `FriendRequest`, and `Friendship`. Enforce unique provider item identifiers, unique user/item saves, valid relationship state transitions, and foreign keys where practical. Index catalog queries by country and publication/event time. Keep cross-module reads behind module interfaces rather than allowing arbitrary table access.

### Low-level request and workload handling

- API endpoints use versioned REST/JSON contracts described with OpenAPI. Authenticate requests using a proven OIDC-compatible implementation operated by the team; authorize personal-library and social operations using the authenticated subject, never a caller-supplied user ID.
- API replicas remain stateless. Use secure tokens or team-operated shared session storage so any replica can serve a request. Apply health/readiness checks, request timeouts, admission control, rate limits, and bounded connection pools.
- Provider workers fetch incrementally, normalize data, and perform idempotent upserts. Configure each provider independently for credentials, allowed request rate, spend ceilings where supported, polling schedule, freshness target, and circuit-breaker state.
- Do not drain a backlog faster than provider quota or budget permits. Use bounded retries, dead-letter handling, deduplication, and queue-age/freshness metrics. Coalesce duplicate refresh requests and expire work that cannot meet its freshness deadline. When provider data exceeds its defined maximum age or a ticket offer cannot be revalidated, return a fast explicit unavailable/temporarily unavailable result rather than presenting it as fresh. Within the allowed freshness window, display the last-fetch time.
- For ticket handoff, expose offer freshness and revalidate availability within a bounded provider request budget before creating the external purchase session. Do not record a completed purchase without provider confirmation or store card data.
- For a public catalog surge, use a self-operated reverse-proxy/cache with explicit country-aware keys, freshness metadata, and TTLs that do not exceed the approved freshness budget. Do not place personal collections or social responses in shared public cache entries. If catalog reads still compete with transactional operations, test query/index improvements and a PostgreSQL read replica before extracting a catalog-read deployment.
- Use an outbox or durable job record when committing application state and enqueueing work must be reliable. Consumers must be idempotent. When capacity is constrained, reserve resources for catalog reads and account/session security; temporarily reject or disable lower-priority social mutations, profile edits, and nonessential background work according to a documented priority policy.

## Low-level implementation specification

This section turns the selected architecture into an initial deployable shape. It is a starting specification: exact replica counts, memory/CPU requests, freshness limits, retention windows, and provider schedules must come from load tests, provider contracts, and operational policy.

### Container and process topology

Build one versioned OneSport OCI image and execute it in separate process roles. API and worker replicas share the codebase and release version but have different entry points, resource ceilings, probes, and network access.

```text
Public network
   |
Self-operated HAProxy/NGINX (TLS, request limits, health routing)
   |
   +-- API Deployment: 2+ warm stateless replicas
   |      |-- Identity/profile, catalog, library, social HTTP APIs
   |      |-- outbound access to Keycloak; PostgreSQL; optional Redis
   |      `-- no direct calls to news/ticket providers
   |
   +-- Worker Deployment: separate bounded replica pool
   |      |-- provider refresh, normalization, cleanup, deletion jobs
   |      `-- outbound access to providers; PostgreSQL; optional RabbitMQ
   |
   +-- Self-operated Keycloak (OIDC) --> team-operated PostgreSQL
   +-- OneSport PostgreSQL primary --> optional same-region read replica
   +-- Optional self-operated RabbitMQ and Redis
   `-- Prometheus/OpenTelemetry collector/logging/alerting
```

- **Required at initial deployment:** ingress, at least two API instances distributed across failure domains where available, worker process capacity, PostgreSQL, monitoring, backups, and a tested restore process.
- **Add only when justified:** RabbitMQ for durable queueing, Redis for bounded catalog caching/rate-limit state, PostgreSQL read replica, and Kubernetes. On a small team-operated platform, Linux LTS VMs with systemd and containers may be simpler and safer than operating Kubernetes. If Kubernetes is used, it is self-managed and its control plane/node failure is the team's responsibility.
- Run Keycloak as a team-operated identity component, not a managed identity dependency. Keep its database and OneSport database logically separated (at minimum separate databases/roles and credentials); do not let application services query Keycloak tables. OneSport stores its own profile and authorization/domain records keyed by the OIDC subject.
- Do not require Redis or RabbitMQ for API correctness. If Redis is unavailable, bypass cache within bounded database limits; if the queue is unavailable, pause ingestion and alert rather than silently losing work. A database-backed job table can be an initial simpler alternative, provided worker claiming is concurrency-safe.
- Use internal network segmentation: only ingress is public; application ports, database, cache, queue, telemetry, and administrative endpoints are private. Worker egress is allowlisted to provider endpoints where practical. Separate production, staging, and development credentials and data.
- Containers run as non-root with read-only root filesystem where practical, dropped capabilities, resource requests/limits, graceful shutdown, health/readiness endpoints, pinned image digests, and no embedded secrets. Mount only required writable temporary paths. Logs go to stdout in structured form with PII redaction.
- For local development, a compose-based environment may run the same API/worker image with PostgreSQL and optional dependencies; never copy production personal data into developer environments.

### Java package/module and class responsibilities

Illustrative package layout:

```text
com.onesport
  api
    config/                 # HTTP, JSON, OpenAPI, security and health config
    error/                  # stable problem response mapping
  identity
    api/ application/ domain/ infrastructure/
  news
    api/ application/ domain/ infrastructure/
  events
    api/ application/ domain/ infrastructure/
  library
    api/ application/ domain/ infrastructure/
  social
    api/ application/ domain/ infrastructure/
  jobs
    application/ scheduling/ messaging/
  shared
    clock/ ids/ country/ outbox/ observability/
```

The `api` packages translate HTTP input/output and enforce transport-level concerns; `application` contains use-case orchestration; `domain` contains invariants and domain types; `infrastructure` implements repository/provider ports. Do not let controllers contain SQL, provider logic, or multi-step domain policy. Domain modules call another module only through its application interface, not by reaching into its repositories.

| Module | Representative classes and responsibility |
|---|---|
| `identity` | `OidcPrincipal`/Spring Security integration maps the validated `sub` claim to the OneSport user ID. `ProfileController` maps profile requests. `GetMyProfile`, `UpdateProfile`, `RequestAccountDeletion` are use cases. `Profile` enforces editable-field rules. `ProfileRepository` is a port; `JpaProfileRepository` implements it. `AccountDeletionService` marks the local account deleting and creates durable cleanup work. Keycloak owns credentials and authentication lifecycle; `KeycloakAdminClient` is a narrowly scoped adapter for approved credential/account actions, never a generic admin proxy. |
| `news` | `NewsController` accepts country/cursor filters. `ListNews` reads normalized articles and freshness metadata. `NewsArticle` is the normalized catalog record. `NewsProvider` defines `fetchUpdates(cursor)`; `ProviderRegistry` selects configured providers; `NewsProviderAdapter` maps a concrete provider response to domain input. `NewsArticleRepository.upsertBatch` performs idempotent persistence. |
| `events` | `EventController` and `ListEvents` provide upcoming events. `TicketOfferController` and `GetOffer` expose offer state and `availabilityCheckedAt`. `TicketProvider` defines event/offer refresh plus bounded offer revalidation. `CreatePurchaseHandoff` verifies freshness and quota policy before returning a provider URL/session; it does not mark a sale complete. |
| `library` | `SavedNewsController`/`SavedTicketController` map save/list/delete/clear operations. `SaveNews`, `RemoveNews`, `ListSavedNews`, `ClearSavedItems` are use cases. `SavedNewsRepository` and `SavedTicketRepository` use authenticated user ID and unique constraints for idempotent saves. |
| `social` | `FriendRequestController` maps send/list/accept/refuse operations. `FindUserByEmail` calls a narrow authenticated lookup interface and applies anti-enumeration policy. `SendFriendRequest`, `RespondToFriendRequest`, `RemoveFriend`, `ListFriends` enforce relationship state transitions. `Friendship`/`FriendRequest` aggregates reject self-links and duplicate pending requests. |
| `jobs` | `RefreshProviderJob` executes quota-aware provider refresh. `JobScheduler` creates due work. `JobLeaseRepository` safely claims due jobs across worker replicas. `OutboxPublisher` publishes committed outbox records if a broker is enabled. `DeadLetterReview` emits alerts/metrics; it does not silently discard repeated failures. |
| `shared` | `CountryCode` validates ISO country codes; `PageCursor` provides stable pagination; `Clock` makes freshness decisions testable; `ProblemDetailsMapper` produces stable HTTP errors; `CorrelationIdFilter` propagates a request ID without logging sensitive values. |

Use constructor injection, explicit interfaces for external providers and persistence, and focused unit tests for domain invariants. Avoid a generic `CommonService` or shared mutable domain objects. Keep DTOs separate from persistence entities so API schema changes do not force database/domain changes.

### HTTP/API contracts and burst behavior

Representative routes:

```text
GET    /api/v1/news?country=IT&cursor=...
GET    /api/v1/events?country=IT&cursor=...
GET    /api/v1/ticket-offers/{offerId}
POST   /api/v1/ticket-offers/{offerId}/purchase-handoff
GET    /api/v1/me/profile
PATCH  /api/v1/me/profile
GET    /api/v1/me/saved-news
PUT    /api/v1/me/saved-news/{articleId}
DELETE /api/v1/me/saved-news/{articleId}
DELETE /api/v1/me/saved-items
POST   /api/v1/me/friend-requests
GET    /api/v1/me/friend-requests/incoming
POST   /api/v1/me/friend-requests/{requestId}/accept
POST   /api/v1/me/friend-requests/{requestId}/refuse
GET    /api/v1/me/friends
DELETE /api/v1/me/friends/{friendUserId}
DELETE /api/v1/me/account
```

Use cursor pagination, bounded page sizes, validated filters, stable public identifiers, and a versioned error schema. Return `429` for caller-specific rate limits and `503` with a short `Retry-After` for system overload or unavailable fresh provider data; do not keep requests waiting in a queue. Catalog responses include `fetchedAt`/freshness state. Use `Cache-Control`/ETag only for public catalog responses and ensure the key includes country, query, and representation version. Never let a shared cache serve authenticated `/me` responses.

### Persistence layout and constraints

Use PostgreSQL migrations under source control. Initial schema ownership can be represented as schemas/tables within one database; module owners control their own migrations. The single primary enables local transactions but is still a shared capacity/failure boundary.

Representative constraints/indexes:

- `profile(user_id PK, email/display fields as required, ...)`; OIDC `sub` is unique. Avoid duplicating credential secrets from Keycloak.
- `news_article(id PK, provider_id, provider_item_id, country_code, published_at, fetched_at, ...)`, unique `(provider_id, provider_item_id)` and index `(country_code, published_at DESC, id)`.
- `sport_event` with stable provider identity and index `(country_code, starts_at, id)`.
- `ticket_offer(event_id FK, provider_offer_id, price, currency, availability_checked_at, ...)`, unique provider identity and index `(event_id, availability_checked_at)`.
- `saved_news(user_id FK, article_id FK, saved_at, PK(user_id, article_id))`; equivalent `saved_ticket`. Clear-all is scoped by authenticated user and transactional/batched if row counts require it.
- `friend_request(sender_id, recipient_id, status, created_at, responded_at)` with sender != recipient; enforce one pending request per ordered pair using a partial unique index where supported or a transaction/locking strategy. `friendship` stores a canonical ordered pair `(min_user_id, max_user_id)` with unique constraint and `min_user_id < max_user_id`.
- `provider_config`/secret references store enabled state, quota/poll policy, and secret reference—not plaintext credentials in ordinary tables. `provider_sync_state` stores cursor, last success, next due time, and freshness. A `refresh_job` table has status, priority, not-before, expiry, attempt count, and lease fields. Claim due jobs atomically (for example `SELECT ... FOR UPDATE SKIP LOCKED` plus a lease) so worker replicas do not run the same job concurrently. `outbox_event` stores event ID/type/schema version, minimal payload, created/published timestamps.
- Index actual query patterns; verify plans with representative load. Keep catalog payloads bounded and avoid indexing unnecessary personal fields.

Set database connection limits by calculating `API replicas × per-replica pool + worker pools + Keycloak + maintenance reserve`. Apply statement/transaction timeouts. If a read replica is introduced, monitor replay lag and route freshness-sensitive reads to the primary or return unavailable when lag exceeds the content freshness budget. Use TLS, least-privilege DB roles, encrypted storage, point-in-time recovery, tested restores, and approved retention for backups.

### Core class-level flows

**Fresh news request**

1. `NewsController.list(country, cursor)` validates the ISO country and page bounds.
2. `ListNews` checks the self-operated catalog cache using a key that includes the normalized country/cursor and freshness policy.
3. On cache miss, `NewsArticleRepository.findRecent(country, cursor, limit)` executes an indexed query against the catalog read source. It does not synchronously call provider APIs.
4. `NewsController` returns normalized DTOs plus `fetchedAt`/freshness metadata. If data age exceeds the configured maximum, it returns an explicit unavailable response rather than falsely labeling stale results current.

**Provider refresh**

1. `JobScheduler` creates/coalesces due provider work using `provider_sync_state`; it honors the provider schedule and request budget before dispatch.
2. A worker obtains a bounded lease (`JobLeaseRepository.claimNext`) and asks `ProviderRegistry` for the provider adapter.
3. `NewsProviderAdapter.fetchUpdates(cursor)` uses connect/read timeouts, bounded response size, provider rate limit, circuit breaker, and conditional requests where permitted.
4. The adapter maps to validated domain records; `NewsArticleRepository.upsertBatch` stores items and the new sync cursor transactionally. Duplicate delivery is safe.
5. On transient failure, retry with bounded exponential backoff+jitter only before job expiry; permanent/schema/quota failures are surfaced and dead-lettered with redacted diagnostics. Do not hot-loop or silently spend beyond cap.

**Save article**

1. Spring Security validates the OIDC access token and places the subject in the security context.
2. `SavedNewsController` derives user ID from that context; it ignores any user ID in the body/path.
3. `SaveNews` checks that the account is active and the catalog item is valid according to the agreed module/database policy, then `SavedNewsRepository.insertIfAbsent(userId, articleId)` relies on the composite unique key for idempotency.
4. Return success for an already-saved item as an idempotent `PUT`; authorization failures do not reveal another user's data.

**Ticket handoff**

1. `CreatePurchaseHandoff` loads the offer and checks `availabilityCheckedAt` against the freshness limit.
2. If a bounded provider revalidation is allowed and the offer is stale, call the ticket adapter with a short deadline and quota/spend check; otherwise return a fast unavailable response.
3. On valid response, return the provider handoff URL/session and an expiry time. Do not accept client-supplied prices or claim purchase completion without a provider confirmation contract.

**Account deletion**

1. `RequestAccountDeletion` authenticates and re-confirms the operation, then marks the OneSport profile `DELETION_PENDING` and prevents new sessions/actions.
2. In one local transaction, create a deletion job/outbox record. The worker idempotently deletes/anonymizes saved items, friend requests/friendships, profile data, and any other OneSport personal records under approved policy.
3. Revoke/disable the identity at Keycloak through a narrow adapter and record completion; retries are safe and observable. If identity service is unavailable, retain a pending deletion state and retry rather than report success prematurely.
4. Apply documented retention/expiry to logs, backups, queues, and audit records; preserve only data with an approved legal basis and retention period. User-facing status must distinguish request accepted from deletion completed where processing is asynchronous.

### Identity, authorization, security, and observability boundaries

- Use team-operated Keycloak as the OIDC provider. Configure authorization-code flow with PKCE for browser/public clients; validate issuer, audience, signature, expiry, and nonce/state as appropriate. API services validate tokens locally using trusted keys and never accept unsigned or client-asserted identities.
- Use short-lived access tokens and controlled refresh/logout/revocation semantics. Keep client secrets out of browser apps. Profile email changes must update identity and OneSport profile consistently with a recoverable workflow; do not claim a change succeeded in only one system.
- Enforce authorization in application use cases in addition to URL-level guards. Apply per-IP and per-account rate limits to login, email lookup, friend requests, and ticket handoff. Return privacy-preserving results for user discovery.
- Administrative access uses MFA, least privilege, audited elevation, and separate production credentials. Secrets are injected from an access-controlled team-operated mechanism, rotated, and excluded from logs/images/source.
- Emit metrics for request latency/status by route class, saturation/rejections, DB pool wait, cache hit/freshness, provider calls/429s/quota/spend, worker oldest-job age, job expiry/dead-letter counts, and deletion completion time. Never use email/user ID as metric labels. Trace IDs are for correlation and logs redact credentials, tokens, and unnecessary personal data.
- Alert on SLO burn, inability to meet freshness budgets, loss of warm headroom, provider quota exhaustion, repeated job failures, DB saturation, backup/restore failures, identity outages, and suspected security events. AI may summarize redacted diagnostics, but operational controls are deterministic and privileged remediation requires human approval.

## Technology and platform baseline

Use mature, broadly supported technologies; at implementation time select supported, patched releases and avoid preview features:

| Area | Recommended baseline |
|---|---|
| Web client | TypeScript and React |
| API and worker | Java LTS (initially Java 21) and Spring Boot supported stable release |
| API contract | REST/JSON with OpenAPI; OIDC/OAuth 2.0 at identity boundaries |
| System of record | Team-operated PostgreSQL |
| Cache | Optional team-operated Redis or reverse-proxy cache, only for bounded non-authoritative data |
| Background jobs | Start simple; self-operated RabbitMQ when durable queueing/isolation is needed |
| Runtime | Linux LTS and OCI containers; systemd/containers on VMs or self-managed Kubernetes according to platform-team capacity |
| Ingress | Team-operated HAProxy or NGINX |
| Observability | OpenTelemetry instrumentation, Prometheus metrics, Grafana dashboards, centralized structured logs and alerts |

These are recommendations, not a mandate to operate every listed component. Prefer fewer stateful systems. The team owns host/network capacity, patching, secrets, database and queue availability, monitoring, backups, restore tests, disaster recovery, and on-call response. Do not make a cloud-specific API or managed control plane necessary for the core system.

## Burst capacity and scale-down

No autoscaler can create unreserved hardware or provider quota. Define and test an explicit burst envelope: peak request rate, duration/ramp, concurrency, geographic distribution, ingestion volume, and acceptable freshness/latency. Reserve warm API, worker, database, network, and queue capacity for that envelope.

- Scale API replicas horizontally within the reserved node pool, with hard replica/resource limits. Keep a safe minimum warm count and roll out gradually.
- Scale ingestion workers from queue age/depth, but cap concurrency using reserved CPU, PostgreSQL connection budgets, and each provider's quotas and spend limits.
- Protect PostgreSQL with bounded connection pools, query budgets, indexes, admission control, and backpressure. API replica count must not create more database connections than the database can safely serve.
- Serve cached public catalog data only while its age is within the feature's freshness budget; defer low-priority refreshes. If fresh data cannot be obtained, fail quickly and clearly rather than wait on a provider or silently serve out-of-budget data. Prefer graceful throttling to retry storms or cascading failure.
- If catalog reads are proven to be the bottleneck, move them to a separately deployed read-only catalog API from the same repository, backed by an appropriate read replica/read model and cache. This is a coarse-grained extraction; it does not require splitting identity, saved lists, and friendships into services.
- Scale down with stabilization windows and minimums to avoid flapping. Alert on spare headroom, request latency/rejection, DB saturation, queue age, provider quota/spend, and data freshness. Test sudden-load, provider-outage, and recovery scenarios.

### Burst-time service priorities

The team should agree numeric SLOs and maximum content ages before launch. The ordering below makes the stated preference actionable; it is not a guarantee when a provider or owned infrastructure is unavailable.

| Priority | Workload | Burst behavior |
|---|---|---|
| 1 | Authentication/session validation and safe, fresh catalog reads | Reserve capacity; apply strict latency and concurrency budgets. Use only cache entries inside the approved freshness window. |
| 2 | Ticket offer details and purchase handoff | Revalidate availability/price within the provider's quota. If validation cannot complete within the latency/freshness budget, mark offers unavailable rather than showing a potentially misleading offer. |
| 3 | Saved-list reads and writes | Keep available where capacity permits; writes are authenticated and transactional. Apply per-user limits and fast overload responses rather than waiting in a queue. |
| 4 | Profile edits and social actions (friend lookup/requests) | May be rate-limited or temporarily disabled during a severe burst. Return a clear retry response and do not accept a mutation that cannot be durably committed. |
| 5 | Nonessential refreshes, enrichment, analytics, maintenance | Defer, coalesce, or expire work. Never let backlog processing consume capacity reserved for interactive traffic or exceed provider spend/quotas. |

### Queueing: benefits, limits, and operating cost

Queues are useful for provider polling, normalization, retries, and other work that is naturally asynchronous. They absorb a short-term mismatch between work arrival and worker throughput, isolate slow providers, and allow bounded worker concurrency. They do **not** make new hardware, throughput, provider quota, or fresh data appear. A growing queue increases data age; if freshness/latency is the priority, blindly draining an old backlog can be worse than dropping obsolete refresh work and returning a quick unavailable status.

Use queues with explicit per-provider rate limits, priority, maximum age, deduplication/coalescing, bounded retries with jitter, idempotent handlers, dead-letter inspection, and alerts on oldest-message age—not depth alone. Expire jobs that have missed their usefulness deadline. Keep messages small and avoid personal data; configure retention and access controls. Do not queue interactive reads, login, friend requests, saves, or checkout to make them appear accepted. Such operations either complete synchronously within their latency budget or fail quickly without ambiguous state. A self-operated RabbitMQ cluster adds patching, quorum/backup design, capacity, monitoring, and 24/7 failure modes; start with simpler durable scheduling if it satisfies delivery guarantees.

## GDPR and Europe/Middle East considerations

GDPR compliance is a product, legal, and operational obligation; architecture alone cannot certify compliance. Have qualified legal/DPO review determine lawful bases, notices/consent where applicable, DPIAs, processor agreements, international-transfer mechanisms, and retention exceptions.

- Minimize personal data and document purposes, lawful bases, retention periods, processing records, and data locations. Separate public catalog data from account and relationship data.
- Implement workflows for access/export, correction, erasure, restriction/objection where applicable, and consent withdrawal when consent is the lawful basis. Account deletion must cover saved items and social relationships and document treatment of logs, indexes, and backups, including their expiry schedules.
- Encrypt data in transit and at rest; restrict and audit privileged access; rotate credentials; redact email/tokens from logs; minimize personal data in events and provider payloads.
- Require authenticated, exact-match, rate-limited email lookup and minimize user details returned to reduce account enumeration.
- **Jurisdiction recommendation:** neither the OneSport requirements nor the repository establish where its controller is based, so no specific country can be responsibly recommended from the available information. Establish the controller where the responsible legal entity has its genuine establishment and central administration; have counsel determine the competent supervisory authority and any one-stop-shop applicability. Select an EU/EEA primary data location based on the actual operating entity, team-operated infrastructure/resilience, user needs, and legal review. Do not establish an entity in a country merely to seek a preferred regulator. A hosting location alone does not determine controller establishment or remove obligations where the service is offered.
- The audience being in the Middle East does not by itself require hosting there. Decide country by country whether local privacy, cybersecurity, or data-localization laws apply to the service, users, or data. Do not assume one Middle East rule applies to the whole region. A non-EEA hosting/DR location or support access can create transfer and local-law questions; obtain jurisdiction-specific counsel before enabling it.
- Avoid identifiable cross-region replication by default. Keep disaster-recovery copies in the approved region unless a documented transfer assessment approves another location. Include backups, monitoring/logging, support access, and provider subprocessors in the data-location map.
- Review providers and subprocessors for data-processing terms and transfer implications. Store only provider fields needed for the product and apply retention rules to imported payloads.

### Security and 24/7 operations

Full platform ownership means OneSport owns the security and availability response as well as the software. A queue, Kubernetes, or AI operations tool does not remove that responsibility. Before promising 24/7 availability, fund a real incident response capability, test runbooks, and define severity, escalation, recovery objectives, and customer communications.

Minimum security controls include asset/software inventory and patch SLAs; secure build/dependency scanning and signed/reproducible releases; MFA and least privilege for operators; segmented management, application, and data networks; short-lived, rotated secrets; encrypted transport/storage; audited privileged access; tested encrypted backups; central alerting and time-synchronized logs; rate limiting and DDoS/abuse planning with the network/hosting provider; and a rehearsed breach-response process. Use a self-operated secrets solution only if the team can patch and recover it; otherwise a tightly controlled encrypted deployment secret procedure is operationally simpler, though less feature-rich. Avoid putting credentials, emails, tokens, or sensitive payloads into logs or queue messages.

**Coverage choices and trade-offs:**

- **Internal 24/7 primary + secondary on-call:** strongest direct ownership and context, but expensive and fatiguing. One continuously staffed seat is 168 hours/week, or 4.2 people at a theoretical 40 hours each before leave, training, handoffs, and sustainable workload; a real rota needs additional coverage and a secondary responder. A small team should not promise this model without enough trained people, compensation, escalation cover, and a manageable page rate.
- **Business-hours human response with predefined 24/7 safeguards:** lower staffing cost. Automated health checks, bounded autoscaling within reserved capacity, circuit breakers, rate limits, fail-fast responses, queue expiry, and safe feature flags can preserve a degraded but predictable service overnight. The trade-off must be an explicit, honest availability/recovery target. Suspected personal-data breaches or active compromise need a defined after-hours escalation and prompt human assessment; do not assume they can wait until the next business day. Counsel/DPO should define applicable notification timelines and decision ownership.
- **Contracted human NOC/SOC or infrastructure support:** can extend alert triage and response, but does not transfer controller/operator accountability. With the no-managed-platform constraint, use contracts for human support only if they fit data-access, confidentiality, residency, and processor requirements. Keep clear escalation paths and least-privilege access.
- **AI-assisted operations:** AI can summarize sanitized alerts/logs, correlate known symptoms, draft incident timelines, retrieve approved runbooks, and recommend next steps. It should not be the only responder, make legal/security decisions, or receive unrestricted production credentials. Treat logs, tickets, and provider responses as untrusted input (prompt-injection/data-exfiltration risk). Default to read-only, scoped access; redact personal data/secrets; require human approval for production writes, failovers, data deletion, firewall changes, or security containment; log and review every action. Only deterministic, pre-authorized actions with bounded blast radius should be automated.
- **Predefined behavior before AI:** deterministic controls are more testable for predictable overload: shed low-priority features, cap connections/concurrency, pause provider polling at quota, reject requests quickly with retry guidance, open circuit breakers, and alert a human. AI may assist diagnosis but must not be a dependency in the request path or the sole mechanism preventing data loss/security incidents.

Recommendation: initially define a business-hours human support model plus 24/7 deterministic safeguards and alerting unless the business funds a sustainable internal or contracted human on-call rota. If availability/security objectives require immediate human action at all hours, establish that human coverage before launch; AI is an assistant, not a staffing substitute.

## Alternatives considered

### A. Three-tier monolithic application

One deployable application contains all modules and may run a worker from the same package.

- **Advantages:** lowest initial platform cost; straightforward local transactions, account deletion, debugging, and deployment.
- **Disadvantages:** API and ingestion workloads compete unless separately configured; broad scaling can waste capacity; feature boundaries can erode; one primary database can bottleneck all workloads.
- **Reason not selected as the target:** while a monolith can scale horizontally, the expected sharp waves make explicit API/worker isolation valuable. This remains a viable lower-cost first implementation if measured burst needs fit reserved capacity.

### B. Modular monolith with independently provisioned workload roles — selected

One modular codebase, separately sized stateless API and ingestion-worker pools, shared initial database, and optional self-operated cache/read replica.

- **Advantages:** directs warm capacity to the saturated workload; buffers provider work; preserves simple in-process calls and relational transactions; keeps GDPR deletion manageable; provides stable boundaries for later extraction.
- **Disadvantages:** shared deployment/version and database remain coupling points; API scaling can still expose a database bottleneck; warm headroom and self-operated infrastructure have fixed cost.
- **Why selected:** best balance of burst isolation, maintainability, technology supportability, platform ownership, and operational complexity while actual scale/team ownership needs remain unknown.

### C. Independently deployable domain services

Separate identity, catalog, library, and social services with independent data stores and communication through APIs/events.

- **Advantages:** strongest independent scaling, deployment, fault isolation, and per-service technology choice.
- **Disadvantages:** highest fixed platform/on-call burden; distributed transactions and eventual consistency; harder account deletion, regional governance, testing, and failure recovery.
- **Reason not selected now:** no evidence yet of independent teams, sustained scale, release cadence, or isolation needs that justify this cost. Reconsider only with measured pressure or clear ownership boundaries.

## Consequences

### Positive

- API and provider-ingestion bursts can be sized independently without immediately introducing a service mesh or distributed domain model.
- Provider quota/cost policy is explicit and replaceable per integration.
- In-process transactions simplify saved-item and friendship invariants and account-deletion completion.
- API/provider contracts and module boundaries retain technology interoperability and a path to extract a genuinely pressured read path.
- The architecture supports team-owned hosting and avoids serverless/managed dependencies.

### Negative and risks

- The team must operate and secure the entire platform, reserve spare capacity, test disaster recovery, and staff on-call. This may outweigh infrastructure savings compared with managed services.
- Queueing absorbs eligible asynchronous backlog but does not increase throughput; expired refresh jobs may be dropped, and functions may return unavailable or controlled throttling when the burst exceeds provisioned capacity or freshness budgets.
- PostgreSQL remains a shared critical dependency and may bottleneck API replicas and worker writes. Replicas and caches add replication lag, invalidation complexity, and more systems to operate.
- A shared codebase/release can still couple teams and deployments. Module boundaries need automated checks, ownership, and migration discipline.
- GDPR and regional transfer compliance depend on operational practices, contracts, and legal review as well as technical controls.

## Rollout and validation

1. Define numeric latency SLOs and per-catalog freshness limits, burst envelope, data residency/transfer requirements, provider terms and quotas, availability/recovery targets, and platform-team capacity.
2. Establish the team-operated Linux/container/ingress environment, PostgreSQL backup/restore, secrets handling, monitoring, and security patch process.
3. Implement modular API and worker roles with provider adapters, quota policy, idempotent refresh, privacy/retention workflows, and OpenAPI contracts.
4. Load-test average and burst traffic, queue backlog/recovery, cache behavior, DB connection budgets, and graceful degradation. Validate GDPR data-subject workflows including deletion from logs/backups under the approved retention policy.
5. Add cache, read replica, or coarse-grained catalog-read deployment only when metrics/load tests identify the relevant bottleneck. Revisit service decomposition only with evidence of a need.

## Open questions

- What numeric latency SLOs and maximum news/event/ticket data ages should apply, and what burst envelope and geographic distribution must be supported?
- Which news/ticket providers are commercially and technically viable, and what rate, cost, caching, and redistribution terms do they permit?
- Does OneSport handle only provider handoff, or must it own bookings, payments, refunds, and ticket fulfillment?
- What team size and operational expertise are available for Linux, Kubernetes, PostgreSQL, queueing, security, and 24/7 response?
- Confirm the controller's actual establishment and supervisory-authority analysis with counsel; which EU/EEA primary and recovery locations and Middle East transfer/local-law decisions apply?
- What availability, recovery-time, and recovery-point objectives are required?
