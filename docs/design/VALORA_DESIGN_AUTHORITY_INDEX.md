# Valora Design Authority Index

**Status:** Canonical reading order and conflict-resolution index
**Reconciled:** 2026-07-15 (S13-PR-001)
**Purpose:** Prevent older roadmap or provisional text from overriding newer owner-approved decisions.

## 1. Read order

1. `CODEX.md` — live task gate and agent operating rules.
2. `ENGINEERING_GUARDRAILS.md` — permanent security, tenant, audit and mutation invariants.
3. This file — version relationship and supersession map.
4. `docs/VALORA_PROJECT_HANDOFF.md` — verified implementation state and next authorized sequence.
5. Design Book v1.2-final package — established domain model and bounded contexts.
6. `VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md` — Vietnamese-first UX, Astryx, MVP scope and AI-provider architecture.
7. `VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md` — Adaptive Intake, two memories, paired dossiers, row alignment, feedback and revised roadmap.
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

## 3. Engineering baseline (evidence, not evergreen)

```text
S12-PR-004 squash-merged to main:
  a9f2c1e77e3ec46f216b881d608a02685b9d322a
Post-merge main CI:
  run 29419008129 — PASS (558 tests; M2 + seven PG nodes executed)
```

Agents must `git fetch origin` and verify live `origin/main`. Do **not** treat historical feature SHAs (`259ee59…`) or historical `main` (`32024be…`) as current status.

## 4. Active roadmap

```text
S12-PR-004 engineering gate: CLOSED (merged)
→ S13-PR-001 Design Authority and Contract Reconciliation (docs-only; active until audit/merge)
→ S13-PR-002+ Adaptive Intake / Column Mapping Memory runtime (only after S13-PR-001 merges)
→ S14 Asset Identity Memory
→ S15 paired-dossier extraction, alignment and bootstrap
→ S16 audited AI suggestion runtime
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
- Public fixtures must be anonymized; real client files never enter the public repository.

## 6. Implementation gates

Before any S13 runtime PR:

1. S13-PR-001 independent design audit must PASS.
2. Owner controls Ready, squash and merge of S13-PR-001.
3. Runtime work must branch from the accepted main baseline after that merge.
4. Follow PR order in `docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md`.

S13-PR-002 is **not** authorized until S13-PR-001 is independently audited and merged.

## 7. Module ownership (future runtime)

| Module | Future ownership |
|---|---|
| `excel_import` | Adaptive Intake, workbook adapters, Column Mapping Memory |
| `taxonomy_asset_identity` | Raw Asset Observation integration, contextual aliases, identity candidates/decisions |
| `document_engine_intelligence` | Dossier source roles, extraction, table roles, row alignment |
| `knowledge_evidence` | Reviewed quote/spec/knowledge candidates and activation |
| `ai_governance_security` | Provider gateway and audited suggestion tasks only |
| Workbench / frontend | Vietnamese Astryx review surfaces |

Cross-module calls use application services / contracts. Direct active-knowledge injection is forbidden.

## 8. Key ADR index

- ADR 0028 — restricted official Workbench mutation gate.
- ADR 0029 — S12 Apply command and provenance (**implemented**).
- ADR 0030 — versioned Column Mapping Memory and Adaptive Workbook Intake.
- ADR 0031 — contextual Asset Identity Memory and human-confirmed feedback.
- ADR 0032 — paired dossier aggregate, document extraction and row alignment.

Historical audit prose never overrides code plus CI evidence for the cited SHA.
