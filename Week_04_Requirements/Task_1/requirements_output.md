# Software Requirements Specification

## Executive summary

This document is the consolidated requirements deliverable for the PINES reporting, inventory, and administrative capabilities corpus provided. Requirements were semantically deduplicated, consolidated where explicit consensus existed in the source documents, and preserved as unresolved conflicts where the sources left a decision open. The consolidation preserved provenance for each requirement and the priority assignments follow the supplied priority scale (Critical / High / Medium / Low). Implementation notes: the requirements synthesis was prepared under an intended LangGraph processing pipeline (Python LangGraph) that would use at least three LLM-invoking nodes (e.g., gpt-4, gpt-4o, claude-v1 as examples), a deterministic non-AI node for matching/deduplication, and a feedback loop node for reconciliation of conflicting candidates; the architecture decision about which models or nodes to run in production remains an implementation choice and is not part of the requirements. This SRS intentionally does not invent additional stakeholder requirements; unresolved architectural and domain decisions are recorded in Unresolved Conflicts for follow-up prior to implementation.

## Priority scale

- **Critical:** Explicitly critical, legal/privacy-critical, or protects against severe or irreversible harm.
- **High:** Core or strongly emphasized capability with substantial operational impact.
- **Medium:** Useful, supported capability with routine impact.
- **Low:** Optional enhancement or weakly evidenced request.

Priorities reflect explicit source emphasis, consolidated decisions, and impact; frequency alone is not treated as approval.

## Requirements

### CON-001 — REQ-017 Operating Environment, Browser & Accessibility Requirements

**Type:** constraint  
**Category:** constraint  
**Priority:** Critical

The system shall operate on supported server platforms (Linux and Solaris were cited) and be accessible via web browsers. All web UI and report outputs shall use standards-compliant HTML and be accessible with assistive technologies (screen readers, magnification), meeting applicable accessibility guidelines (e.g., Section 508). The reporting system shall be designed so report processing does not degrade OPAC responsiveness. Note: the specific browser-version list in the sources reflects historical environments and must be finalized by implementers; do not hard-code legacy versions without verification.

**Sources:** `early_draft_srs_galecia.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

**Verification notes:** Verify server compatibility via deployment smoke tests on Linux and Solaris test servers. Verify HTML output against W3C validators and run accessibility checks and manual screen-reader walkthroughs. Confirm that a heavy-report job does not measurably degrade OPAC responsiveness during acceptance testing.

### CON-002 — REQ-021 Reporting Performance Isolation (protect OPAC and production)

**Type:** constraint  
**Category:** non-functional  
**Priority:** Critical

The system shall ensure heavy reporting workloads do not materially degrade OPAC or circulation client responsiveness. Mitigation strategies may include background job processing, queueing and prioritization, query optimization, and optional use of a read replica or reporting warehouse. The final architectural choice is unresolved in the sources and must be decided and recorded; until then, the system must include queueing and prioritization controls for long‑running reports.

**Sources:** `evergreen_reference_2009.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

**Verification notes:** Verify by running controlled load tests: start a long-running complex report and confirm the OPAC response time meets SLA thresholds during the test. Demonstrate queueing/prioritization behavior for multiple concurrent report jobs. Provide architecture decision and subsequent verification steps if a replica/warehouse is chosen.

### CON-003 — REQ-031 Accessibility & Standards-Compliant HTML Output

**Type:** constraint  
**Category:** non-functional  
**Priority:** Critical

All web-based components, the online help system, and report HTML output must be implemented using standards-compliant HTML (W3C) with accessibility-oriented markup (semantic HTML, ARIA roles, alt text) and must be operable with screen-reading software and screen magnification to meet applicable accessibility regulations.

