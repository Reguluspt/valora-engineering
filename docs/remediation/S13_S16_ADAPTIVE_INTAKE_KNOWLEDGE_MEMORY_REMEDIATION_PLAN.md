# S13–S16 Adaptive Intake, Knowledge Memory and Historical Dossier Remediation Plan

**Status:** Active implementation plan after S12-PR-004 engineering closure; runtime tasks remain individually gated.
**Design authority:** Design Book v1.4 adaptive-intake addendum + ADR 0030–0032 + Design Authority Index.
**S12-PR-004 engineering baseline (evidence, not evergreen):** main squash `a9f2c1e77e3ec46f216b881d608a02685b9d322a`; post-merge main CI `29419008129` PASS.
**Gate 0 (S12 engineering closure):** **satisfied**.
**Active gate:** **S13-PR-001** docs-only design reconciliation until independent design audit PASS and owner merge.
**Rule:** Do not start S13-PR-002 runtime until S13-PR-001 is audited and merged. Branch runtime from the accepted main baseline only.

---

## 1. Goal

Close the verified gaps that prevent Valora from:

- reading real customer `.xls`/`.xlsx` workbooks with variable structures;
- asking non-IT users to confirm ambiguous columns;
- remembering confirmed column mappings by customer/template;
- preserving and matching customer raw asset wording;
- ingesting historical Excel–Word dossiers as supervised knowledge sources;
- extracting and aligning technical, quote and final-result tables;
- learning safely from human decisions;
- running audited AI column/identity suggestions end to end.

The target remains human-controlled. No task below authorizes AI auto-approval, AI auto-Apply or direct active-knowledge injection.

---

## 2. Verified gap register

| ID | Current gap | Current evidence | Target owner |
| --- | --- | --- | --- |
| G-01 | Parser accepts `.xlsx` only | `excel_import/domain/ACCEPTED_EXTENSIONS` | Sprint 13 workbook adapter |
| G-02 | First non-empty row becomes header | `_LazyWorkbook._find_headers()` | Sprint 13 structure discovery |
| G-03 | Fixed aliases miss real headers/blank I | `COLUMN_ALIASES`, `_map_columns()` | Sprint 13 Column Mapping Memory |
| G-04 | No section/subtotal/total classification | parser emits each non-empty row | Sprint 13 row classifier |
| G-05 | No mapping-confirmation screen | no adaptive mapping UI/API | Sprint 13 UX |
| G-06 | No `ColumnMappingProfile` | no persistence/API | Sprint 13 memory persistence |
| G-07 | No Excel–Word dossier aggregate | no DossierBundle | Sprint 15 dossier aggregate |
| G-08 | No multi-table row alignment | no alignment model/service | Sprint 15 alignment |
| G-09 | No real Word extraction runtime | generic models/CRUD only | Sprint 15 Document Intelligence runtime |
| G-10 | No feedback contract | no confirmed-decision learning events | Sprint 14 feedback |
| G-11 | No end-to-end AI column/asset matcher | AI module boundary only | Sprint 16 AI Gateway/tasks |

---

## 3. Global gates and ordering

```mermaid
flowchart TD
    A["Close S12-PR-004"] --> B["Sprint 13: Column Mapping Memory"]
    B --> C["Sprint 14: Asset Identity Memory"]
    C --> D["Sprint 15: Paired Dossier Bootstrap"]
    D --> E["Sprint 16: Audited AI Runtime"]
```

### Gate 0 — S12 engineering closure (satisfied)

Evidence:

