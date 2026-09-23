# VALORA Documentation Status Index

**Status:** CURRENT DOCUMENTATION GOVERNANCE
**Date:** 2026-09-23
**Scope:** Classification and reading rules for repository documentation.
**Inventory reconciliation:** 351 documentation/config-document files at the 2026-09-21 live-tree verification sweep.

## 1. Why this index exists

The repository contains current authority, implementation contracts, historical sprint plans, audits,
research notes and superseded handoffs. A file being present in the repository does **not** make it a
current roadmap or product authority.

When documents conflict, use this order:

```text
Explicit current Product Owner decision — wins only in named scope
→ current v2.3 UI/UX master + Authority Index + applicable addenda + accepted scoped ADRs
   (product semantics / workflow / IA / interaction / Microsoft Fluent 2 light visual authority)
→ VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md
   (development sequencing / architecture integration)
→ current implementation contracts / active task contract
→ project handoff / acceptance matrix
→ historical design/sprint/audit/research evidence
```

Historical evidence must not be rewritten to pretend it knew later decisions.

## 2. Current product/UX authority and roadmap roles

Current product/UX authority:

- `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`
- `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
- current v2.3 Design Authority addenda referenced by that index
- accepted scoped ADRs where architecture/persistence semantics are explicitly governed

Current development sequencing / architecture integration:

- `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`
- `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` — OS-G7 architecture detail; documentation authority only, not runtime activation

Conflict-resolution/read-order map:

- `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`

Current document-change authority:

- ADR 0043 — app-owned immutable document storage
- ADR 0044 — OneDrive Personal Exchange v1, amended by ADR 0045
- ADR 0045 — Working Change Observation / DocumentChangeCandidate / Human Commit
- `VALORA_UIUX_HANDOFF_v2.3_WORKING_CHANGE_OBSERVATION_REVIEW_CONTRACT_ADDENDUM.md`

Current roadmap ordering:

```text
OS-G0 Authority + Fluent 2 light visual-system reconciliation
→ OS-G1 Pre-case
→ OS-G2 Appraisal Core
→ OS-G3 Document Runtime
→ OS-G4 Release/Publishing
→ OS-G5 Template Intelligence/Fidelity
→ OS-G6 Product E2E
→ OS-G7 Valora Intelligence Platform & Assistant
```

Current visual authority is **Microsoft Fluent 2 light, desktop-first, Vietnamese-first, data-heavy/table-first**. Astryx is historical/low-level reference only and must not drive product styling.

Sub-domain plans may not reorder this sequence without a new Product Owner decision.

## 2.1 Current visual-system disposition

- Microsoft Fluent 2 light is current product visual authority.
- S10/S12/S13/NCCQ/NCC Selection/Không gian tài liệu approved baselines are golden visual references.
- Astryx mapping/package records are historical/low-level implementation evidence only.
- Existing dark/cyan/glassmorphic frontend is remediation debt, not visual acceptance.
- Historical browser/PR acceptance remains functional evidence but does not prove current visual conformance.
- Current UI acceptance must include screenshot/visual-regression checks for authority-defined golden screens.
- Active OS-G0 execution contract: `docs/implementation/VALORA-FLUENT2-REMEDIATION-001.md`; its code inventory is `docs/audits/2026-09-22__FRONTEND_ASTRYX_TO_FLUENT2_CODE_INVENTORY.md`.

## 3. Current engineering / evidence documents

Use for current implementation truth, always checking the live Git/PR SHA:

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `PR_RULES.md`
- `README.md`
- `docs/VALORA_PROJECT_HANDOFF.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md`
- active implementation contracts explicitly marked current
- active plans explicitly marked current
- exact-head CI / manifests / closeout evidence

Current candidate facts as of this reconciliation:

- merged main: through PR #31 at `27d1cc6...`;
- Draft PR #32: active integration candidate; `feat/operational-frontend-m365` exact head is `d725bbc6...` after F2-PR-001/#34, F2-PR-002/#36 and F2-PR-003/#38 merged into that branch; this is not merged-main authority;
- Local immutable storage: G6 accepted;
- OneDrive Exchange: G8 offline complete at code milestone `f896f15...`;
- Working Change Observation: design/ADR accepted, runtime implementation contract still required;
- canonical Case State stages 5–16: not yet product-complete;
- Release/Publishing and full North-star E2E: not implemented.

## 4. Historical design handoffs

These remain useful as design history but are **not current authority**:

- `docs/design/VALORA_UIUX_HANDOFF_v1.8.md`
- `docs/design/VALORA_UIUX_HANDOFF_v1.9.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.0.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.1.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.2.md`

Current v2.3 master + newer addenda win within their scope.

## 5. Historical next-session handoff prompts

Everything under:

`docs/handoff/`

is a historical conversation/session transfer artifact. It must never override current Design
Authority, ADRs, the Unified Roadmap or live repository state.

## 6. Historical sprint plans

The following are implementation history, not current roadmap:

- `docs/01_SPRINT_0_PLAN.md`
- `docs/05_CODEX_PROMPTS_SPRINT_0.md`
- `docs/sprint-1/**`
- `docs/sprint-2/**`
- `docs/sprint-3/**`
- `docs/sprint-4/**`
- `docs/sprint-5/**`
- `docs/sprint-6/**`
- `docs/sprint-7/**`
- `docs/sprint-8/**`

They may explain why old runtime surfaces exist, but they do not authorize revival of:

- Review Queue as product axis;
- standalone Validation Dashboard;
- separate KSCL/reviewer workflow;
- multi-level approval;
- legacy S13 right-panel IA.

## 7. Audit and remediation evidence

Everything under:

- `docs/audits/**`
- `docs/remediation/**`

is immutable historical evidence unless a file explicitly states it is a current remediation task.
Do not rewrite test counts, historical verdicts or old assumptions. If a later decision supersedes an
audit conclusion, add a current disposition outside the evidence or in this status index.

## 8. Research / provider evidence

Research documents are evidence, not authority unless promoted by an ADR/Product Owner decision.

Specifically:

- old PR-07 direct OneDrive replacement research is historical/blocked;
- `VALORA_UIUX_V2_3_PR07_PROVIDER_CONFORMANCE_RUNBOOK.md` is historical direct-write research;
- old S3 provider-selection work remains a future reference;
- current VPS pilot provider is accepted local immutable storage;
- live AppFolder conformance is a separate Product Owner gate;
- no provider research may override ADR 0045 Human Commit semantics.

## 9. Plan directory status rules

`docs/plan/done/**` is historical closeout evidence.

Current files under `docs/plan/**` must carry an explicit status. At this reconciliation:

- `valora-storage-local-001.md` — COMPLETE / G6 ACCEPTED;
- `valora-onedrive-exchange-001.md` — COMPLETE / G8 OFFLINE ACCEPTED;
- `valora-storage-s3-spike-001.md` — deferred/reference unless explicitly reopened;
- PR-07 C2/OAuth plans — historical direct-write research; do not execute as current roadmap.

## 10. Template / Office intelligence documents

The v2.3 Template/AI baselines remain valid Design Authority for their UX/domain boundaries.

Roadmap placement is now:

```text
minimum deterministic compiler/fill needed by OS-G3
→ Release/Publishing
→ OS-G5 Template Intelligence/Fidelity expansion
   → AI Template Mapper
   → advanced visual QA
   → Template Family / adaptation
```

OS-G5 may freeze/implement AI-assisted template UX/task contracts, provider-neutral interfaces and deterministic/rule-based candidate mapping. LLM/external-provider execution remains OS-G7 runtime under the AI Master Plan unless separately and explicitly authorized.

OfficeCLI is only a candidate read-only Office Intelligence sidecar until a bounded conformance gate accepts it. OfficeCLI/template/AI work is not allowed to displace Pre-case or Appraisal Core closure.

## 11. Document lifecycle vocabulary

Use these distinct concepts:

- `TemplateMappingCandidate` — template authoring proposal;
- `GeneratedDocumentCandidate` — generated output awaiting verification/acceptance;
- `DocumentChangeCandidate` — external Working change awaiting review;
- `DocumentRevision` — accepted authoritative document version;
- Working / Export — non-authoritative external representation;
- `ReleaseManifest` — exact accepted revision set for publishing;
- `Published` — terminal release state.

Never collapse them into one generic Candidate/Version model.

## 12. AI architecture and implementation-contract status

Current AI architecture detail:
- `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md`;
- ADR 0033/0034 as retained foundations;
- `docs/implementation/VALORA-AI-PR-000...` through `...AI-PR-012...`.

Rules:
- AI-PR-000 is documentation-only.
- AI-PR-001…012 are **PLANNED / NOT AUTHORIZED FOR RUNTIME** until explicit assignment and prerequisites.
- Historical S13–S16 AI sequencing is evidence/reference only.
- No provider call, migration, agent, R2 promotion or autonomous command is authorized by documentation presence.
- OS-G1→OS-G6 should remain AI-readable-by-design.

## 13. Maintenance rule

When a current decision changes:

1. update the canonical authority / ADR;
2. update the Unified Roadmap if ordering changes;
3. update this status index and docs index;
4. amend current living contracts that would otherwise mislead implementation;
5. preserve historical audit/sprint evidence unchanged;
6. rerun a stale-marker documentation sweep.