**Sources:** `early_draft_srs_galecia.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

**Verification notes:** Verify via W3C validation and accessibility testing with automated tools and manual screen-reader review of representative UI flows and exported HTML reports. Confirm remediation of any blocking accessibility defects.

### FR-001 — REQ-008 Deletion Tracking & Audit Log

**Type:** functional  
**Category:** administrative  
**Priority:** Critical

The system shall log deletions of core records (item, bibliographic, patron, and other relevant record types) to an immutable deletion audit table that records: record_type, record_id, a small record summary (identifying fields), deleted_by (user id), deleted_at (timestamp), and user location (branch). The system shall optionally log denied deletion attempts and shall provide reporting interfaces to aggregate deletions and denied attempts by period, type, user, and location for auditing and compliance.

**Sources:** `conversations/conv_pines022_deletions.eml`, `early_draft_srs_galecia.txt`

**Verification notes:** Verify by deleting a test item/patron/bib record and confirming an immutable audit entry exists with required fields. Test a forbidden deletion and confirm an optional denied-attempt log entry is recorded when this option is enabled. Run an aggregate deletion report for a sample period.

### FR-002 — REQ-018 Staff Login Methods and Role-Based Access Control

**Type:** functional  
**Category:** administrative  
**Priority:** High

The system shall support streamlined staff login methods (optional card-swipe or similar) plus traditional username/password fallback. The authentication mechanism must reliably identify the individual staff member for auditing (card-swipe may be permitted for convenience but must map to an individual account). User rights and privileges shall be controlled through role-based security groups that are easy to administer and support assignment at individual, workgroup, and branch levels.

**Sources:** `early_draft_srs_galecia.txt`, `email_staff_login.eml`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

**Verification notes:** Verify by demonstrating: (a) card-swipe login mapped to a user account (with audit trail); (b) username/password fallback; (c) role change for a user propagates permission changes; (d) admin UI for role/group management is usable for adding/removing roles.

### FR-003 — REQ-011 Financial Reporting & Audit Trail

**Type:** functional  
**Category:** financial  
**Priority:** Critical

The system shall provide financial reports including: value of items aggregated by selection (based on item purchase_price or equivalent field) for entire collection or subsets; patron account balances and transaction detail by patron, home library, and system; fines and charges accrued per configurable time periods and by type; fines waived per time period and per branch; and payments by period and payment method (staff desk, self-check, OPAC). The system shall maintain a financial audit trail (ledger) recording payments, waivers, and which charges payments were applied to, to support reconciliation and compliance.

**Sources:** `early_draft_srs_galecia.txt`, `email_financial_reports.eml`

**Verification notes:** Verify by producing: (1) value-of-items report for a filter (e.g., DVDs in children's) and confirming aggregation from item purchase_price fields; (2) account balance and payment-applied reporting for sample patrons; (3) waivers and payments reporting per branch; (4) ledger entries show which charges payments were applied to. Confirm retention configuration is supported for audit requirements.

### FR-004 — REQ-001 Material Volume Report (historical & categorical)

**Type:** functional  
**Category:** inventory  
**Priority:** Critical

The system shall provide a Material Volume Report that produces volume counts for a selected library or the system at a specified point in time (snapshot or historical date range) and for current state. The report shall break down volumes into configurable categories (examples: new acquisitions, on‑shelf/checked‑in, checked‑out/circulation, holds, collection subcategories such as adult fiction or board books), support per‑library and per‑system aggregation, allow filtering by date range or snapshot timestamp, and support export to CSV and Excel formats. Where stakeholders did not provide an exclusive definition of 'volume' (e.g., whether to exclude certain statuses), the report shall surface its selection criteria and category definitions in the report header.

**Sources:** `conversations/conv_pines014_material_volume.eml`, `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`

**Verification notes:** Verify by producing: (1) a current-state run for a sample branch showing category totals; (2) a historical snapshot (point-in-time) for a given date and branch; (3) exported CSV/XLSX includes the report name and exact selection criteria (date/snapshot and category definitions). Confirm categories can be customized and that the report header records which category definitions (and status filters) were applied.

### FR-005 — REQ-002 System Capacity Interface (overview, filter, drill-down)

**Type:** functional  
**Category:** inventory  
**Priority:** High

The system shall provide a Capacity Interface that presents a high-level overview of capacity metrics across branches (system view) with interactive filtering/grouping (example groupings: region, library type) and the ability to drill down to individual branch detail views. The interface shall support sorting, CSV export of displayed rows, and display trend indicators (growth/shrink) over selectable time ranges. The interface must scale to large numbers of locations by supporting grouping, pagination, or dynamic filtering to avoid overcrowding.

**Sources:** `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`

**Verification notes:** Verify by demonstrating: (a) system-level overview with >100 shown locations using grouping and filtering; (b) drill-down to a single branch detail; (c) sorting and CSV export of the current view; (d) trend visualization for selected branch over at least two time intervals. Note: the exact metric(s) shown as 'capacity' (shelf space, configured item limits, processing load, etc.) are unresolved — see Unresolved Conflicts; the interface must allow selecting/labeling which capacity metric is displayed.

### FR-006 — REQ-003 Shelf Space Utilization Report (genre/format comparison)

**Type:** functional  
**Category:** inventory  
**Priority:** High

The system shall provide a Shelf Space Utilization Report that, for each genre and format and for a selected library or the system, reports (a) percentage of total circulations, (b) percentage of the collection (item count), and (c) percentage of total shelf space occupied. The report shall support date-range filtering, per-library and system aggregation, and export to CSV/Excel. Because shelf space is not universally recorded, the report shall support configurable estimation methods (for example item-dimensions based calculation or an item-count proxy) and must document which estimation method was used in the report header.

**Sources:** `conversations/conv_pines016_shelf_space.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

