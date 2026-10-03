# VALORA Documentation Status Index

**Status:** CURRENT DOCUMENTATION GOVERNANCE
**Date:** 2026-10-03 (DOC-R6 current disposition; dated evidence retained)
**Scope:** Classification and reading rules for repository documentation.
**Historical inventory reconciliation — 2026-09-24:** 380 documentation/config-document artifacts after the 2026-09-24 reconciliation closeout: 369 Markdown files + 11 supporting documentation artifacts (8 JSON/config evidence files + 3 approved design JPG assets) across the root governance set and `docs/**`. The pre-closeout audited source tree at `6a964112…` contained 379 artifacts; the additional artifact is the final reconciliation audit itself.

## 1. Why this index exists

The repository contains current authority, implementation contracts, historical sprint plans, audits,
research notes and superseded handoffs. A file being present in the repository does **not** make it a
current roadmap or product authority.

When documents conflict, use this order:

```text
Explicit current Product Owner decision — wins only in named scope
→ CODEX.md
→ ENGINEERING_GUARDRAILS.md
→ current v2.3 UI/UX master
→ current v2.3 UI/UX Authority Index
→ applicable current v2.3 addendum
→ VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md
→ VALORA_AI_MASTER_PLAN_V1.md for OS-G7 / AI-readiness only
→ accepted scoped ADR
→ current task / implementation contract
→ current handoff / acceptance evidence
→ historical Design Book / sprint / audit / remediation / research evidence
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
- `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` — current OS-G7 / AI-readiness architecture detail; documentation authority only, not runtime activation

Conflict-resolution/read-order map:

- `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`

Current document-change authority:

- ADR 0043 — app-owned immutable document storage
- ADR 0044 — OneDrive Personal Exchange v1, amended by ADR 0045
- ADR 0045 — Working Change Observation / DocumentChangeCandidate / Human Commit
- `VALORA_UIUX_HANDOFF_v2.3_WORKING_CHANGE_OBSERVATION_REVIEW_CONTRACT_ADDENDUM.md`

Current bounded Pre-case journey: **OS-G1 CERTIFIED/CLOSED** through G1.1K / PR #68 / CI #527. [ADR 0046](adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md) governs optional Customer, explicit current batch and immutable versioned analysis/result selection; [ADR 0047](adr/0047-authoritative-column-mapping-selection-and-recovery.md) is its implemented/certified bounded mapping-selection successor. Retained ADR 0030/0037/0038 foundations do not override these scoped successors.

Current Appraisal Core: **OS-G2 PARTIAL THROUGH ASSET_REVIEW**, certified through A5 / PR #86 / CI #555. [ADR 0048](adr/0048-post-intake-guarded-apply-and-asset-review-authority.md) governs implemented guarded Apply v2 / Asset Review Case State; [ADR 0049](adr/0049-asset-line-human-review-and-validation-authority.md) governs implemented human-triggered server validation and explicit human review, separate from value drafts. Use the [Case State contract](implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) and [Line Decision contract](implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md). Full OS-G2 remains INCOMPLETE; current_stage is capped at ASSET_REVIEW and ASSET_WORKBENCH+ remains NOT AUTHORIZED / NOT_AVAILABLE. New runtime still requires its own explicit task; this index grants none.

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

## 2.0 Deployment/client v1 disposition — Issue #89 (2026-10-03)

- [ADR 0050](adr/0050-linux-server-windows-native-client.md) — accepted Product Owner deployment/client decision; **REPOSITORY CERTIFIED** via PR #91, merge `e2e03f3a91e21e366af72e35beeeab73ed18cfdb`, exact-main [CI #559 / run 37111129209 SUCCESS](https://github.com/Reguluspt/valora-engineering/actions/runs/37111129209), Issue #89 CLOSED/CERTIFIED. Architecture documentation only; runtime and deployment remain separately gated. Linux single-node Server + HTTPS LAN + WinUI 3/WebView2 + server-hosted React/Fluent 2 light + typed native bridge + MSIX. Server retains business/auth/tenant/document/job authority; no local LLM/model-weight/GPU dependency, core workflow AI dependency NONE; provider-backed AI stays OS-G7 gated.
- [Windows Client plan](plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md) and [Linux Server plan](plan/VALORA_LINUX_SERVER_V1_PLAN.md) — PLANNED / NOT AUTHORIZED FOR RUNTIME OR DEPLOYMENT.
- [Windows Preview brief](implementation/VALORA_WINDOWS_PREVIEW_TASK_BRIEF.md) — reconciled; formal UAT after Software Completion, architecture/skeleton only through explicit owner task, Linux Deployment Pilot separate. Docker Desktop local-stack production direction and architecture selection after Preview are superseded.
- Existing dated inventories and status snapshots below are evidence of their recorded reconciliation, not current main certification. Issue #89 does not execute Issue #90's full-tree inventory/status cleanup or rewrite historical evidence.

## 2.1 Current visual-system disposition

- Microsoft Fluent 2 light is current product visual authority.
- S10/S12/S13/NCCQ/NCC Selection/Không gian tài liệu approved baselines are golden visual references.
- Astryx mapping/package records are historical/low-level implementation evidence only.
- F2-PR-001…008 are closed on merged `main` through squash PR #32. Their accumulated result establishes the OS-G0 Fluent 2 engineering closeout on main, including golden-surface remediation, provider-neutral Document Workspace, Astryx/package retirement, zero-debt visual ratchets and cross-surface regression evidence. Merged-main SHA is `51eab864…` with exact-head CI #485 SUCCESS; historical `Astryx`/dark/cyan/glass mentions or prohibition text do not imply current visual direction.
- Historical browser/PR acceptance remains functional evidence but does not prove current visual conformance.
- Current UI acceptance must include screenshot/visual-regression checks for authority-defined golden screens.
- Completed OS-G0 execution contract: `docs/implementation/VALORA-FLUENT2-REMEDIATION-001.md`; its code inventory is `docs/audits/2026-09-22__FRONTEND_ASTRYX_TO_FLUENT2_CODE_INVENTORY.md` and must be read as a historical code snapshot with its current disposition.
- Historical 2026-09-24 documentation reconciliation record: `docs/audits/2026-09-24__AI_MASTER_PLAN_UNIFIED_ROADMAP_DOCUMENTATION_RECONCILIATION.md`; current DOC-R6 evidence is linked in §2.3.

### 2.2 2026-09-24 inventory by lifecycle/category

Exact-tree inventory used for this reconciliation:

| Category | Count |
|---|---:|
| Root governance docs (`CODEX`, guardrails, PR rules, README) | 4 |
| `docs/` root files | 9 |
| ADR | 45 |
| Architecture | 1 |
| Audits | 151 |
| Design (including design assets) | 70 |
| Handoff | 4 |
| Implementation | 57 |
| Plan | 9 |
| Reference | 1 |
| Remediation | 4 |
| Research | 8 |
| Sprint 1–8 history | 17 |
| **Total** | **380** |

Lifecycle rule: current/living authority and active engineering documents receive substantive review; audits, old handoffs, sprint plans, research and superseded remediation are preserved as historical evidence and marker-scanned for misleading current-authority wording. Presence in the tree does not promote historical evidence to current authority.

### 2.3 Current final closeout census — DOC-R6 / 2026-10-03

At baseline main `9e743212f3b2b2ff4297d95795ae84bf3e79053a` / exact-main CI #565 SUCCESS, the DOC-R0 scope recount is **562 artifacts (428 text + 134 supporting binaries)**. This DOC-R6 candidate contains **563 (429 text + 134 binaries)**: **+1**, the single new [final closeout audit](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_CLOSEOUT.md). Counts use the four explicit root governance files (`CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `README.md`, `PR_RULES.md`) plus every tracked `docs/**` artifact; each path is counted once. Private/local untracked evidence is excluded.

