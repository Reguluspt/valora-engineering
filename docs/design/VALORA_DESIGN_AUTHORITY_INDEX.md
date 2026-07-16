# Valora Design Authority Index

**Status:** Canonical reading order and conflict-resolution index
**Reconciled:** 2026-07-16 (Gate 0c closeout / live-gate reconciliation)
**Purpose:** Prevent older roadmap or provisional text from overriding newer owner-approved decisions.

## 1. Read order

1. `CODEX.md` — live task gate and agent operating rules.
2. `ENGINEERING_GUARDRAILS.md` — permanent security, tenant, audit and mutation invariants.
3. This file — version relationship and supersession map.
4. `docs/VALORA_PROJECT_HANDOFF.md` — verified implementation state and next authorized sequence.
5. Design Book v1.2-final package — established domain model and bounded contexts.
6. `VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md` — Vietnamese-first UX, Astryx, MVP scope and AI-provider architecture.
7. `VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md` — Adaptive Intake, two memories, paired dossiers, row alignment, feedback, bounded-AI automation readiness and revised roadmap.
8. Feature contracts under `docs/design/` and accepted ADRs under `docs/adr/`.
9. Active remediation plan `docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md`, then task-specific audit evidence.

When two sources conflict, the newer explicit decision governs only the scope it names. Security, tenant isolation, immutable evidence, append-only decisions and human approval remain cumulative unless an accepted ADR explicitly supersedes them.

## 2. Version relationship

| Authority | Continues to govern | Superseded or extended by later authority |
|---|---|---|
| Design Book v1.2-final | Core domain architecture, canonical assets, evidence/knowledge, workflow and document boundaries | Extended, not replaced, by v1.3/v1.4 |
| Design Book v1.3 | MVP scope, Vietnamese-first UX, Astryx, provider gateway and human-in-the-loop AI | **§7 roadmap sequencing** is superseded by v1.4 (Sprint 13 is no longer “AI Assistant first”) |
| Design Book v1.4 | Adaptive workbook intake, Column Mapping Memory, Asset Identity Memory, historical dossier bootstrap, row alignment and feedback | Does **not** silently change S12 Apply v1 |
| Excel staging contract §15 / ADR 0029 | S12 Apply command and `s12-pr-004-v1` semantics (implemented/merged) | A future Apply change requires a new version and ADR |
| ADR 0014 | Historical deterministic candidate-generation rationale | Automated batch approval wording is superseded by **ADR 0031** |
| ADR 0030 | Column Mapping Memory and Adaptive Workbook Intake | Implementation gated by S13 plan |
| ADR 0031 | Asset Identity Memory and human-confirmed feedback | Implementation gated by S14 plan |
| ADR 0032 | Paired dossier aggregate, extraction and row alignment | Implementation gated by S15 plan |
| ADR 0033 | Audited AI task runs, Decision Episodes and learning evidence | Phase-appropriate implementation begins with domain decisions; AI runtime gated by S16 |
| ADR 0034 | Risk-tiered Execution Policy and reliable autonomous commands | Defines extension point only; no R2 capability promoted by S13–S16 |

## 3. Engineering baseline (evidence, not evergreen)

```text
Gate 0c design authority squash-merged to main:
  99dfccbc7bf2893fa5b0dce8d52a01068655e39a
  (PR #13; audited head 656dc9ff70a453ee5b83f47d13b7040b3f062076;
   parent a3672f41bc54f42420fb70639a27bf50d604376a)
Post-merge main CI:
  run 29504915362 — PASS
Prior S13-PR-001 / closeout evidence (historical):
  7f7473e… / CI 29429680504; a3672f4… / CI 29474065397
Prior S12-PR-004 evidence (historical):
  a9f2c1e… / CI 29419008129 PASS
```


Agents must `git fetch origin` and verify live `origin/main`. Do **not** treat historical feature SHAs (`259ee59…`) or historical `main` (`32024be…` / `a9f2c1e…` alone) as current status when a newer accepted main exists.

## 4. Active roadmap

```text
S12-PR-004 engineering gate: CLOSED (merged)
S13-PR-001 design-authority gate: CLOSED (merged)
Gate 0c bounded-AI automation readiness: CLOSED / SATISFIED
Runtime assignment state: S13-PR-002 assigned / in progress (branch s13-pr-002-legacy-workbook-source-artifact; not merged)
→ S13-PR-002 Legacy Workbook Adapter and Immutable Source Artifact (in progress on feature branch; not merged)
→ S13-PR-003+ Column Mapping Memory / Adaptive Intake follow-ons (require separate owner assignment)
→ S14 Asset Identity Memory
→ S15 paired-dossier extraction, reliable jobs, alignment and bootstrap
→ S16 reliable audited AI suggestion runtime and shadow evaluation
→ S17 report generation
→ S18 real auth and pilot acceptance
```