**Verification notes:** Verify by running the report with each supported estimation method on a sample dataset where expected percentages are precomputed. The exported output must include the estimation method and its parameters. If dimension fields are missing for some items, confirm documented fallback behavior (e.g., apply proxy).

### FR-007 — REQ-004 Item Transfer Utility (batch transfers, revert, audit)

**Type:** functional  
**Category:** inventory  
**Priority:** Critical

The system shall provide an Item Transfer Utility enabling batch movement of items between locations (branches, mobile units, events, temporary warehouses). Features shall include: a query builder for selecting candidate items; ability to save and share queries; manual selection from query results; preview/confirmation before applying batch updates; chunked batch processing to avoid database locking; generation of pull/transit lists and printable transit labels; comprehensive audit logging (who/when/old-location/new-location/transaction id); undo/rollback where feasible; role‑based permission controls for transfer execution; and configurable auto‑reversion options (time‑based and/or event‑based) with stored revert metadata. Because event-based revert semantics were requested but underspecified, the system must treat precise event triggers and precedence as an implementation decision documented prior to use.

**Sources:** `conversations/conv_pines018_item_transfer.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

**Verification notes:** Verify by: (1) creating and saving a query and reusing it; (2) selecting a 10K-item batch and executing a chunked transfer; (3) generating pull lists and transit labels; (4) demonstrating preview and cancellation of a pending transfer; (5) showing audit records for the transfer and ability to undo a recent transfer when allowed. Validate auto-revert with at least one time-based test case; event-driven revert test cases must be specified and validated after finalizing the event triggers (see Unresolved Conflicts).

### FR-008 — REQ-005 Missing and Damaged Items Report

**Type:** functional  
**Category:** inventory  
**Priority:** High

The system shall provide Missing and Damaged Items Reports that list items flagged missing or damaged, filterable by branch and configurable date ranges, include available condition notes, and export to CSV/Excel for inventory audits and trend analysis.

**Sources:** `conversations/conv_pines019_020_missing_intransit.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

**Verification notes:** Verify by running the report for a branch over a 90-day range and confirm exported file includes item id, title, current status (missing/damaged), condition notes, and branch filter metadata. Run a trend query grouping by month to confirm date-range aggregation.

### FR-009 — REQ-006 In-Transit Items Report (aging, merged view)

**Type:** functional  
**Category:** inventory  
**Priority:** High

The system shall provide an In-Transit Items Report that lists items currently in transit whose elapsed time since departure exceeds a configurable threshold X days (X configurable, default suggested e.g., 7). The report shall merge 'transit-to' and 'transit-from' perspectives into a single view, be filterable by branch and system, sortable by oldest departure/expected arrival, and include transit metadata (departure date, expected arrival, sending and receiving locations).

**Sources:** `conversations/conv_pines019_020_missing_intransit.eml`, `early_draft_srs_galecia.txt`

**Verification notes:** Verify by selecting threshold X = 7 and listing all items with departure date older than X, confirming merged view includes both transit-to and transit-from entries, and that sorting by departure date places oldest first. Confirm CSV export contains transit metadata fields.

### FR-010 — REQ-007 Item Record Purging & Last-Copy Protection

**Type:** functional  
**Category:** inventory  
**Priority:** Critical

The system shall provide a Weeding/Purging utility to identify candidate item records for purge using customizable criteria (status/time/activity combinations), produce read-only candidate reports, support complex boolean criteria and saved filter sets, enable batch status conversions (e.g., missing -> discard/weed), provide a 'last copy' report that flags whether a candidate is the last copy within a scoped selection (per-branch and per-system), require an explicit separate confirmation step before deletions, maintain a purge audit trail (who/when/why), and offer scheduling/background execution for long-running cleanup tasks.

**Sources:** `conversations/conv_pines021_item_purging.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

**Verification notes:** Verify by producing: (1) a candidate report using combined criteria (e.g., status = missing AND last_circulated > 2 years); (2) a last-copy check for a sample bibliographic record showing per-branch and system scopes; (3) that deletion is blocked until a separate confirmation step is executed; (4) that a purge audit entry is created for each deletion.

### FR-011 — REQ-023 Uncataloged Material Inventory Control

**Type:** functional  
**Category:** inventory  
**Priority:** Medium

The system shall support lightweight inventory control for uncataloged material (e.g., paperbacks, board books) with quick distribution workflows minimizing branch labor, ability to record transactions for uncataloged items and include them in circulation statistics and reports, and mechanisms to differentiate uncataloged tracking from fully cataloged item records.

**Sources:** `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