The [DOC-R0 inventory](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.md) / [per-path JSON ledger](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.json) retain their **559 baseline / 562 including three outputs** census. The September 24 **379 / 380** census above used its dated tree/supporting-artifact selection. These are separate provenance records, not interchangeable totals. The [certified conflict matrix](audits/2026-10-03__DOCUMENTATION_AUTHORITY_CONFLICT_MATRIX.md) remains unchanged; final dispositions, historical links and the DOC-R0 → DOC-R1+R2 → DOC-R3+R4 → DOC-R6 chain are centralized in the new audit. Candidate readiness is not owner merge or exact-main certification.

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

**Dated snapshot — 2026-09-27 reconciliation (preserved):** The following facts describe that checkpoint; current dispositions are in §§2–2.3 and live CODEX, not inferred from these historical states.

- merged `main`: `51eab8648005186197d2fbb37a19bde4332aeaa5`, exact-head CI #485 SUCCESS;
- PR #32: MERGED/CLOSED by squash; source integration head `0ccc9c14aba520d2f6ae405129018e5d5ec26cb2` is historical branch evidence only;
- OS-G0 Fluent 2 engineering closeout: complete on merged main;
- Local immutable storage: G6 accepted;
- OneDrive Exchange: G8 offline complete at code milestone `f896f15...`;
- Working Change Observation: design/ADR accepted; the full ADR 0045 observation/candidate runtime is not implied complete by OS-G0;
- canonical Case State stages 5–16: not yet product-complete;
- OS-G1: G1.0 current-result gate merged by PR #51 (`7db69708…`, exact-head CI #491 SUCCESS); ADR 0046 is accepted G1.1 design authority; G1.1 runtime not started and requires an explicit Product Owner task;
- OS-G2: not started;
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

