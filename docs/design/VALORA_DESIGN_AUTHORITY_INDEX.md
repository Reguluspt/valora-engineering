# Valora Design Authority Index

**Status:** Canonical reading order and conflict-resolution index
**Reconciled:** 2026-09-21 (G8 offline Exchange complete on Draft PR #32; ADR 0045 + Working Change Observation design authority accepted)
**Purpose:** Prevent older roadmap or provisional text from overriding newer owner-approved decisions.
**Documentation lifecycle:** `docs/DOCUMENTATION_STATUS_INDEX.md`.
**v2.3 gate:** PR-00 — **CLOSED**; PR-01 / PR-02 / PR-03 / PR-04 contracts — **ACCEPTED** and merged.

## 1. Read order

Product/UX/business semantics and visual authority are governed by `VALORA_UIUX_HANDOFF_v2.3.md`, `VALORA_UIUX_V2_3_AUTHORITY_INDEX.md` and directly relevant v2.3 addenda. Development ordering / architecture integration is governed by `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`. `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` details OS-G7 architecture and AI-readable-by-design constraints but does not activate AI runtime. An explicit current Product Owner decision wins only in the scope it names.

1. Explicit current Product Owner decision — wins only in the scope it names.
2. `CODEX.md` — live task gate and agent operating rules.
3. `ENGINEERING_GUARDRAILS.md` — permanent security, tenant, audit and mutation invariants.
4. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical UI/UX master.
5. `VALORA_UIUX_V2_3_AUTHORITY_INDEX.md` — v2.3 reading order and scope.
6. The current v2.3 addendum directly governing the assigned scope.
7. `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md` — current development sequencing / architecture integration.
8. `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` — OS-G7 / AI-readiness architecture detail; never runtime authorization by itself.
9. Accepted scoped ADR governing the assigned boundary.
10. Current task / implementation contract, including `docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md` where applicable.
11. `docs/VALORA_PROJECT_HANDOFF.md` and current acceptance evidence.
12. Design Book v1.2-final plus v1.3/v1.4, sprint, audit, remediation and research material — historical/domain evidence where not superseded.

This file is a supersession/navigation map for the authority above; it does not create a higher
authority tier of its own.

When two sources conflict, the newer explicit decision governs only the scope it names. Security, tenant isolation, immutable evidence, append-only decisions and human approval remain cumulative unless an accepted ADR explicitly supersedes them.

## 2. Version relationship

| Authority | Continues to govern | Superseded or extended by later authority |
|---|---|---|
| UI/UX Handoff v2.3 + v2.3 Authority Index | North-star flow, single-user UX, stage/state vocabulary, NCC, M365, Publishing and audit/lineage UI semantics | Newer explicit v2.3 addendum wins only in its named scope |
| Design Book v1.2-final | Core domain architecture, canonical assets, evidence/knowledge, workflow and document boundaries | Extended, not replaced, by v1.3/v1.4 |
| Design Book v1.3 | Historical MVP/domain/provider/AI foundation | **Astryx visual-system authority is superseded by UI/UX Handoff v2.3 Microsoft Fluent 2 light**; roadmap sequencing is superseded by the Unified Roadmap v2.3 |
| Design Book v1.4 | Adaptive workbook intake, Column Mapping Memory, Asset Identity Memory, historical dossier bootstrap, row alignment and feedback | Does **not** silently change S12 Apply v1 |
| Excel staging contract §15 / ADR 0029 | S12 Apply command and `s12-pr-004-v1` semantics (implemented/merged) | A future Apply change requires a new version and ADR |
| ADR 0014 | Historical deterministic candidate-generation rationale | Automated batch approval wording is superseded by **ADR 0031** |
| ADR 0030 | Column Mapping Memory and Adaptive Workbook Intake | Historical implementation foundation; current product placement is under `OS-G1` Pre-case/intake slices where required, not an S13 sequencing gate |
| ADR 0031 | Asset Identity Memory and human-confirmed feedback | Historical implementation foundation; current product placement is under `OS-G2` Asset Review/Workbench where required, not an S14 sequencing gate |
| ADR 0032 | Paired dossier aggregate, extraction and row alignment | Historical/domain foundation; activate only when a current Unified Roadmap slice requires it, not through the old S15 sequencing gate |
| ADR 0033 | Audited AI task runs, Decision Episodes and learning evidence | Domain provenance foundation remains valid; provider-backed AI runtime/learning expansion belongs to `OS-G7`. Earlier OS-G5 work may define UX/task contracts or deterministic candidate logic, but provider/model execution requires the AI Master Plan gate unless separately and explicitly authorized |
| ADR 0034 | Risk-tiered Execution Policy and reliable autonomous commands | Defines extension point only; no autonomous capability is promoted by historical S13–S16. Controlled automation belongs to `OS-G7` unless separately authorized earlier |
| ADR 0036 | Computed Global Case State projection | Accepted foundation; PR-01 computed-on-read runtime is implemented and accepted; resume persistence remains deferred |
| ADR 0037 | Durable Official Intake commit | Accepted foundation; the durable official-intake fact and command feed the implemented PR-01 provider |
| ADR 0045 | Working-copy change observation and human-confirmed document revision | Automatic notification/delta/revalidation may create Change Candidates and recommendations; authoritative business mutation and Revision N+1 require explicit human-confirmed commit. Supersedes ADR 0044 only for immediate DOCX Working re-import promotion semantics. |

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
S13-PR-002 closed evidence:
  main 137f8c527422b656974e569c924dafa8150b8b22 (PR #15); CI 29641452155 PASS
S13-PR-003 closed evidence:
  main 2af753520ab6b7885555adc5b7945a28d32ee311 (PR #17); CI 29676915010 PASS
Current UI/UX integration evidence:
  PR-00 through PR-04 merged by PR #29 at 2775cb9a96a8067be3e558a84c96bb69566859cb
  PR-05 merged by PR #30 at 42a87fca1a90f5b94724a4ca0d7a83fa5dec1699
  PR-06 merged by PR #31 at 27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6
  Per-layer truth: docs/implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md
```


Agents must `git fetch origin` and verify live `origin/main`. Do **not** treat historical feature SHAs (`259ee59…`) or historical `main` (`32024be…` / `a9f2c1e…` alone) as current status when a newer accepted main exists.

## 4. Active roadmap

```text
Accepted merged baseline: origin/main 27d1cc6… (PR #31)
Active integration candidate: Draft PR #32 / `feat/operational-frontend-m365` at reconciliation head `d725bbc6…` after F2-PR-001…003 merged on that branch; CI #454 SUCCESS; not merged to main
G6 Local immutable storage: ACCEPTED
G8 OneDrive Personal Exchange offline implementation: COMPLETE at f896f15…
ADR 0045 / Working Change Observation design authority: ACCEPTED

Current product direction:
Authority cleanup
→ complete Pre-case product journey
→ close ASSET_REVIEW → APPRAISAL_RESULT as vertical OS slices
→ Document Workspace with automatic observation/revalidation + Change Candidate + Human Commit
→ Release/Publishing
→ traceability/state/fidelity/E2E
→ Valora Intelligence Platform & Assistant (OS-G7)

Original direct OneDrive replacement PR-07 write path: BLOCKED/HISTORICAL.
Protected Old/V/W and explicit conflict semantics remain reusable.
New document-change runtime is gated by an ADR-0045 implementation contract; webhook/subscription/
delta runtime is not authorized by ADR 0045 alone.

G9 live AppFolder conformance: separate Product Owner gate; not automatically opened by G8.
Historical PR-08 through PR-13 capability labels remain not product-complete; current closure ordering is `OS-G0 → OS-G7`.
Windows Preview: only after Software Completion.
```

Infrastructure expansion is not a roadmap goal by itself. New storage/provider/Graph abstractions are
justified only when a concrete North-star slice cannot safely close without them.

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
- Historical S13–S16 scope did not promote R2 auto-draft/auto-stage. Any future promotion follows the current `OS-G7` controlled-AI boundary and still requires task-specific design, shadow evaluation and owner-approved release.
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

Historical S13 runtime gate record:

1. Separate explicit owner assignment of a runtime task ID.
2. Runtime work must branch from the then-current accepted `origin/main`.
3. Follow PR order in `docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md`.

S13-PR-002 through S13-PR-004 are implemented historical foundation. This record does not
authorize S13-PR-005 or override the current Unified Roadmap `OS-G0 → OS-G7`. Historical PR-00→PR-13 labels remain acceptance/evidence references only.

Current v2.3 disposition:

1. PR-00 through PR-04 — merged bounded foundations/slices.
2. PR-05 / PR-06 — merged OneDrive Personal read/revalidation foundations.
3. Draft PR #32 — operational frontend candidate + accepted Local G6 + completed G8 offline Exchange.
4. ADR 0045 — accepted target semantics for automatic Working observation, Change Candidate and
   explicit human-confirmed Revision N+1.
5. Canonical stages 5-16 remain incomplete at OS/product level; Case State provider still only owns
   the four prefix stages.
6. PR-07 direct OneDrive replacement execution is historical/blocked; new document-change runtime
   requires the ADR-0045 implementation contract.
7. Historical PR-08 through PR-13 capability gaps remain open, but they must be closed in the current Unified Roadmap order `OS-G0 → OS-G7`, not by restoring the old PR sequence.


## 7. Module ownership (future runtime)

| Module | Future ownership |
|---|---|
| `excel_import` | Adaptive Intake, workbook adapters, Column Mapping Memory |
| `taxonomy_asset_identity` | Raw Asset Observation integration, contextual aliases, identity candidates/decisions |
| `document_engine_intelligence` | Dossier source roles, extraction, table roles, row alignment |
| `knowledge_evidence` | Reviewed quote/spec/knowledge candidates and activation |
| `ai_governance_security` | Task registry, context-manifest governance, provider gateway, AI-task provenance and deterministic Execution Policy boundary |
| Worker / reliable task runtime | Durable job/outbox execution, attempts, lease/retry/timeout/cancellation and stale-generation rejection |
| Workbench / frontend | Vietnamese Microsoft Fluent 2 light review surfaces; desktop-first, data-heavy/table-first |

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