**Verification notes:** Verify by creating uncataloged item records using the lightweight flow, performing circulation transactions, and ensuring counts appear in aggregate circulation reports. Confirm that uncataloged items are clearly distinguishable in exports and UI.

### FR-012 — REQ-025 Shelf Space Side-by-Side Comparison (optional UX enhancement)

**Type:** functional  
**Category:** inventory  
**Priority:** Low

The system may provide an optional side-by-side comparison view within the shelf space reporting feature showing each selected library’s breakdown in adjacent columns to highlight outliers. This view is a low-priority UX enhancement requested by staff.

**Sources:** `conversations/conv_pines016_shelf_space.eml`

**Verification notes:** If implemented, verify by selecting multiple libraries and rendering a side-by-side CSV/XLSX where each library is a column and genres/formats are rows; confirm outlier detection is visually apparent and that export preserves the layout.

### FR-013 — REQ-026 Item Transfer Delay Alerts (optional)

**Type:** functional  
**Category:** inventory  
**Priority:** Low

The system may provide optional alerts or notifications when item transfers are delayed beyond expected arrival windows or encounter other issues. This is a lower-confidence request and may be prioritized as an enhancement.

**Sources:** `conversations/conv_pines018_item_transfer.eml`

**Verification notes:** If enabled, verify by creating a transfer with an expected arrival and simulating a delay; confirm alert(s) are sent to configured recipients and logged in the transfer history.

### FR-014 — REQ-009 Patron Characteristics Reporting (filters & grouping)

**Type:** functional  
**Category:** patron  
**Priority:** High

The system shall support queries and reports that filter, limit, and group patrons by configurable characteristics including age range (computed from birthdate with configurable brackets), ZIP code, county of residence, home branch, patron type (adult/juvenile/etc.), and preferred language. Reports shall support combining filters with Boolean logic, include explicit null values in results (not silently excluded), allow aggregations (GROUP BY), and support export for downstream program planning.

**Sources:** `conversations/conv_pines023_patron_characteristics.eml`, `early_draft_srs_galecia.txt`, `survey_results_2009.txt`

**Verification notes:** Verify by generating grouped reports using configurable age brackets and by ZIP code; confirm null field rows are present (with an explicit null marker) and that exports include nulls. Confirm ability to combine filters with AND/OR logic.

### FR-015 — REQ-010 Inactive Patrons Report (configurable activity definition)

**Type:** functional  
**Category:** patron  
**Priority:** High

The system shall generate an Inactive Patrons Report listing patrons with no circulation or recorded electronic activity within the last X days (X configurable). 'Electronic activity' shall include OPAC login, online hold placement, online renewals, and other logged digital access where available. The report shall be runnable at multiple scopes (system, home library, county), include current mailing addresses for outreach, allow exclusion of specified patron classes (e.g., staff, VIPs, opt-outs), be exportable (CSV/Excel), and support background processing or caching for performance.

**Sources:** `conversations/conv_pines024_inactive_patrons.eml`, `early_draft_srs_galecia.txt`

**Verification notes:** Verify with tests: (1) X days configurable (e.g., 180 days) and output matches expected patrons given known circulation and OPAC logs; (2) exclusions for staff/VIP work; (3) exports include mailing addresses and scope metadata. Note: availability of certain digital activity logs (third-party integrations) must be documented — missing logs should be treated as 'no recorded electronic activity' and noted in report metadata.

### FR-016 — REQ-012 Report Query Tool (fields, picklists, regex, boolean)

**Type:** functional  
**Category:** reporting  
**Priority:** Critical

The system shall provide an interactive Query Tool for constructing reports across bibliographic, item, patron, transaction, and financial data. The tool shall allow selection of fields, picklist-value selection, regular expression support (from a configurable list), Boolean operators (AND/OR/NOT), inclusion of uploaded filters (e.g., lists of barcodes/IDs), and shall display the selection criteria alongside results for auditability. Administrators shall be able to control access to underlying tables/fields.

**Sources:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `evergreen_reference_2009.txt`

**Verification notes:** Verify by building queries that use picklists, regex, boolean logic and uploaded barcode lists; confirm that the result view shows the query criteria and that field-level access control prevents forbidden fields from appearing to unauthorized users.

### FR-017 — REQ-013 Report Templates, Cloning, and Permissions

**Type:** functional  
**Category:** reporting  
**Priority:** Critical

The system shall support administrator-managed Report Templates that can be run as-is or cloned and modified by permitted users. Administrators shall be able to restrict which filters and display fields are editable by staff, organize templates in shared folders, and assign fine-grained permissions (create, clone, run, modify, schedule) to roles or individual users to produce consistent certified outputs for governance needs.