The 2026-09-21 documentation reconciliation audits are historical snapshots of their recorded branch/head/inventory. Their older roadmap labels, counts and implementation states do not override the 2026-09-24 status index, Unified Roadmap, current UI/UX authority or AI Master Plan.

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
- AI-PR-000 documentation reconciliation is **IMPLEMENTED / NO RUNTIME AUTHORIZATION**.
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

## 14. Historical Issue #89 encounter log — deferred at that checkpoint

**Current disposition — DOC-R6 / 2026-10-03:** The full 64-finding matrix is now dispositioned by certified Issue #94 (DOC-R1+R2), certified Issue #96 (DOC-R3+R4), and this Issue #98 candidate (DOC-R6); DOC-R5 was intentionally omitted. See the [final closeout audit](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_CLOSEOUT.md) for every owned finding, census and preserved historical-link disposition. Issue #90 remains owner-controlled pending final certification; the old log below is retained as evidence of Issue #89's checkpoint.

This is a bounded encounter log, not the repository-wide review. [Issue #90](https://github.com/Reguluspt/valora-engineering/issues/90) starts only after the architecture ADR is accepted/certified on main. Preserve historical exact-SHA claims and use live CODEX/task/CI for implementation. Six conflict groups were encountered during Issue #89's named reads:

| Group | Files / concept needing later reconciliation | Disposition |
|---|---|---|
| 1 | CODEX live-task prose still says A5 resumes; Issue #89 baseline says A5/ASSET_REVIEW certified/closed | Defer product-status reconciliation; no later stage authorized |
| 2 | ENGINEERING_GUARDRAILS, Unified Roadmap, this index and PROJECT_HANDOFF retain OS-G1/G1.1/OS-G2 not-started/current-baseline prose from earlier reconciliations | Defer status cleanup; dated SHA/CI evidence remains dated, not current certification |
| 3 | README incomplete Adaptive Intake/mapping UX claims predate G1.1K closure | Defer feature-status reconciliation |
| 4 | DOCUMENTATION_STATUS_INDEX inventory/count and docs/index active OS-G0 remediation wording reflect 2026-09-24 state | Defer full-tree recount/lifecycle classification |
| 5 | DESIGN_AUTHORITY_INDEX ADR 0046/0047 rows still describe partial/pending G1.1/F0 and blocked G1.1H | Defer domain-status reconciliation; preserve accepted semantic contracts |
| 6 | AI Master Plan opening OS-G0 integration/current four-prefix-provider snapshot predates later product slices | Defer stale repository-state prose; OS-G7/provider gates unchanged |

Historical audits/handoffs/sprint/research/exact-SHA evidence were not modified. This log grants no runtime, deployment or repository-wide cleanup authority.