- S12-PR-004 squash-merged to `main` at `a9f2c1e77e3ec46f216b881d608a02685b9d322a` (PR #10);
- post-merge main CI `29419008129` PASS;
- M2 + seven concurrency nodes executed with zero target skips;
- independent post-CI audit PASS on pre-merge head `64086dd…`.

### Gate 0b — S13-PR-001 documentation gate (active)

Before any S13 runtime PR:

- S13-PR-001 independent design audit PASS;
- owner Ready/squash/merge of S13-PR-001;
- runtime branches from the accepted main baseline after that merge;
- no Adaptive Intake runtime mixed into unrelated tasks.

S13-PR-002 is **not** authorized until Gate 0b completes.

### Gate 1 — deterministic baseline before external AI

Workbook discovery, mapping profiles, deterministic identity retrieval and DOCX extraction must work without Gemini/DeepSeek. Sprint 16 augments, not replaces, those paths.

### Gate 2 — source and review before knowledge activation

No historical bootstrap activation until source locators, alignment review and candidate lineage are complete.

---

## 4. Sprint 13 — Adaptive Intake and Column Mapping Memory

### S13-PR-001 — Design Authority and Contract Reconciliation

**Type:** docs-only (this PR).
**Status:** active until independent design audit PASS and owner merge.
**Scope:** Design Book v1.4, ADR 0030–0032, Authority Index, contract/handoff/CODEX/guardrails reconciliation, this plan.
**Not implemented:** runtime code, migrations, dependencies, AI calls.
**Gate:** document link/status consistency, privacy scan, independent design review.
**Does not authorize:** S13-PR-002 or any S13 runtime work.

### S13-PR-002 — Legacy Workbook Adapter and Immutable Source Artifact

**Closes:** G-01 and the source-replay prerequisite.

Scope:

- neutral `WorkbookAdapter` contract;
- safe `.xlsx` adapter extraction behind the contract;
- safe `.xls` adapter following dependency/security spike;
- immutable source artifact/checksum/storage metadata;
- value-only behavior, no macro/formula/external execution;
- bounded resource/security limits for both formats;
- friendly Vietnamese format/security errors.

Required tests:

- valid `.xls` and `.xlsx` fixtures;
- malformed/encrypted/macro/external-link rejection as applicable;
- max file/row/column/cell boundaries;
- duplicate and blank header preservation;
- source checksum and prior-generation preservation on failure;
- no `ProjectAssetLine` mutation.

Non-goals:

- no semantic mapping;
- no new identity logic;
- no Office desktop automation.

### S13-PR-003 — Workbook Structure Discovery and Row Classification

**Closes:** G-02 and G-04.

Scope:

- rank candidate sheets/table regions/header spans;
- support title rows and multi-row headers;
- classify `asset/section/subtotal/total/note/empty/unresolved`;
- persist/version structure snapshot and rule version;
- expose explanations and candidate confidence;
- fail to review instead of silently choosing ambiguous regions.

Required tests:

- PD-001 selects/proposes sheet `PD-001` and header row 5;
- A1 title is not accepted as the table header;
- `PHẦN ĐIỆN` and `PHẦN NƯỚC` are sections;
- total/subtotal/note rows are not materialized as assets;
- inserted/reordered title/header rows create review rather than silent drift;
- deterministic replay from the same structure snapshot.

### S13-PR-004 — Column Mapping Memory Persistence and Application Services

**Closes:** G-03 and G-06.

Scope:

- migrations/models for source snapshot, profile, fields, decision and usage;
- semantic role registry;
- customer/template fingerprinting;
- profile versions and supersession;
- proposal/confirm/reject application services;
- exact mapping snapshot per import batch;
- materialize staging only from confirmed mapping;
- tenant/RBAC/audit contracts.

Required tests:

- map `TÊN VẬT TƯ`, `KHỐI LƯỢNG`, `GIÁ TĐ` by semantics;
- permit blank-header I to be confirmed as `evidence_note`;
- same customer/template retrieves the active profile;
- moved columns produce the correct new snapshot/profile version;
- duplicate/conflicting profile requires review;
- cross-tenant profile access fails closed;
- correcting a profile never rewrites prior batch mapping;
- no AI/rule proposal materializes staging without confirmation.

### S13-PR-005 — Mapping Confirmation API and Astryx Vietnamese UX

**Closes:** G-05.

Scope:

- analysis/proposal/read/confirm API adapters;
- step **Xác nhận cấu trúc file**;
- sheet/header/table preview;
- role selectors and blank-header rendering;
- row-type preview and warnings;
- `Ghi nhớ cấu trúc này cho khách hàng`;
- optimistic version/double-submit protection;
- Vietnamese i18n and friendly errors;
- Astryx-only patterns.

Required tests:

- non-IT happy path from upload to confirmed staging;
- required-role missing/duplicate conflicts;
- stale profile/decision response;
- loading/error/empty states;
- keyboard/accessibility and layout tests as supported;
- frontend cannot bypass server confirmation.

### Sprint 13 completion gate

- both formats accepted safely;
- sample structure/roles/row classes pass;
- profile reuse/versioning works;
- mapping UI is human-confirmed and Vietnamese-first;
- existing S12 validation/Apply invariants are preserved;
- PostgreSQL migration/tenant/concurrency tests pass.

---

## 5. Sprint 14 — Raw Asset Observation and Asset Identity Memory

### S14-PR-001 — Raw Asset Observation and Contextual Alias Persistence

**Closes:** the data foundation for G-10/G-11.

Scope:

- `RawAssetObservation` persistence and immutable source locator;
- link to staging/import and optional project/dossier contexts;
- `ContextualAssetAlias` organization/customer scope;
- status/version/source-decision lineage;
- compatible relationship to CanonicalAsset/AssetVariant;
- migration/backfill policy for current imported project lines.

Required tests:

- raw wording/unit/quantity remain unchanged after identity decisions;
- customer-specific alias scope;
- curated AssetAlias remains distinct;
- merge/deprecate preserves alias/decision lineage;
- cross-tenant reads/writes fail closed.

### S14-PR-002 — Deterministic Explainable Asset Matcher

Scope:

- normalization and attribute extraction baseline;
- layered candidate retrieval;
- contextual alias/customer precedent;
- canonical/variant/code/fuzzy/attribute scoring;
- top-k and score breakdown;
- close-candidate/conflicting-attribute detection;
- derived/rebuildable match index;
- price excluded as a primary identity key.

Required tests:

- exact contextual/curated alias precedence;
- model/brand/attribute match and conflict cases;
- local wording and mixed name/spec examples from PD-001;
- deterministic score version/replay;
- recall@k benchmark fixture;
- no official write from candidate generation.

### S14-PR-003 — Identity Review, Decision and Feedback Contract

**Closes:** G-10.

Scope:

- append-only accepted/corrected/rejected/deferred decisions;
- positive/negative `LearningFeedbackEvent` semantics;
- approved contextual alias creation/promotion path;
- high-confidence explicit batch review, never auto-approval;
- UI step **Đối chiếu tài sản** using Astryx/Vietnamese;
- raw/candidate/difference/source views;
- top-k selection, create variant/new asset/defer actions.

Required tests:

- only committed human decisions become feedback;
- temporary/failed/rolled-back/auto-rejected candidates do not become positive examples;
- rejected candidate reason persists;
- duplicate submit and stale review protection;
- no automatic active CanonicalAsset/Alias/KnowledgeVersion;
- audit actor/time/version completeness.

### Sprint 14 completion gate

- raw observations and contextual aliases are first class;
- deterministic matcher has measurable recall@k and explanations;
- all identity outcomes are human-reviewed and append-only;
- next Excel-only import can reuse reviewed history without AI.

---

## 6. Sprint 15 — Paired Dossier, Word Runtime and Historical Bootstrap

### S15-PR-001 — DossierBundle and Source File Roles

**Closes:** G-07.

Scope:

- DossierBundle aggregate and lifecycle;
- source file roles/checksums/access policy;
- bootstrap batch identity/idempotency;
- organization/customer/report/valuation metadata;
- link to existing Project only when real, not manufactured.

Required tests:

- pair Excel + Word in one bundle;
- required/duplicate role rules;
- source immutability/checksum;
- rerun idempotency;
- tenant and evidence-access security.

### S15-PR-002 — DOCX Extraction Runtime and Table Role Candidates

**Closes:** G-09.

Scope:

- deterministic DOCX paragraphs/tables/layout extraction;
- ExtractedTable/Row persistence missing from runtime code;
- metadata extraction for report number/date/valuation time/customer;
- candidate roles for technical/comparison/final tables;
- source table/row/cell locator;
- retry/version/failure behavior;
- bounded PDF/OCR extension contract, not necessarily full OCR in this PR.

Required tests:

- PD-001 extracts report metadata;
- 49 technical rows;
- 3 suppliers × 49 = 147 quote observations;
- 49 final-result rows;
- source locators and extraction version;
- parser failure preserves prior reviewed extraction;
- no official mutation.

### S15-PR-003 — Multi-Table Dossier Row Alignment and Review UX

**Closes:** G-08.

Scope:

- `DossierRowAlignment` model/service;
- STT/section/order/name/unit/quantity/attribute scoring;
- missing/inserted/split/merged/reordered row handling;
- conflict explanations;
- review/confirm/reject/unresolved workflow;
- Astryx/Vietnamese alignment review.

Required tests:

- 49 sample alignments are proposed/reviewable;
- order-only matching is rejected as sole authority;
- `Km` vs `Mét` is flagged;
- epoxy rounding is recorded as transformation;
- five materially changed names remain linked raw-to-standardized;
- removed/reordered synthetic rows create conflicts, not drift.

### S15-PR-004 — Reviewed Historical Bootstrap Candidate Import

Scope:

- produce identity/contextual-alias/spec/quote/decision/knowledge candidates;
- price-proposal vs QuoteLine vs final-decision separation;
- raw evidence-note observation and typed-resolution candidate;
- human promotion commands;
- batch metrics, reconciliation and deactivation/rollback;
- pilot with 5–10 diverse dossiers before 20–50 corpus expansion.

Required tests:

- no direct active-knowledge SQL injection;
- full source lineage for every promoted candidate;
- quote supplier/time/evidence completeness;
- rerun does not duplicate candidates/knowledge;
- rollback/deactivation retains source and audit;
- reconciliation counts match source/alignment/promoted outputs.

### Sprint 15 completion gate

- historical dossier is a real aggregate;
- Word extraction and alignment run end to end;
- bootstrap creates reviewed candidates with full lineage;
- sample and adversarial row-drift fixtures pass;
- pilot data can seed both memories safely.

---

## 7. Sprint 16 — Audited AI Column Mapper and Asset Matcher

### S16-PR-001 — Gemini/DeepSeek AI Gateway Runtime

Scope:

- backend-only provider interface;
- Gemini, DeepSeek and deterministic/mock provider;
- prompt/task registry;
- tenant-scoped context bundles;
- timeout/rate/cost/audit/error handling;
- no provider credentials in frontend/logs.

### S16-PR-002 — AI Column Mapping Suggestion Task

**Partially closes:** G-11.

- implement `AI-TASK-COLUMN-MAPPING-SUGGEST`;
- schema-validate role/row candidates;
- combine with deterministic proposal;
- expose reasons/confidence/model/prompt version;
- mandatory mapping review;
- fallback to deterministic/manual flow on AI failure.

### S16-PR-003 — AI Asset Identity Rerank Task

**Closes:** remaining G-11 scope.

- extend `AI-TASK-ASSET-IDENTITY-SUGGEST` over deterministic top-k;
- never allow AI to invent unreferenced active assets/evidence;
- show reason/difference/conflict explanations;
- mandatory identity review;
- fallback to deterministic matcher.

### S16-PR-004 — End-to-End Evaluation and Release Gate

- versioned 20–50 dossier corpus with train/evaluation separation;
- compare deterministic baseline vs AI-assisted path;
- measure mapping accuracy, alignment accuracy, recall@k, false high-confidence and review time;
- deploy only if agreed thresholds pass;
- rollback provider/prompt/model version;
- no online per-click training.

### Sprint 16 completion gate

- AI tasks work end to end through audited gateway;
- deterministic/manual fallback remains complete;
- AI cannot auto-confirm, auto-Apply or activate knowledge;
- evaluation shows measurable benefit without unacceptable high-confidence errors.

---

## 8. Cross-cutting data and migration rules

- Every migration states tenant scope, indexes, delete behavior and downgrade/rollback limits.
- Source artifacts, raw observations, decisions and reviewed extraction use RESTRICT/immutability semantics appropriate to audit lineage.
- Existing S12 batches/rows remain readable; do not retroactively infer confirmed profiles.
- Backfill creates `unknown_legacy_mapping` metadata where exact prior mapping decisions do not exist.
- Derived fingerprints/indexes may be rebuilt; they are not source-of-truth records.
- Active/canonical records are never seeded by migration scripts.
- Pilot/import data uses application commands and batch idempotency keys.

---

## 9. Security and privacy gates

Every code PR must prove:

- server-derived actor/organization/customer/project/bundle scope;
- no cross-tenant profile, alias, observation, dossier or AI-context access;
- no raw file/cell payloads in general audit logs;
- no formula/macro/external execution;
- no provider secret exposure;
- no unrestricted context sent to AI;
- fail-closed behavior on unknown/ambiguous targets;
- immutable evidence/source lineage.

---

## 10. UX gates

- Vietnamese labels are externalized in i18n.
- Astryx components/tokens only unless separately approved.
- Non-IT users see business language and corrective actions, not HTTP/SQL/model internals.
- Mapping and identity review show source data, proposal, differences and explicit confirm/reject actions.
- Confidence color alone is insufficient; text labels and reasons are required.
- Empty/loading/error/stale/double-submit states are specified and tested.

---

## 11. Quality dashboard

Track by adapter/rule/profile/model version:

```text
sheet and header discovery accuracy
column-role accuracy and correction rate
row-classification accuracy
profile reuse and conflict rate
raw locator completeness
identity recall@k and top-1 acceptance
false high-confidence identity rate
dossier extraction/table-role accuracy
row-alignment accuracy
quote supplier/time/evidence completeness
review time and deferred rate
reuse accuracy on subsequent imports
```

No confidence threshold is production-frozen from the single PD-001 dossier.

---

## 12. Definition of completion for the remediation program

The program is complete only when all G-01…G-11 are closed by code, tests and audit; Design Book/ADR/handoff truth matches the merged main; the deterministic/manual path works without AI; the paired-dossier bootstrap has reviewed pilot evidence; and no unresolved blocker is hidden behind a PASS label.