**Sources:** `early_draft_srs_galecia.txt`, `email_report_features.eml`

**Verification notes:** Verify by creating templates in an Admin role, restricting editable filters, attempting to run and modify as a lower-privilege role (should be prevented where restricted), cloning templates and confirming cloned template is independent of original, and placing templates into shared folders. A permission matrix is required before implementation (see Unresolved Feedback).

### FR-018 — REQ-014 Report Queueing, Scheduling, Prioritization, and Delivery

**Type:** functional  
**Category:** reporting  
**Priority:** High

The system shall provide a Report Queue showing submitted reports with status (queued, running, completed, failed), queue position or estimated wait, submission time, and the ability to cancel scheduled or running reports. Scheduling options shall include ASAP, hourly, daily, weekly, monthly, and yearly recurrence. The system shall support prioritization (ability to elevate urgent reports) and delivery options including UI download and optional email delivery (with address book support).

**Sources:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `survey_results_2009.txt`

**Verification notes:** Verify by submitting multiple reports to produce a queue, confirm status updates, cancel a queued job, schedule recurring reports, elevate priority for a configured role and demonstrate priority behavior. Confirm email delivery by sending a sample completed report to address-book entries.

### FR-019 — REQ-022 Transaction & Event Counts (check-in/out/holds breakdowns)

**Type:** functional  
**Category:** transaction  
**Priority:** High

The system shall capture and report transaction counts broken down by types and modifiers: check-in types (book-drop, by terminal, by user, self-service), check-out types (staff checkout, self-checkout, staff renewal, self-checkout renewal, online/OPAC renewal), and holds including method of placement (staff desk, public in-library computer, remote/online). These breakdowns shall be available for grouping by hour, terminal, branch, and system.

**Sources:** `early_draft_srs_galecia.txt`, `survey_results_2009.txt`

**Verification notes:** Verify by generating transaction reports that enumerate counts by type and modifier, grouped by hour and terminal, and by branch. Confirm that holds metadata shows method-of-placement for sample hold events.

### NFR-001 — REQ-019 Data Specifications, Online Help & Error Feedback

**Type:** non-functional  
**Category:** administrative  
**Priority:** High

The developer shall provide complete data specifications (data dictionary) for authority, bibliographic, order, item, hold/request, patron, transaction, and financial records; deliver a searchable, hierarchical, cross-linked online help system in HTML; provide high-level process documentation for key workflows (imports/exports, validation, standard reports); and surface meaningful, query-specific error and troubleshooting feedback in the front-end to assist administrators.

**Sources:** `early_draft_srs_galecia.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

**Verification notes:** Verify the presence and searchability of the data dictionary, confirm help pages exist for major workflows, and validate that error messages link to relevant help topics. Confirm that data field definitions (names/types) are sufficient to construct queries and mappings.

### NFR-002 — REQ-015 Output Formats, Pivot & Null Inclusion

**Type:** non-functional  
**Category:** reporting  
**Priority:** High

Report output shall be available in standard machine-readable and user formats including CSV, Excel (XLS/XLSX), and HTML. The system shall produce pivot-friendly output formats where required, ensure all null/blank fields are explicitly represented in results (not silently omitted), and include the selection criteria and date range and report name in the output header for traceability.

**Sources:** `early_draft_srs_galecia.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

**Verification notes:** Verify by exporting sample reports to CSV and XLSX and confirm: (a) null fields are present as explicit empty cells or 'NULL' markers; (b) header rows include report name and selection criteria; (c) Excel file loads into pivot tools with expected column types.

### NFR-003 — REQ-016 Transaction History Retention and Historical Reporting (architectural dependency)

**Type:** non-functional  
**Category:** transaction  
**Priority:** High

The system shall maintain transaction history according to configurable retention settings: detailed transaction history retained for X days (configurable), while monthly and annual aggregates are retained indefinitely. The system shall support historical reporting (snapshots) that can reproduce aggregates for a specified date range. To protect production responsiveness, the architecture must provide either reporting-optimized background processing or a reporting replica/warehouse; the final architecture choice (background-only vs read-replica vs reporting warehouse) is unresolved in the source corpus and must be decided and recorded prior to implementation.