Deterministic structure discovery, mapping profiles, identity retrieval and document extraction must exist before external AI is allowed to augment ambiguous cases.

## 5. Binding v1.4 decisions

- `ColumnMappingProfile` remembers customer/template workbook interpretation; it does not own asset identity.
- `RawAssetObservation` preserves exact customer wording and source locator; normalization never overwrites it.
- Asset Identity Memory owns contextual aliases, candidate explanations and human identity decisions.
- Historical Excel and Word/PDF files enter one `DossierBundle`; extracted tables remain source-backed candidates until reviewed.
- Supplier quotes, appraiser proposal and final appraised price are separate semantics.
- Only authenticated human-confirmed decisions create feedback. No per-click online training.
- AI may propose or rerank; it cannot confirm mapping, identity or price, Apply staging, or activate knowledge.
- Domain decisions remain authoritative; `AITaskRun` and `DecisionEpisode` add task/learning provenance without duplicating domain truth.
- Workflow-pattern learning uses domain commands and committed outcomes, never UI clickstream.
- AI/rules create typed proposals only. Write-capable execution requires deterministic `ExecutionPolicy` and an allowlisted idempotent domain command.
- Current S13–S16 scope does not promote R2 auto-draft/auto-stage. Later promotion requires task-specific design, shadow evaluation and owner-approved release.
- Human, system and AI-service principals remain distinct; AI/system execution cannot impersonate human approval.
- Long-running AI/extraction tasks require durable idempotent jobs and recoverable database/object-storage failure semantics before production automation.
- Public fixtures must be anonymized; real client files never enter the public repository.

## 6. Implementation gates

S13-PR-001 documentation/design-authority prerequisites (satisfied):

1. S13-PR-001 independent design audit PASS — **satisfied**.
2. Owner Ready, squash and merge of S13-PR-001 — **satisfied** (main `7f7473e…`).
3. Post-merge main CI PASS — **satisfied** (run `29429680504`).

Gate 0c — bounded-AI automation readiness (satisfied):

1. Design Book v1.4 §20 plus ADR 0033–0034 reconciled across authority, roadmap, handoff and agent rules — **satisfied**.
2. Independent design audit PASS on head `656dc9ff70a453ee5b83f47d13b7040b3f062076` — **satisfied**.
3. Owner Ready, squash and merge of Gate 0c PR #13 — **satisfied** (main `99dfccbc7bf2893fa5b0dce8d52a01068655e39a`).
4. Exact post-merge main CI PASS — **satisfied** (run `29504915362`).

Before any S13 runtime PR (still required for each task ID):

1. Separate explicit owner assignment of a runtime task ID.
2. Runtime work must branch from the then-current accepted `origin/main`.
3. Follow PR order in `docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md`.

S13-PR-002 is **assigned / in progress** on branch `s13-pr-002-legacy-workbook-source-artifact` from baseline `949903f3912aa65f8b990852756aeef7981bca08`; it is **not merged**. S13-PR-003+ still require separate owner assignment.

## 7. Module ownership (future runtime)

| Module | Future ownership |
|---|---|
| `excel_import` | Adaptive Intake, workbook adapters, Column Mapping Memory |
| `taxonomy_asset_identity` | Raw Asset Observation integration, contextual aliases, identity candidates/decisions |
| `document_engine_intelligence` | Dossier source roles, extraction, table roles, row alignment |
| `knowledge_evidence` | Reviewed quote/spec/knowledge candidates and activation |
| `ai_governance_security` | Task registry, context-manifest governance, provider gateway, AI-task provenance and deterministic Execution Policy boundary |
| Worker / reliable task runtime | Durable job/outbox execution, attempts, lease/retry/timeout/cancellation and stale-generation rejection |
| Workbench / frontend | Vietnamese Astryx review surfaces |

Cross-module calls use application services / contracts. Direct active-knowledge injection is forbidden.

## 8. Key ADR index

- ADR 0028 — restricted official Workbench mutation gate.
- ADR 0029 — S12 Apply command and provenance (**implemented**).
- ADR 0030 — versioned Column Mapping Memory and Adaptive Workbook Intake.
- ADR 0031 — contextual Asset Identity Memory and human-confirmed feedback.
- ADR 0032 — paired dossier aggregate, document extraction and row alignment.
- ADR 0033 — audited AI task runs, Decision Episodes and learning evidence.
- ADR 0034 — risk-tiered Execution Policy and reliable autonomous commands.

Historical audit prose never overrides code plus CI evidence for the cited SHA.
