# DOC-R0 Documentation Authority Reconciliation Inventory

**Status:** Diagnostic candidate for Issue #92 / parent Issue #90. No DOC-R1…R6 remediation executed.
**Date:** 2026-10-03

Live baseline: `e2e03f3a91e21e366af72e35beeeab73ed18cfdb`; CODEX blob `756c51ed743868ed9658c336658ebebf67762cea`; [exact-main CI #559](https://github.com/Reguluspt/valora-engineering/actions/runs/37111129209) SUCCESS. PR #91 merged at that SHA and Issue #89 closed/certified; ADR 0050 is accepted/certified documentation, not runtime or deployment acceptance.

## Scope and exact census

The baseline contains **559 artifacts: 425 text documentation/config/evidence artifacts and 134 supporting binary/visual artifacts**. The candidate inventory includes the three new DOC-R0 outputs exactly once, yielding **562 artifacts (428 text + 134 binary)**. The scope is the four named root governance files and every tracked `docs/**` file; no old ~422 estimate is reused. Supporting JPG/PNG/PDF/XLSX files are included to make the evidence/reference inventory complete, beyond the required text-format subset. There are no MDX/YAML/YML files at this baseline.

The [JSON inventory](2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.json) is the complete per-path ledger. Its baseline rows retain source SHA-256, metadata, declared status/date, lifecycle/authority/state, marker candidates, interpreted disposition, link issues, review method, action, primary batch and finding references. Null status/date means no declaration found; declarations are not current certification. The three generated rows omit self-referential hash/size/line-count metadata explicitly. [Conflict matrix and batch proposal](2026-10-03__DOCUMENTATION_AUTHORITY_CONFLICT_MATRIX.md) record deferred work.

| Census | Count |
| --- | --- |
| Baseline tracked documentation/evidence | 559 |
| Baseline text formats | 425 |
| Supporting binary/visual evidence | 134 |
| Generated DOC-R0 outputs | 3 |
| Candidate total / unique paths | 562 |
| Duplicates / missing in-scope paths | 0 / 0 |

## Review strategy and authority

Current governance, authority indexes, unified roadmap, active plans and retained/planned contracts were read fully. Implicated accepted ADRs received full/targeted semantic review; all50 ADR headers/statuses were reconciled without inferring acceptance from implemented code. Historical audits, handoffs, sprint/remediation/research, closed plans and proposed ADRs received header/status/date, deterministic whole-text marker and local-link/reference review; targeted sections were read where currentness or disposition needed context. Binary files received metadata/hash/reference-membership review; no visual/PDF/XLSX content acceptance is claimed.

Lexical stale/architecture hits are candidates, not findings: dated snapshots, explicit prohibitions, accepted design without runtime activation and historical assertions are separated from current claims. Local Markdown targets/fragments and repo-qualified manifest references were checked. PDF `#page` is a viewer locator. Remote HTTP URLs were not availability-tested; backtick authority references received targeted review rather than generic URI validation.

Authority follows the explicit current owner decision in its named scope, live CODEX/guardrails, v2.3 master/index/addenda, unified roadmap, scoped AI plan, accepted scoped ADR/current contract, then dated evidence. ADR0048/49 are accepted scoped ratchets to Apply/status commands; frozen v1 bodies remain history. OS-G1 and ASSET_REVIEW are certified/closed; full OS-G2 and ASSET_WORKBENCH+ are not authorized by that closure. ADR0050 preserves server authority, no local LLM/GPU, foundation/UAT/pilot separation and OS-G7 gates.

## Reconciled counts

| Lifecycle | Count |
| --- | --- |
| A | 64 |
| B | 5 |
| C | 35 |
| D | 26 |
| E | 168 |
| F | 102 |
| G | 162 |

| Action | Count |
| --- | --- |
| UPDATE | 36 |
| ADD_NOTICE | 0 |
| INDEX_ONLY | 42 |
| PRESERVE | 484 |
| INVESTIGATE | 0 |

| Primary proposed artifact batch | Count |
| --- | --- |
| DOC-R1 | 3 |
| DOC-R2 | 2 |
| DOC-R3 | 22 |
| DOC-R4 | 6 |
| DOC-R5 | 0 |
| DOC-R6 | 45 |
| NONE | 484 |

| Category | Count |
| --- | --- |
| adr | 50 |
| architecture | 1 |
| audits | 154 |
| design | 84 |
| docs-root | 9 |
| handoff | 4 |
| implementation | 209 |
| plan | 17 |
| ref | 1 |
| remediation | 4 |
| research | 8 |
| root-governance | 4 |
| sprint-1 | 2 |
| sprint-2 | 3 |
| sprint-3 | 2 |
| sprint-4 | 2 |
| sprint-5 | 2 |
| sprint-6 | 2 |
| sprint-7 | 2 |
| sprint-8 | 2 |

| Format | Count |
| --- | --- |
| .jpg | 52 |
| .json | 20 |
| .md | 402 |
| .pdf | 3 |
| .png | 78 |
| .txt | 6 |
| .xlsx | 1 |

Batch counts assign each artifact exactly one primary owner; secondary link tasks travel with substantive changes. They do not sum matrix finding rows or the four external GitHub artifacts. `NONE` means no proposed edit/index action. `ADD_NOTICE=0` and DOC-R5=0: existing historical notices plus central classification are sufficient; no blanket notice rewrite is proposed.

## Current and retained artifacts requiring action

| Path | Class | Action | Primary batch | Findings |
| --- | --- | --- | --- | --- |
| [CODEX.md](../../CODEX.md) | A | UPDATE | DOC-R1 | R0-001, R0-002, R0-003 |
| [ENGINEERING_GUARDRAILS.md](../../ENGINEERING_GUARDRAILS.md) | A | UPDATE | DOC-R1 | R0-004, R0-005, R0-006 |
| [README.md](../../README.md) | A | UPDATE | DOC-R1 | R0-007, R0-008, R0-009, R0-010 |
| [docs/DOCUMENTATION_STATUS_INDEX.md](../../docs/DOCUMENTATION_STATUS_INDEX.md) | A | UPDATE | DOC-R6 | R0-014, R0-015, R0-016 |
| [docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md](../../docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md) | B | UPDATE | DOC-R2 | R0-011, R0-012 |
| [docs/adr/0036-computed-global-case-state-projection.md](../../docs/adr/0036-computed-global-case-state-projection.md) | D | UPDATE | DOC-R3 | R0-020 |
| [docs/adr/0037-durable-official-intake-commit.md](../../docs/adr/0037-durable-official-intake-commit.md) | D | UPDATE | DOC-R3 | R0-021 |
| [docs/adr/0038-bounded-preliminary-prefix-predicates.md](../../docs/adr/0038-bounded-preliminary-prefix-predicates.md) | D | UPDATE | DOC-R3 | R0-022 |
| [docs/adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md](../../docs/adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md) | D | UPDATE | DOC-R3 | R0-023 |
| [docs/adr/0047-authoritative-column-mapping-selection-and-recovery.md](../../docs/adr/0047-authoritative-column-mapping-selection-and-recovery.md) | D | UPDATE | DOC-R3 | R0-024 |
| [docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md](../../docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md) | D | UPDATE | DOC-R3 | R0-025 |
| [docs/adr/0049-asset-line-human-review-and-validation-authority.md](../../docs/adr/0049-asset-line-human-review-and-validation-authority.md) | D | UPDATE | DOC-R3 | R0-026 |
| [docs/adr/0050-linux-server-windows-native-client.md](../../docs/adr/0050-linux-server-windows-native-client.md) | D | UPDATE | DOC-R3 | R0-027 |
| [docs/architecture/VALORA_AI_MASTER_PLAN_V1.md](../../docs/architecture/VALORA_AI_MASTER_PLAN_V1.md) | A | UPDATE | DOC-R2 | R0-013 |
| [docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md](../../docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md) | A | UPDATE | DOC-R3 | R0-046, R0-047, R0-048, R0-049 |
| [docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md](../../docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md) | C | INDEX_ONLY | DOC-R6 | R0-056 |
| [docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md](../../docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md) | C | UPDATE | DOC-R6 | R0-058, R0-059 |
| [docs/design/VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md](../../docs/design/VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md) | A | UPDATE | DOC-R3 | R0-053 |
| [docs/design/VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md](../../docs/design/VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md) | A | UPDATE | DOC-R3 | R0-055 |
| [docs/design/VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md](../../docs/design/VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md) | A | UPDATE | DOC-R3 | R0-054 |
| [docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md](../../docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md) | A | UPDATE | DOC-R6 | R0-057 |
| [docs/design/assets/VALORA_TM01_BASELINE_v2.3.md](../../docs/design/assets/VALORA_TM01_BASELINE_v2.3.md) | A | UPDATE | DOC-R3 | R0-050, R0-051, R0-052 |
| [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-030, R0-031, R0-032, R0-042 |
| [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-033, R0-034 |
| [docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-035 |
| [docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-036 |
| [docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-037 |
| [docs/implementation/VALORA_UIUX_V2_3_PR01_OFFICIAL_INTAKE_COMMIT_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_OFFICIAL_INTAKE_COMMIT_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-038 |
| [docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_ANALYSIS_SNAPSHOT_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_ANALYSIS_SNAPSHOT_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-039 |
| [docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_RESULT_GENERATION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_RESULT_GENERATION_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-040 |
| [docs/implementation/VALORA_UIUX_V2_3_PR02_CASE_OVERVIEW_FRONTEND_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR02_CASE_OVERVIEW_FRONTEND_CONTRACT.md) | C | UPDATE | DOC-R3 | R0-041 |
| [docs/index.md](../../docs/index.md) | A | UPDATE | DOC-R6 | R0-017 |
| [docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md](../../docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) | A | UPDATE | DOC-R4 | R0-043 |
| [docs/plan/VALORA_LEAN_AGENT_PROTOCOL_V1.md](../../docs/plan/VALORA_LEAN_AGENT_PROTOCOL_V1.md) | A | UPDATE | DOC-R4 | R0-044 |
| [docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md](../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) | A | UPDATE | DOC-R4 | R0-045 |
| [docs/plan/VALORA_OS_G2_A5_WORKBENCH_SESSION_RBAC_AUTHORITY_PROPOSAL.md](../../docs/plan/VALORA_OS_G2_A5_WORKBENCH_SESSION_RBAC_AUTHORITY_PROPOSAL.md) | C | UPDATE | DOC-R4 | R0-029 |
| [docs/plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md](../../docs/plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md) | C | UPDATE | DOC-R4 | R0-028 |

## Complete ADR status / supersession map

| ADR path | Declared lifecycle | Disposition | Action / primary batch |
| --- | --- | --- | --- |
| [docs/adr/0001-record-architecture-decisions.md](../../docs/adr/0001-record-architecture-decisions.md) | D / Accepted | Accepted ADR-recording foundation; historical DesignBook hierarchy yields to current CODEX scoped hierarchy. | PRESERVE / NONE |
| [docs/adr/0002-persistence-orm-migration-strategy.md](../../docs/adr/0002-persistence-orm-migration-strategy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0003-auth-session-password-hashing-strategy.md](../../docs/adr/0003-auth-session-password-hashing-strategy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0004-rbac-enforcement-and-permission-snapshot.md](../../docs/adr/0004-rbac-enforcement-and-permission-snapshot.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0005-audit-event-persistence-strategy.md](../../docs/adr/0005-audit-event-persistence-strategy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0006-fuzzy-duplicate-matching-policy.md](../../docs/adr/0006-fuzzy-duplicate-matching-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0007-project-file-upload-storage-policy.md](../../docs/adr/0007-project-file-upload-storage-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0008-future-slice-endpoint-handling-policy.md](../../docs/adr/0008-future-slice-endpoint-handling-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0009-sprint-1-migration-and-seed-plan-clarification.md](../../docs/adr/0009-sprint-1-migration-and-seed-plan-clarification.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0010-taxonomy-hierarchy-and-scope-policy.md](../../docs/adr/0010-taxonomy-hierarchy-and-scope-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0011-asset-family-dna-attribute-definition-policy.md](../../docs/adr/0011-asset-family-dna-attribute-definition-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0012-canonical-asset-variant-boundary-policy.md](../../docs/adr/0012-canonical-asset-variant-boundary-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0013-asset-alias-scope-and-normalization-policy.md](../../docs/adr/0013-asset-alias-scope-and-normalization-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0014-identity-candidate-generation-policy.md](../../docs/adr/0014-identity-candidate-generation-policy.md) | D / Accepted for Sprint 2 candidate generation mechanics. | Accepted candidate mechanics; automated approval superseded by ADR0031; no global Review Queue authority. | PRESERVE / NONE |
| [docs/adr/0015-duplicate-merge-lineage-policy.md](../../docs/adr/0015-duplicate-merge-lineage-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0016-taxonomy-asset-identity-rbac-and-review-policy.md](../../docs/adr/0016-taxonomy-asset-identity-rbac-and-review-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0017-sprint-2-migration-and-seed-policy.md](../../docs/adr/0017-sprint-2-migration-and-seed-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0018-knowledge-version-registry-strategy.md](../../docs/adr/0018-knowledge-version-registry-strategy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0019-quote-price-conflict-formulas.md](../../docs/adr/0019-quote-price-conflict-formulas.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0020-evidence-immutability-unlink-cleanup-policy.md](../../docs/adr/0020-evidence-immutability-unlink-cleanup-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0021-sensitive-evidence-access-log-policy.md](../../docs/adr/0021-sensitive-evidence-access-log-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0022-quote-batch-line-appraised-price-boundary.md](../../docs/adr/0022-quote-batch-line-appraised-price-boundary.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0023-ai-knowledge-queue-auto-reject-policy.md](../../docs/adr/0023-ai-knowledge-queue-auto-reject-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0024-knowledge-evidence-rbac-and-review-policy.md](../../docs/adr/0024-knowledge-evidence-rbac-and-review-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0025-sprint-3-migration-and-seed-policy.md](../../docs/adr/0025-sprint-3-migration-and-seed-policy.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0026-authentication-identity-boundary-hardening-proposal.md](../../docs/adr/0026-authentication-identity-boundary-hardening-proposal.md) | D / Accepted | Accepted auth/cookie/session/CSRF foundation retained by ADR0050. | PRESERVE / NONE |
| [docs/adr/0027-workbench-session-cardinality-and-state-scope.md](../../docs/adr/0027-workbench-session-cardinality-and-state-scope.md) | D / Accepted | Accepted Workbench session scope; OS-G2 A5R/A5R2 ratchets role-grant disposition only. | PRESERVE / NONE |
| [docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md](../../docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md) | D / Accepted | Accepted restricted-field mutation foundation; ADR0049 dedicated status commands ratchet routing, value drafts/no status PATCH retained. | PRESERVE / NONE |
| [docs/adr/0029-excel-staging-apply-command-and-lineage.md](../../docs/adr/0029-excel-staging-apply-command-and-lineage.md) | D / Accepted (owner-approved design authority, 2026-07-14) | Accepted frozen Apply v1 historical scope; ADR0048 accepted/current guarded Apply v2 successor, not rewritten v1. | PRESERVE / NONE |
| [docs/adr/0030-versioned-column-mapping-memory-and-adaptive-workbook-intake.md](../../docs/adr/0030-versioned-column-mapping-memory-and-adaptive-workbook-intake.md) | D / Accepted — owner-requested design authority, 2026-07-14. | Accepted mapping/adaptive intake semantics; ADR0046/47 implemented scoped current-batch/selection successors; dated G1.1-not-started note preserved. | PRESERVE / NONE |
| [docs/adr/0031-contextual-asset-identity-memory-and-human-confirmed-feedback.md](../../docs/adr/0031-contextual-asset-identity-memory-and-human-confirmed-feedback.md) | D / Accepted — owner-requested design authority, 2026-07-14. **2026-09-21 reconciliation:** the former Gate 0c/Sprint 14 implementation ordering is historical; current implementation timing follows the Unified Roadmap v2.3 and a task-specific contract. No runtime or autonomous identity decision is authorized by this ADR alone. | Accepted human-confirmed identity/memory foundation; old Sprint14 ordering not current; provider AI remains gated. | PRESERVE / NONE |
| [docs/adr/0032-paired-dossier-aggregate-document-extraction-and-row-alignment.md](../../docs/adr/0032-paired-dossier-aggregate-document-extraction-and-row-alignment.md) | D / Accepted — owner-requested design authority, 2026-07-14. **2026-09-21 reconciliation:** the former Gate 0c/Sprint 15 implementation ordering is historical; current implementation timing follows the Unified Roadmap v2.3 and a task-specific contract. No runtime or autonomous bootstrap is authorized by this ADR alone. | Accepted dossier extraction/alignment foundation; no replacement of current product sequencing. | PRESERVE / NONE |
| [docs/adr/0033-audited-ai-task-runs-decision-episodes-and-learning-evidence.md](../../docs/adr/0033-audited-ai-task-runs-decision-episodes-and-learning-evidence.md) | D / Accepted — owner-requested design authority, 2026-07-16. | Accepted future AI provenance semantics; no runtime/provider activation. | PRESERVE / NONE |
| [docs/adr/0034-risk-tiered-execution-policy-and-reliable-autonomous-commands.md](../../docs/adr/0034-risk-tiered-execution-policy-and-reliable-autonomous-commands.md) | D / Accepted — owner-requested design authority, 2026-07-16. | Accepted future ExecutionPolicy semantics; no R2 promotion or runtime activation. | PRESERVE / NONE |
| [docs/adr/0035-alembic-schema-drift-reconciliation.md](../../docs/adr/0035-alembic-schema-drift-reconciliation.md) | F / Proposed | Declared Proposed: historical proposal only; no acceptance inferred, no current task authorization. | PRESERVE / NONE |
| [docs/adr/0036-computed-global-case-state-projection.md](../../docs/adr/0036-computed-global-case-state-projection.md) | D / Accepted for architecture; fact-mapping gate remains open | Accepted computed projection; five-stage implemented scope; later unavailable providers/predicates remain gated. | UPDATE / DOC-R3 |
| [docs/adr/0037-durable-official-intake-commit.md](../../docs/adr/0037-durable-official-intake-commit.md) | D / Accepted — PR-01a authority closeout complete locally | Accepted Official Intake foundation; ADR0046/47 scoped successors implemented; local historical evidence preserved. | UPDATE / DOC-R3 |
| [docs/adr/0038-bounded-preliminary-prefix-predicates.md](../../docs/adr/0038-bounded-preliminary-prefix-predicates.md) | D / Accepted for design authority — source facts, providers and runtime remain unimplemented | Accepted prefix predicates; implemented under certified G1.1 closure; ADR0046/47 scoped currentness ratchets retained. | UPDATE / DOC-R3 |
| [docs/adr/0039-tenant-safe-ncc-selection-revisions.md](../../docs/adr/0039-tenant-safe-ncc-selection-revisions.md) | D / ACCEPTED — PRODUCT OWNER APPROVED | Accepted NCC-selection foundation; no inference of complete later OS-G2 product stages. | PRESERVE / NONE |
| [docs/adr/0040-onedrive-delegated-integration-and-file-binding.md](../../docs/adr/0040-onedrive-delegated-integration-and-file-binding.md) | D / ACCEPTED — PRODUCT OWNER AUTHORIZED IMPLEMENTATION **Date:** 2026-09-12 **Task:** `VALORA-PR05-IMPL-001` | Accepted delegated provider/file-binding foundation; no mutable OneDrive business authority; ADR0043-45 govern current revisions. | PRESERVE / NONE |
| [docs/adr/0041-onedrive-personal-return-revalidation-observations.md](../../docs/adr/0041-onedrive-personal-return-revalidation-observations.md) | D / ACCEPTED FOUNDATION — CURRENT DOCUMENT-CHANGE SEMANTICS EXTENDED BY ADR 0045 **Date:** 2026-09-12 **Task:** `VALORA-PR06-IMPL-001` | Accepted return/revalidation read foundation; Working change promotion extended by ADR0045. | PRESERVE / NONE |
| [docs/adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md](../../docs/adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md) | D / ACCEPTED HISTORICAL PR-07 AUTHORITY — COMPARISON/CONFLICT SEMANTICS RETAINED; DIRECT-WRITE EXECUTION RE-BASELINED BY ADR 0043–0045 **Date:** 2026-09-13 **Task:** `VALORA-PR07-CONTRACT-001` | Partially superseded accepted ADR: protected-value/Old-V-W comparisons retained; direct-write execution historical/blocked under ADR0043-45. | PRESERVE / NONE |
| [docs/adr/0043-app-owned-immutable-document-storage.md](../../docs/adr/0043-app-owned-immutable-document-storage.md) | D / AMENDED — LOCAL VPS G6 ACCEPTED; G8 OFFLINE EXCHANGE COMPLETE | Accepted/amended app-owned immutable blobs, DB revision/CurrentHead, G6; production recovery targets remain binding, not achieved. | PRESERVE / NONE |
| [docs/adr/0044-onedrive-personal-exchange-v1.md](../../docs/adr/0044-onedrive-personal-exchange-v1.md) | D / ACCEPTED FOR OFFLINE IMPLEMENTATION — DOCX WORKING RE-IMPORT PROMOTION AMENDED BY ADR 0045 | Accepted G8 offline Exchange; changed Working DOCX promotion amended by ADR0045; live gate not automatic. | PRESERVE / NONE |
| [docs/adr/0045-working-copy-change-observation-and-human-confirmed-document-revision.md](../../docs/adr/0045-working-copy-change-observation-and-human-confirmed-document-revision.md) | D / ACCEPTED DESIGN / RUNTIME CONTRACT REQUIRED | Accepted Working observation/candidate/human revision semantics; runtime contract still required, not certified by G0/G2. | PRESERVE / NONE |
| [docs/adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md](../../docs/adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md) | D / Accepted design authority (Product Owner decisions D1–D3); G1.1 runtime not started | Accepted scoped Pre-case D1-D3; implementation certified via G1.1K/PR68; status metadata stale. | UPDATE / DOC-R3 |
| [docs/adr/0047-authoritative-column-mapping-selection-and-recovery.md](../../docs/adr/0047-authoritative-column-mapping-selection-and-recovery.md) | D / Accepted by Product Owner on 2026-09-29; runtime implementation in F0 candidate pending merge | Accepted mapping selection/recovery; F0/PR62 and H/PR63 implemented, G1 closed PR68; pending header stale. | UPDATE / DOC-R3 |
| [docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md](../../docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md) | D / **ACCEPTED PRODUCT OWNER AUTHORITY — 2026-10-02.** Task `VALORA-TASK-OS-G2-A1-ENTRY-GUARD-CASESTATE-AUTHORITY-RATCHET`, [Issue #73](https://github.com/Reguluspt/valora-engineering/issues/73). Baseline `main=a293395c53ab12aa27cac86d82046a6a9f59983b`, exact-main CI #533 SUCCESS; 2026-10-02. The Product Owner accepted OS-G2 A1 in this task chat on 2026-10-02, accepting this ADR and the [Case State contract](../implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) as successor authority. Runtime remains unimplemented and UNAUTHORIZED; acceptance does not authorize implementation, capability activation or merge. | Accepted guarded Apply/Asset Review authority; A2/PR76 implemented, A5/PR86 closed; original acceptance-alone hold preserved as history. | UPDATE / DOC-R3 |
| [docs/adr/0049-asset-line-human-review-and-validation-authority.md](../../docs/adr/0049-asset-line-human-review-and-validation-authority.md) | D / **ACCEPTED PRODUCT OWNER AUTHORITY — 2026-10-02.** The Product Owner accepted OS-G2 A3 according to the Gate Owner recommendation recorded on PR #78. This authority is limited to the successor contract below; it does not imply runtime implementation or activation. Baseline at proposal: `main=b3085242d083e03f1663aa79ea3241bd48592c84`, exact-main CI #538 SUCCESS; A2 / PR #76 MERGED/CERTIFIED; migration head `f3a4b5c6d7e8`. | Accepted dedicated line validation/human review; A4/PR80 implemented, A5/PR86 closed; no later-stage authorization. | UPDATE / DOC-R3 |
| [docs/adr/0050-linux-server-windows-native-client.md](../../docs/adr/0050-linux-server-windows-native-client.md) | D / ACCEPTED PRODUCT OWNER ARCHITECTURE DECISION — Issue #89; repository certification pending | Accepted deployment/client architecture CERTIFIED ON MAIN via PR91/CI559; Windows/Linux runtime, deployment and formal UAT separately gated. | UPDATE / DOC-R3 |

## Preservation and validation boundary

Historical evidence changed: **NONE**. Runtime/source changed: **NO**. Unexpected current-authority edits: **NONE**. Candidate changes are exactly these three audit outputs. Original historical SHA/CI/verdict/count statements remain byte-for-byte preserved; links needing historical disposition are carried in the JSON and central matrix list. No semantic Product Owner decision is required (0); administrative retirement of four old GitHub artifacts is a later Gate Owner action.

Validation checks reconcile562 unique candidate paths,559 baseline hashes, class/action/batch totals, JSON parsing, generated local links and allowed changed paths. Candidate review/CI are recorded against the eventual frozen commit in the Draft PR closeout, outside these self-referential artifacts. Audit findings are deferred remediation, distinct from material defects in this inventory candidate.