**Sources:** `early_draft_srs_galecia.txt`, `evergreen_reference_2009.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

**Verification notes:** Verify configurable retention by setting X to a test value and confirming older detailed transactions are removed while aggregates remain. Because architecture is unresolved, acceptance requires an architecture decision record (replica vs warehouse vs background processing) and, after that decision, demonstration that historical snapshots reproduce past-period aggregates to within documented tolerances.

## Discarded requirements

- **Discarded: Mandated Denormalized Live Reporting Schema:** A candidate requirement that the system must implement a denormalized, write-through reporting schema (live denormalization) was considered but rejected in this SRS. The technical subcommittee and referenced materials recommend against mandating denormalization due to synchronization, maintenance, and operational complexity. Instead, the SRS records the need for reporting performance and historical snapshots and leaves the architectural approach (background processing, read-replica, reporting warehouse) as an unresolved implementation decision.
  Sources: `evergreen_reference_2009.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

## Unresolved conflicts

- Architectural approach for historical reporting is unresolved: sources request historical snapshots and reporting isolation but the technical subcommittee cautioned against denormalized live schemas. Decision required: choose between background processing on production DB with caching, read-only replica, or dedicated reporting warehouse. This decision affects REQ-016 and REQ-021 and must be recorded in an Architecture Decision Record before implementation.
- Shelf-space measurement method unresolved: stakeholders require percentage of total shelf space per genre/format (REQ-003) but the database does not store shelf-space. Implementers must choose or provide configurable estimation methods (item dimensions vs item-count proxy vs manual linear-feet per shelving location) and document the chosen method and acceptance tests prior to release.
- Event-based auto-reversion semantics unresolved for item transfers (REQ-004): stakeholders requested time-based and event-based reversion (e.g., revert when not checked out at destination) but the exact event triggers, precedence rules (e.g., checkout cancels revert), and edge-case behavior were not specified. The implementer must define precise triggers, conflict resolution, and test cases before enabling automatic reversion.
- Browser-version specifics are a soft conflict: source documents reference legacy browsers (IE 6.0 / Firefox 2.0). Implementers must finalize supported browser versions in an environment/compatibility policy and avoid hard-coding historically-cited versions in the SRS.
- Capacity metric definition unresolved: the notion of 'capacity' for the Capacity Interface (REQ-002) is underspecified. Stakeholders referenced different metrics (shelf-space, configured item limits, processing/circulation load). The system must either support multiple selectable metrics or the owners must decide the authoritative definition.
- Unresolved review issue: {"candidate_ids": ["functional-0001"], "instruction": "Consolidate the material-volume statements into one testable requirement artifact. functional-0001 presently documents a consolidation action but is flagged as paragraph-length and may not be testable. Revise functional-0001 to (a) present a single canonical requirement statement (one-line), (b) add explicit acceptance criteria (e.g., inputs, filters, outputs, expected aggregates), (c) list exact source documents and quotations that justify each sub-element, and (d) remove or link any sibling candidate entries (stakeholder-0025, technical-0034) to this canonical ID. If there truly are distinct variants (for example, point-in-time vs. current-only semantics), enumerate them as named options with explicit selection rules rather than leaving variants scattered across candidates.", "issue_type": "duplicate", "severity": "Medium", "target_agents": ["functional", "technical"]}
- Unresolved review issue: {"candidate_ids": ["functional-0002"], "instruction": "The 'capacity' concept in functional-0002 is underspecified. Update functional-0002 to (1) enumerate the specific metrics that may be considered as 'capacity' (e.g., physical shelf space [linear feet], configured item limits, percent-filled by shelving location, current item count vs configured capacity, processing/circulation load metrics), (2) indicate which metrics are REQUIRED vs OPTIONAL, (3) state whether metrics are configurable per system or per-branch, and (4) include measurable acceptance criteria (example queries, expected columns, and sample outputs). If stakeholders did not agree which metric(s) to use, mark this as an unresolved decision in the requirement header and list the options explicitly for an architectural decision.", "issue_type": "incomplete", "severity": "High", "target_agents": ["functional", "technical"]}
- Unresolved review issue: {"candidate_ids": ["functional-0003"], "instruction": "functional-0003 (Shelf Space Utilization Report) depends on an estimation method for 'shelf space' that is not specified. Provide concrete, testable options and map them to available data: (a) declare required item fields (height/width/depth) if using item-dimension estimation and indicate fallback behavior when missing; (b) specify the proxy method (e.g., items-per-linear-foot by format) with the formula and default parameters; (c) include example SQL or pseudo‑queries that implement the chosen method and at least one verification test case (input dataset → expected % values). If multiple estimation methods are acceptable, the requirement must require the report to support selecting the method and documenting which method produced the result.", "issue_type": "missing_evidence", "severity": "High", "target_agents": ["functional", "technical"]}
- Unresolved review issue: {"candidate_ids": ["functional-0016"], "instruction": "functional-0016 surfaces an unresolved architectural conflict: how to provide historical reporting and heavy analytics without impacting production (background processing, reporting replica/warehouse, or live queries). The technical team owning functional-0016 must (a) produce a short options analysis (cost/perf/ops/security/consistency tradeoffs) that compares at minimum: background job queueing on production vs read-replica vs ETL into a reporting warehouse, (b) recommend a preferred architecture for PINES-scale loads with concrete operational constraints (e.g., replication lag SLA, retention policy, expected query concurrency), and (c) produce acceptance criteria for protecting OPAC responsiveness (e.g., max allowed query CPU/IO during business hours, or required use of replica for queries above X seconds). If a final decision cannot be made in this revision, mark the architectural choice as unresolved and attach the options analysis so that downstream implementers/testers have clear evaluation criteria.", "issue_type": "conflict", "severity": "Critical", "target_agents": ["functional", "technical"]}
- Unresolved review issue: {"candidate_ids": ["functional-0004"], "instruction": "functional-0004 (Item Transfer Utility) leaves event-based auto-revert behavior underspecified. Update this candidate to specify: (1) the complete list of supported revert triggers (time-based X days, item status change, checkout at destination, manual override), (2) precedence and conflict rules (e.g., if checkout occurs before scheduled revert, cancel revert), (3) how revert metadata is stored (original_location, transfer_timestamp, revert_policy), (4) expected behavior for partially-processed batches and error conditions, and (5) a set of concrete test cases that demonstrate acceptable behavior (e.g., schedule transfer with 30-day revert, item checked out at day 10 → no revert; item not checked out → revert at day 30). Ensure that permission and audit trails for auto-reverts are also specified.", "issue_type": "incomplete", "severity": "High", "target_agents": ["functional", "technical"]}
- Unresolved review issue: {"candidate_ids": ["technical-0039"], "instruction": "technical-0039 (side-by-side comparison view for shelf space) has low evidence and low confidence. Either (a) integrate this view explicitly into the main shelf-space requirement (functional-0003) with acceptance criteria and a sample UI/output, or (b) remove it as a separate requirement. Revise the candidate to state whether the side-by-side comparison is a mandatory deliverable or an optional UX enhancement, and provide at least one concrete example (CSV or mockup) showing the expected comparison output.", "issue_type": "unsupported", "severity": "Low", "target_agents": ["technical", "functional"]}
- Unresolved review issue: {"candidate_ids": ["functional-0010"], "instruction": "functional-0010 (Inactive Patrons Report) references 'electronic activity' and 'digital resource access' but does not specify required log sources and availability. Update the requirement to enumerate which electronic activity events are in scope (OPAC login, online holds, online renewals, third-party digital resource access such as OverDrive) and identify the required data tables/timestamps for each. If some integrations do not provide logs, the requirement must state expected behavior (e.g., treat missing logs as 'no recorded electronic activity' and note that results may undercount electronic-only interactions). Provide at least one acceptance test that combines OPAC login and hold-placement events.", "issue_type": "missing_evidence", "severity": "Medium", "target_agents": ["functional", "technical"]}
- Unresolved review issue: {"candidate_ids": ["functional-0013"], "instruction": "functional-0013 (Report Templates & Permissions) requires a concrete permission matrix. Produce a mapping table that defines roles (e.g., Staff, Local Admin, Library Manager, Global Admin) and the allowed operations (create template, clone template, modify template, run template, edit filters, schedule reports, set priority, export results). Include example default role assignments and note which actions require audit logging. Attach this matrix to functional-0013 and reference it from related candidates (e.g., functional-0014 queue priorities, functional-0004 transfer permissions).", "issue_type": "incomplete", "severity": "Medium", "target_agents": ["functional", "technical", "stakeholder"]}
- Unresolved review issue: {"candidate_ids": ["functional-0024"], "instruction": "functional-0024 documents that a denormalized live reporting schema candidate has been discarded. Treat this as a recorded design decision candidate: move the text from the functional candidates list into a short 'architectural decisions' artifact and ensure it lists the rationale and alternatives considered (why denormalization was rejected, and the mitigations to be used instead). Link this decision explicitly to functional-0016 (historical reporting) so implementers understand the rationale and the accepted approaches.", "issue_type": "other", "severity": "Medium", "target_agents": ["functional", "technical"]}

## Assumptions and dependencies

- Duplicate and semantically equivalent candidate statements about the material volume report were consolidated into REQ-001; the consolidation preserved explicit requested subfeatures (customizable categories, per-branch/system aggregation, export formats) and recorded consolidation metadata in this SRS rather than keeping near-identical variants as separate requirements.
- Where source documents requested functionality that depends on external integrations or non-uniform data capture (for example, logging of third-party digital resource access or item dimension fields), the SRS assumes those integrations may not always provide data. Requirements that depend on such data require implementers to document available data sources and fallback behaviors.
- The SRS does not mandate particular architectural solutions (replication, ETL, or denormalized stores); architectural choices that materially affect functional behavior (historical snapshots, large-scale analytics) are recorded as unresolved conflicts and must be decided and captured in a separate Architecture Decision Record prior to implementation.

## Source-document coverage

- `conversations/conv_pines014_material_volume.eml` — **requirements**: Primary source for Material Volume Report requests (counts by acquisitions, on-shelf, checked-out; customizable categories). Contributed directly to REQ-001 and REQ-003 category customization items.
- `conversations/conv_pines015_capacity_interface.eml` — **requirements**: Primary source for the System Capacity Interface and related UI/scale concerns. Contributed to REQ-002 and to unresolved 'capacity metric' decision.
- `conversations/conv_pines016_shelf_space.eml` — **requirements**: Primary source for shelf space utilization reporting, estimation concerns, and the optional side-by-side comparison request. Contributed to REQ-003 and REQ-025.
- `conversations/conv_pines018_item_transfer.eml` — **requirements**: Primary source for item transfer utility features: query builder, save queries, batch transfers, revert behavior, audit, preview, and permissions. Contributed to REQ-004 and REQ-026.
- `conversations/conv_pines019_020_missing_intransit.eml` — **requirements**: Provided requirements for Missing/Damaged and In-Transit reporting (REQ-005 and REQ-006), including merging transit-to/from and configurable thresholds.
- `conversations/conv_pines021_item_purging.eml` — **requirements**: Primary source for item purging and last-copy protection requirements (REQ-007). Also provided purge-safety expectations (read-only candidates, confirmation, audit trail).
- `conversations/conv_pines022_deletions.eml` — **requirements**: Primary source for deletion-tracking and audit log fields; contributed to REQ-008 and the optional denied-attempt logging capability.
- `conversations/conv_pines023_patron_characteristics.eml` — **requirements**: Primary source for patron demographic query/report requirements (REQ-009), including configurable age brackets and null-handling.
- `conversations/conv_pines024_inactive_patrons.eml` — **requirements**: Primary source for Inactive Patrons reporting (REQ-010) including scope and required electronic activity types; contributed to the note about variable availability of digital access logs.
- `early_draft_srs_galecia.txt` — **requirements**: Central draft SRS that provided structured candidate requirements across reporting, purging, transactions, security, and operating environment. Contributed substantively across many REQs (multiple references).
- `email_financial_reports.eml` — **requirements**: Primary source for financial reporting and audit-trail requirements (REQ-011, REQ-075 mapping). Provided retention and compliance expectations.
- `email_report_features.eml` — **requirements**: Provided detailed query tool and report-template/queueing requirements (REQ-012, REQ-013, REQ-014) and influenced REQ-016 and REQ-021 through performance concerns.
- `email_staff_login.eml` — **requirements**: Provided staff login and authentication convenience vs. auditability tradeoffs, and contributed to REQ-018.
- `evergreen_reference_2009.txt` — **context-only**: Provided context about limitations of existing systems and operational lessons (e.g., lack of reporting replica). Influenced unresolved architectural conflicts but did not define new functional requirements.
- `interview_cataloging_2009-05-08.txt` — **requirements**: Cataloging team input used for uncataloged-material handling, transfer utilities, purging expectations, and shelf-space estimation context; contributed to REQ-023, REQ-004, REQ-007, REQ-003.
- `interview_sysadmin_2009-05-10.txt` — **requirements**: System/ops constraints and server-platform expectations came from this interview; contributed to REQ-017 and REQ-021 (performance isolation).
- `meeting_minutes/meeting_2009-03-15_minutes.txt` — **noise**: This meeting minutes file contained no substantive requirements or unique recommendations referenced by candidates; treated as noise for this SRS consolidation.
- `meeting_minutes/meeting_2009-07-20_minutes.txt` — **requirements**: Provided operating environment, browser compatibility, and accessibility expectations feeding REQ-017 and REQ-031.
- `meeting_tech_subcommittee_2009-06-30.txt` — **conflict**: Provided technical subcommittee recommendations and warnings (notably against denormalization) that conflict with some desires for live historical reporting. Influenced the decision to leave architectural choices unresolved (affects REQ-016 and the discarded denormalized candidate).
- `survey_results_2009.txt` — **context-only**: Survey results provided prioritization signals (e.g., queue visibility, null inclusion) that influenced priorities and non-functional details across the SRS but did not introduce new functional items.
