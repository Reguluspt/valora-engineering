# DOC-R0 Documentation Authority Conflict Matrix and Proposed Batches

**Status:** Diagnostic candidate; Issue #92 / parent Issue #90. No remediation executed.
**Date:** 2026-10-03

Baseline `e2e03f3a91e21e366af72e35beeeab73ed18cfdb` / CODEX `756c51ed743868ed9658c336658ebebf67762cea` / CI #559 SUCCESS. [Inventory](2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.md) and [complete per-artifact JSON ledger](2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.json) define the scope.

## Findings and severity

| Severity | Material audit findings |
| --- | --- |
| P0 | 0 |
| P1 | 3 |
| P2 | 40 |
| P3 | 21 |

64 findings: 60 repository findings (one historical-link group lists every affected path), plus4 external historical GitHub records. Semantics change: **NO for every finding**. New semantic Product Owner decisions: **0 / NONE**. P0 means unsafe contradictory authority, P1 means materially misleading current execution/availability gate, P2 means current status/scoped-authority/navigation drift, P3 means lifecycle/metadata/historical-navigation clarity. These are **deferred source-document findings**, not unresolved material review defects in DOC-R0. No later-stage runtime/deployment permission is created.

## Material findings

### R0-001 — A5 presented as resumed active

Path: [CODEX.md](../../CODEX.md) (line 4).

Evidence: **Last reconciled:** 2026-10-02 (A5R2 certified; A5 product closure resumed)

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P1**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Add the certified A5 closure disposition and current stage cap; remove resumed-active assignment language only from living status.

### R0-002 — Four-stage availability assertion

Path: [CODEX.md](../../CODEX.md) (line 57).

Evidence: canonical stages 5-16 are still unavailable until their domain facts/providers are implemented.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Reconcile current availability through ASSET_REVIEW; preserve PR-01 four-stage milestone as dated evidence.

### R0-003 — Generic draft wording omits accepted status-command successor

Path: [CODEX.md](../../CODEX.md) (line 226).

Evidence: ADR 0028 restricted Workbench fields (description, appraised_unit_price, review_status, validation_status) require draft-commit command path + authorization

Current governing authority: Explicit accepted ADR 0049 D1-D6 / line decision contract; A4/A5 certification Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated. ADR 0028 remains binding for value drafts and direct status PATCH prohibition.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: State the scoped dedicated validation/review successor alongside retained value-draft and no-direct-PATCH constraints; do not weaken any human/tenant/CAS/audit gate.

### R0-004 — G1.1 and OS-G2 presented as unstarted

Path: [ENGINEERING_GUARDRAILS.md](../../ENGINEERING_GUARDRAILS.md) (line 58).

Evidence: G1.0 current-result integrity gate is merged by PR #51 at `7db69708b4668b77f49c97ec59b195be2b0f6037` (CI #491 SUCCESS). ADR 0046 is the accepted G1.1 design for optional Pre-case Customer, explicit current batch and immutable versioned analysis/results. It does not authorize runtime changes; G1.1 runtime and OS-G2 remain not started. Preserve tenant/Project lineage, explicit human binding, immutable history and G1.0's fail-closed Official Intake gate in later slices.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Add current certified Pre-case/ASSET_REVIEW disposition; preserve dated early milestone SHAs.

### R0-005 — Stage 5 included in all downstream incomplete assertion

Path: [ENGINEERING_GUARDRAILS.md](../../ENGINEERING_GUARDRAILS.md) (line 59).

Evidence: The original PR-07 direct OneDrive replacement execution is historical/blocked. Protected-value and Old/V/W conflict semantics remain reusable. New Working-copy change runtime must follow ADR 0045 and a task-specific implementation contract before coding. Release/Publishing and canonical stages 5–16 remain incomplete.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Distinguish closed ASSET_REVIEW from stages 6-16 and incomplete full OS-G2.

### R0-006 — Draft route wording lacks scoped status-command ratchet

Path: [ENGINEERING_GUARDRAILS.md](../../ENGINEERING_GUARDRAILS.md) (line 234).

Evidence: These fields must **not** be mutated via direct PATCH. They require the draft-commit command path:

Current governing authority: Explicit accepted ADR 0049 D1-D6 / line decision contract; A4/A5 certification Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated. ADR 0028 remains binding for value drafts and direct status PATCH prohibition.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Document accepted dedicated status commands without changing value-draft or direct-PATCH boundaries.

### R0-007 — Next phase incorrectly unopened

Path: [README.md](../../README.md) (line 14).

Evidence: **Current execution direction:** **OS-G0 is merged-main complete; OS-G1 Pre-case Product Closure is the next roadmap phase but remains unopened until an explicit Product Owner task**

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Reconcile phase/status rows, downstream stage wording and live task gate against closed Pre-case/Asset Review; full OS-G2 and production remain incomplete.

### R0-008 — Undated live task gate pins old OS-G0 baseline

Path: [README.md](../../README.md) (line 48).

Evidence: Accepted code baseline: origin/main `51eab8648005186197d2fbb37a19bde4332aeaa5` (squash PR #32; exact-head CI #485 SUCCESS).

Current governing authority: Issue #92 verified live baseline e2e03f3a91e21e366af72e35beeeab73ed18cfdb, CODEX blob 756c51ed743868ed9658c336658ebebf67762cea, CI #559 SUCCESS; CODEX requires fresh fetch and exact-SHA verification.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Keep top not-evergreen PR32 record; label the old task-gate snapshot as dated and point to fresh exact-head verification.

### R0-009 — Product mapping completion still denied

Path: [README.md](../../README.md) (line 146).

Evidence: - Current product-facing Adaptive Intake / mapping-confirmation UX completion (the historical workbook adapter and structure-discovery foundations already exist)

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Distinguish certified G1.1H/K bounded journey from future provider AI matching/dossier and broader identity work.

### R0-010 — Mutation summary lists only historical Apply/draft authority

Path: [README.md](../../README.md) (line 90).

Evidence: - **ADR 0028** restricted Workbench fields require draft-commit + atomic audit.

Current governing authority: Explicit accepted ADR 0049 D1-D6 / line decision contract; A4/A5 certification Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated. ADR 0028 remains binding for value drafts and direct status PATCH prohibition. Accepted ADR0048 D1/D7 freezes v1 history and guards current successor.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R1**.

Recommended remediation: Add versioned current Apply v2 and dedicated line-status command pointers; never rewrite frozen v1 contract as v2.

### R0-011 — Current main labels old OS-G0 SHA

Path: [docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md](../../docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md) (line 75).

Evidence: `origin/main` accepted merged baseline is currently

Current governing authority: Issue #92 verified live baseline e2e03f3a91e21e366af72e35beeeab73ed18cfdb, CODEX blob 756c51ed743868ed9658c336658ebebf67762cea, CI #559 SUCCESS; CODEX requires fresh fetch and exact-SHA verification.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R2**.

Recommended remediation: Keep dated header/OS-G0 milestone; reconcile undated section3 and current OS-G1 narrative to certified closure.

### R0-012 — Current OS-G1 narrative unstarted

Path: [docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md](../../docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md) (line 284).

Evidence: the first commit. G1.1 runtime is not started; the ADR alone does not implement this journey.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R2**.

Recommended remediation: Add certified OS-G1/ASSET_REVIEW slice disposition and remaining OS-G2 hold; retain OS-G0→OS-G7 ordering.

### R0-013 — Unqualified integration and four-provider snapshot

Path: [docs/architecture/VALORA_AI_MASTER_PLAN_V1.md](../../docs/architecture/VALORA_AI_MASTER_PLAN_V1.md) (line 130).

Evidence: Assistant không tự suy diễn lifecycle state từ hội thoại. Nó đọc Global Case State và authoritative projections. Hiện exact-head mới có provider cho bốn stage đầu; stages 5–16 phải được đóng theo roadmap trước khi AI reasoning end-to-end trên toàn hồ sơ.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated. AI Master Plan §§20-22 retains OS-G7/provider gate.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R2**.

Recommended remediation: Label sections2/6 as dated integration evidence and add current five-stage checkpoint; retain every AI activation gate.

### R0-014 — Deployment ADR certification still pending

Path: [docs/DOCUMENTATION_STATUS_INDEX.md](../../docs/DOCUMENTATION_STATUS_INDEX.md) (line 81).

Evidence: - &#91;ADR 0050&#93;(adr/0050-linux-server-windows-native-client.md) — accepted Product Owner deployment/client decision; repository certification pending. Linux single-node Server + HTTPS LAN + WinUI 3/WebView2 + server-hosted React/Fluent 2 light + typed native bridge + MSIX. Server retains business/auth/tenant/document/job authority; no local LLM/model-weight/GPU dependency, core workflow AI dependency NONE; provider-backed AI stays OS-G7 gated.

Current governing authority: ADR 0050 D1-D10; PR #91 MERGED at e2e03f3a91e21e366af72e35beeeab73ed18cfdb; exact-main CI #559 / run 37111129209 SUCCESS; Issue #89 CLOSED/CERTIFIED.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Reconcile documentation certification only; Windows/server runtime and deployment remain unassigned.

### R0-015 — Latest inventory navigation points to dated 380-artifact census

Path: [docs/DOCUMENTATION_STATUS_INDEX.md](../../docs/DOCUMENTATION_STATUS_INDEX.md) (line 6).

Evidence: **Inventory reconciliation:** 380 documentation/config-document artifacts after the 2026-09-24 reconciliation closeout: 369 Markdown files + 11 supporting documentation artifacts (8 JSON/config evidence files + 3 approved design JPG assets) across the root governance set and `docs/**`. The pre-closeout audited source tree at `6a964112…` contained 379 artifacts; the additional artifact is the final reconciliation audit itself.

Current governing authority: Issue #92 verified live baseline e2e03f3a91e21e366af72e35beeeab73ed18cfdb, CODEX blob 756c51ed743868ed9658c336658ebebf67762cea, CI #559 SUCCESS; CODEX requires fresh fetch and exact-SHA verification. This DOC-R0 inventory: 559 baseline artifacts, including 425 text and134 supporting binaries; 562 with three outputs.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Retain §2.2 as dated September24 evidence; link this exact census with explicit scope and count provenance, not rewrite historical counts.

### R0-016 — Current Pre-case and accepted ADR map incomplete

Path: [docs/DOCUMENTATION_STATUS_INDEX.md](../../docs/DOCUMENTATION_STATUS_INDEX.md) (line 60).

Evidence: 0037 and 0038 in that scope; G1.1 runtime remains separately gated.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated. ADR 0050 D1-D10; PR #91 MERGED at e2e03f3a91e21e366af72e35beeeab73ed18cfdb; exact-main CI #559 / run 37111129209 SUCCESS; Issue #89 CLOSED/CERTIFIED.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Add current dispositions/links for ADR0047-0050 and certified G1/G2 slices; retain dated §3 snapshot and partially superseded foundations.

### R0-017 — Closed OS-G0 packet called active

Path: [docs/index.md](../../docs/index.md) (line 16).

Evidence: - &#91;VALORA-FLUENT2-REMEDIATION-001&#93;(implementation/VALORA-FLUENT2-REMEDIATION-001.md) — active OS-G0 implementation contract and F2-PR-001…008 delivery sequence; detailed task-ready packets are `VALORA-FLUENT2-F2-PR-001_IMPLEMENTATION_PLAN.md` through `...008...` in `docs/implementation/`.

Current governing authority: CODEX.md and VALORA-FLUENT2-REMEDIATION-001 status: PR32/F2-PR001-008 merged/closed; current OS-G1/G2 checkpoints.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Classify completed remediation navigation as history; add current G1/G2/ADR0048-49 and DOC-R0 entry points.

### R0-018 — Historical supplement contains misleading current successor note

Path: [docs/VALORA_PROJECT_HANDOFF.md](../../docs/VALORA_PROJECT_HANDOFF.md) (line 16).

Evidence: > OS-G1 authority work is active; G1.1 runtime and OS-G2 are not started. Each runtime slice

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R4**.

Recommended remediation: Add its later disposition centrally or outside frozen snapshot; preserve historical handoff body and September27 statement.

### R0-019 — Onboarding mutation vocabulary misses status-command ratchet

Path: [docs/VALORA_PROJECT_HANDOFF.md](../../docs/VALORA_PROJECT_HANDOFF.md) (line 117).

Evidence: Official changes go through draft → human confirmation → `commit_asset_line_draft` with atomic audit. Direct PATCH of those four fields is rejected.

Current governing authority: Explicit accepted ADR 0049 D1-D6 / line decision contract; A4/A5 certification Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated. ADR 0028 remains binding for value drafts and direct status PATCH prohibition.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R4**.

Recommended remediation: Clarify successor in current onboarding navigation outside preserved historical body; no historic fact rewrite.

### R0-020 — ADR status leaves original prefix fact-mapping gate open

Path: [docs/adr/0036-computed-global-case-state-projection.md](../../docs/adr/0036-computed-global-case-state-projection.md) (line 3).

Evidence: **Status:** Accepted for architecture; fact-mapping gate remains open

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add implementation disposition limited to five-stage approved providers; later predicates remain fail-closed. Preserve original decision/body.

### R0-021 — ADR metadata remains local-only closeout

Path: [docs/adr/0037-durable-official-intake-commit.md](../../docs/adr/0037-durable-official-intake-commit.md) (line 3).

Evidence: **Status:** Accepted — PR-01a authority closeout complete locally

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. ADR0046/0047 and implemented Official Intake successor.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Record certified implementation disposition externally/in status metadata while preserving local exact-SHA record.

### R0-022 — Accepted prefix ADR still claims all runtime absent

Path: [docs/adr/0038-bounded-preliminary-prefix-predicates.md](../../docs/adr/0038-bounded-preliminary-prefix-predicates.md) (line 3).

Evidence: **Status:** Accepted for design authority — source facts, providers and runtime remain unimplemented

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add current implemented/successor disposition to metadata/index; preserve original design exit checklist and decision facts.

### R0-023 — Accepted Pre-case ADR status unstarted

Path: [docs/adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md](../../docs/adr/0046-precase-identity-current-batch-and-versioned-result-lifecycle.md) (line 3).

Evidence: **Status:** Accepted design authority (Product Owner decisions D1–D3); G1.1 runtime not started

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Reconcile status/successor metadata to certified Pre-case closure, preserving accepted D1-D3 and original migration proposal.

### R0-024 — Mapping ADR status pending F0 candidate

Path: [docs/adr/0047-authoritative-column-mapping-selection-and-recovery.md](../../docs/adr/0047-authoritative-column-mapping-selection-and-recovery.md) (line 3).

Evidence: **Status:** Accepted by Product Owner on 2026-09-29; runtime implementation in F0 candidate pending merge

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS. CODEX F0 PR62 CI514 and G1.1H PR63 CI516 certified.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Reconcile F0/H implementation disposition only; preserve selection/CAS/legacy-recovery semantics.

### R0-025 — Apply successor ADR undated runtime absence

Path: [docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md](../../docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md) (line 5).

Evidence: **ACCEPTED PRODUCT OWNER AUTHORITY — 2026-10-02.** Task `VALORA-TASK-OS-G2-A1-ENTRY-GUARD-CASESTATE-AUTHORITY-RATCHET`, &#91;Issue #73&#93;(https://github.com/Reguluspt/valora-engineering/issues/73). Baseline `main=a293395c53ab12aa27cac86d82046a6a9f59983b`, exact-main CI #533 SUCCESS; 2026-10-02. The Product Owner accepted OS-G2 A1 in this task chat on 2026-10-02, accepting this ADR and the &#91;Case State contract&#93;(../implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) as successor authority. Runtime remains unimplemented and UNAUTHORIZED; acceptance does not authorize implementation, capability activation or merge.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add certified A2/A4/A5 implementation disposition; retain original proposal/acceptance quote and frozen v1 boundary.

### R0-026 — ADR scoped token/status notes omit implemented A4 successor

Path: [docs/adr/0049-asset-line-human-review-and-validation-authority.md](../../docs/adr/0049-asset-line-human-review-and-validation-authority.md) (line 59).

Evidence: The accepted versioned token successor is `global-case-state-v3-asset-review-line-decision-v1` at a separately authorized activation, retaining all A2 inputs and adding line input/reference/rule digests and validation/review generation identity. This authority does not change the live v2 token. Line row-version increments also invalidate Case State on every committed new generation; no identical-verdict token reuse.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add A4/A5 implementation disposition outside original proposal body. Acceptance-alone != activation remains correct; do not remove it.

### R0-027 — Accepted architecture metadata certification pending

Path: [docs/adr/0050-linux-server-windows-native-client.md](../../docs/adr/0050-linux-server-windows-native-client.md) (line 3).

Evidence: **Status:** ACCEPTED PRODUCT OWNER ARCHITECTURE DECISION — Issue #89; repository certification pending

Current governing authority: ADR 0050 D1-D10; PR #91 MERGED at e2e03f3a91e21e366af72e35beeeab73ed18cfdb; exact-main CI #559 / run 37111129209 SUCCESS; Issue #89 CLOSED/CERTIFIED.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Record repository certification on main; preserve all implementation/deployment holds and accepted D1-D10.

### R0-028 — a0 runtime pending

Path: [docs/plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md](../../docs/plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md) (line 3).

Evidence: **Status:** ACCEPTED PRODUCT OWNER AUTHORITY for the decisions in the accepted-decision section below. Their runtime enforcement remains unimplemented. Other candidate predicates and route examples are not accepted authority. **Baseline:** `main` at `81b5366d580681a768daaee6b7cacb54d1a8cc5e`, exact-main CI #530 SUCCESS. **Scope:** Official Intake → first official `ProjectAssetLine` set → `ASSET_REVIEW`; later OS-G2 stages are outside this record.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R4**.

Recommended remediation: Add A2/A4/A5 successor disposition while retaining verbatim accepted decisions and historical proposal implementation gap.

### R0-029 — a5r2 grant pending

Path: [docs/plan/VALORA_OS_G2_A5_WORKBENCH_SESSION_RBAC_AUTHORITY_PROPOSAL.md](../../docs/plan/VALORA_OS_G2_A5_WORKBENCH_SESSION_RBAC_AUTHORITY_PROPOSAL.md) (line 88).

Evidence: Product Owner acceptance freezes the bounded policy only. The grant is NOT YET IMPLEMENTED / NOT YET CERTIFIED. A separately authorized runtime task must implement and certify the future data-only migration, preserving unrelated grants and pre-existing accepted grants, with durable grant provenance and safe downgrade. This proposal creates no migration and changes no RBAC record, backend authentication, API, frontend, runtime or test behavior. No A5 worktree changes or browser E2E were performed; acceptance alone does not certify A5 or authorize ASSET_WORKBENCH+.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R4**.

Recommended remediation: Add A5R2 PR #85/CI #552 grant certification and A5 PR #86 closure disposition; preserve historical baseline graph and no broader grants.

### R0-030 — a1 runtime unimplemented

Path: [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) (line 3).

Evidence: **Status:** ACCEPTED PRODUCT OWNER AUTHORITY — 2026-10-02 with &#91;ADR 0048&#93;(../adr/0048-post-intake-guarded-apply-and-asset-review-authority.md). **Task:** OS-G2 A1 / &#91;Issue #73&#93;(https://github.com/Reguluspt/valora-engineering/issues/73). **Baseline:** `a293395c53ab12aa27cac86d82046a6a9f59983b`, exact-main CI #533 SUCCESS; 2026-10-02. The Product Owner accepted OS-G2 A1 in this task chat; the verbatim decision is recorded in ADR 0048. Runtime remains unimplemented and UNAUTHORIZED; implementation must not begin without a separate explicit authorization.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add certified A2/A4/A5 successor disposition and scoped implemented boundary; preserve accepted A1 five-state semantics and separate assignment rule.

### R0-031 — a1 provider unavailable

Path: [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) (line 9).

Evidence: Accepted provider identity `asset_review_v1`; capability available only after the accepted contract/ADR is implemented and wired through separately authorized runtime. Until then retain current &#91;provider&#93;(../../backend/app/modules/project_master_data/application/case_state_projection.py): `ASSET_REVIEW=NOT_AVAILABLE`, four-stage bound, no authorized downstream action after the completed prefix (existing scoped blockers still take global priority). Merely merging authority does not activate a provider.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Qualify as pre-A2 state and reference certified current Asset Review provider; do not activate any later provider.

### R0-032 — a1 action schema stale

Path: [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) (line 39).

Evidence: All action contexts have typed `project_id:UUID`, `case_version:SHA256` and a safe `reason_code` enum, plus only the branch-specific fields below. Semantic keys are domain routing identifiers, not frontend URLs or commands; provider output never executes a mutation. These are accepted authority descriptors, not claims that today's public response exposes typed target context. The current action schema has only kind/stage/key/issue ID; a separately authorized API task must expose the accepted discriminated contexts without changing the existing enums.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add successor/current response disposition, preserve historical wire-schema note.

### R0-033 — a3 commands unimplemented

Path: [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md) (line 9).

Evidence: Current &#91;Human Commit&#93;(../../backend/app/modules/project_master_data/commands/commit_asset_line_draft.py) remains the value-edit authority for description/appraised unit price. The &#91;S11 audit&#93;(../audits/S11_PR_006_HUMAN_COMMIT_REVIEW_GATE_AUDIT.md#4-commit-field-allowlist) and &#91;live API contract §§12–13&#93;(../design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md#13-s11-pr-006-human-commit--review-gate) do not prove status commands exist. The &#91;A2 provider&#93;(../../backend/app/modules/project_master_data/application/asset_review_provider.py) is current runtime; the accepted successor commands remain unimplemented. Historical broad remediation wording has no greater authority.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add A4 certified implementation and A5 closure note; preserve exact proof/decision/replay/negative-hold semantics.

### R0-034 — a3 route keys not live

Path: [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md) (line 94).

Evidence: Current A2 `asset_review_line_pending` combines two different missing authorities; it is insufficient as the successor's actionable routing identifier. The two accepted keys are authority only, not live. Preserve current_stage at ASSET_REVIEW once the four prefix stages complete; no ASSET_WORKBENCH+ activation or Project workflow transition.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Record A4 API/provider plus A5 UI routing implementation; keep ASSET_WORKBENCH+ unavailable.

### R0-035 — pr00 retired routes remaining

Path: [docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md) (line 59).

Evidence: The following pre-v2.3 surfaces remain unchanged and are debt, not approved north-star behavior:

Current governing authority: CODEX OS-G0/F2-PR001-008 closed through PR32/CI485; Fluent2 light remains current authority.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Mark old route inventory historical and F2-PR-001 closure supersession; preserve backend and still-enforced semantic ratchets.

### R0-036 — pr01 asset review unmapped

Path: [docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md) (line 62).

Evidence: /  `ASSET_REVIEW`  /  mandatory asset-review predicates  /  asset-line review/validation facts exist; completeness predicate not approved  /  UNMAPPED  /

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Preserve original PR01 foundation table as historical and add ADR0048/49 plus A2/A4/A5 successor disposition.

### R0-037 — pr01 multiplicity current claim

Path: [docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md) (line 8).

Evidence: > **2026-09-27 scoped successor:** C2's batch/snapshot/artifact multiplicity → `NOT_AVAILABLE` is the implemented PR-01 v1 rule. ADR 0046 accepts a future explicit current-batch pointer and highest-valid-lineage version rule: valid historical rows alone will no longer be ambiguous. Actual duplicate current claims/corrupt lineage still fail closed. G1.1 runtime is not started; this contract remains accurate for current code.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Qualify v1/C2 as historical; cite implemented ADR0046/47 pointer/version/current-mapping successor and ADR0048/49 Stage5; preserve old envelope/fixtures.

### R0-038 — pr01 intake successor future

Path: [docs/implementation/VALORA_UIUX_V2_3_PR01_OFFICIAL_INTAKE_COMMIT_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_OFFICIAL_INTAKE_COMMIT_CONTRACT.md) (line 8).

Evidence: > **2026-09-27 scoped successor:** ADR 0046 requires explicit ACTIVE same-tenant Project Customer binding before first commit and freezes the exact current applicable result, even if that result was generated while unbound and carries historical `customer_id=NULL`. The same Project and atomic/idempotent commit remain. This is a future G1.1 contract delta; current runtime and this historical implementation record are unchanged.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Record G1.1E/K implementation disposition; retain original bounded v1 command/history.

### R0-039 — pr01 analysis successor future

Path: [docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_ANALYSIS_SNAPSHOT_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_ANALYSIS_SNAPSHOT_CONTRACT.md) (line 7).

Evidence: > **2026-09-27 scoped successor:** The non-NULL Customer and one-snapshot-per-Project assumptions below describe implemented v1. ADR 0046 accepts nullable historical Customer snapshot metadata and immutable versioned successors selected by current batch/source/materialized mapping usage. No schema or generator change is made by this note; G1.1 runtime remains not started.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add implemented G1.1C/K disposition; preserve historical original v1 schema and uniqueness statements.

### R0-040 — pr01 result successor future

Path: [docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_RESULT_GENERATION_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_RESULT_GENERATION_CONTRACT.md) (line 7).

Evidence: > **2026-09-27 scoped successor:** The one-artifact-per-Project and non-NULL Customer assumptions below describe implemented v1. ADR 0046 accepts immutable versioned regeneration before Official Intake and nullable historical Customer snapshot metadata; the current result is the highest valid version matching the selected current analysis. This note authorizes no generator/schema change; G1.1 runtime remains not started.

Current governing authority: CODEX.md G1.1K checkpoint; OS-G1 closed by PR #68, d283c690b9f014833fa5c98e1125939351966b81, exact-main CI #527 SUCCESS.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add implemented G1.1D/K disposition preserving original v1 generator historical body.

### R0-041 — pr02 active dark styling

Path: [docs/implementation/VALORA_UIUX_V2_3_PR02_CASE_OVERVIEW_FRONTEND_CONTRACT.md](../../docs/implementation/VALORA_UIUX_V2_3_PR02_CASE_OVERVIEW_FRONTEND_CONTRACT.md) (line 8).

Evidence: **2026-09-21 visual-authority amendment:** PR-02 functional semantics and Case State wiring remain accepted. Historical browser checks do not establish current visual acceptance because the active frontend uses superseded dark/Astryx styling. `Tổng quan hồ sơ` must conform to the approved S10/Orchestration Hub Microsoft Fluent 2 light baseline; screenshot/visual-regression acceptance is required during OS-G0 remediation.

Current governing authority: CODEX OS-G0/F2-PR001-008 closed through PR32/CI485; Fluent2 light remains current authority.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Mark September21 visual debt superseded by F2-PR-004/PR #32; retain immutable original browser limitation.

### R0-042 — broken aggregator anchor

Path: [docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md](../../docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) (line 7).

Evidence: The &#91;accepted A0 decisions&#93;(../plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md) bind initial-set lineage, post-Intake Apply, project-wide COMPLETE and the current downstream hold. This accepted contract extends &#91;PR-01 projection §§2–6&#93;(VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md) and &#91;provider current-stage/Next Action rules&#93;(VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md#6-aggregator--next-action) only through `ASSET_REVIEW`. Historical broader design vocabulary does not add public enums: the &#91;current schema&#93;(../../backend/app/modules/project_master_data/schemas.py) supports stage results `COMPLETE  /  INCOMPLETE  /  BLOCKED  /  STALE  /  NOT_AVAILABLE` and action kinds `BLOCKER  /  PENDING  /  UNAVAILABLE  /  NO_AUTHORIZED_DOWNSTREAM_ACTION`. Use those values only; business progress maps to `INCOMPLETE`.

Current governing authority: Target provider contract §6 heading: Aggregator & Next Action (D8); correct anchor #6-aggregator--next-action-d8.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Repair only the repository-relative anchor; preserve current-stage/Next Action semantics.

### R0-043 — missing explicit lifecycle status

Path: [docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md](../../docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) (line 1).

Evidence: # VALORA Compact Task Contract

Current governing authority: docs/DOCUMENTATION_STATUS_INDEX.md §9 explicit status rule; CODEX §1.0 execution/tooling policy.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R4**.

Recommended remediation: Add explicit current tooling/template status and role, without changing operating requirements or making tooling a product/runtime dependency.

### R0-044 — missing explicit lifecycle status

Path: [docs/plan/VALORA_LEAN_AGENT_PROTOCOL_V1.md](../../docs/plan/VALORA_LEAN_AGENT_PROTOCOL_V1.md) (line 1).

Evidence: # VALORA Lean Agent Protocol v1

Current governing authority: docs/DOCUMENTATION_STATUS_INDEX.md §9 explicit status rule; CODEX §1.0 execution/tooling policy.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R4**.

Recommended remediation: Add explicit current tooling/template status and role, without changing operating requirements or making tooling a product/runtime dependency.

### R0-045 — missing explicit lifecycle status

Path: [docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md](../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) (line 1).

Evidence: # Valora OpenViking Operating Profile v1

Current governing authority: docs/DOCUMENTATION_STATUS_INDEX.md §9 explicit status rule; CODEX §1.0 execution/tooling policy.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R4**.

Recommended remediation: Add explicit current tooling/template status and role, without changing operating requirements or making tooling a product/runtime dependency.

### R0-046 — Stale OS-G1 lifecycle gate

Path: [docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md](../../docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md) (line 54).

Evidence: /  ADR 0046  /  Optional Pre-case Customer, explicit current batch, immutable versioned analysis/result lifecycle  /  Accepted design only; ratchets ADR 0030/0037/0038 in named scope; G1.1A–G1.1G merged, remaining lifecycle runtime gated  /   /  ADR 0047  /  Explicit, versioned current Column Mapping selection and recovery for Pre-case  /  Accepted by Product Owner on 2026-09-29. F0 runtime implementation and public recovery GET are in a candidate PR pending merge and exact-main CI; G1.1H UI remains blocked.  /

Current governing authority: CODEX.md live task gate: F0 PR62 CI514, G1.1H PR63 CI516, OS-G1 certified/closed PR68 CI527; current task certified baseline.

Severity: **P1**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Reconcile dated ADR0046/0047 implementation dispositions to certified history without opening later runtime gates.

### R0-047 — Active roadmap calls PR32 the accepted merged baseline

Path: [docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md](../../docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md) (line 87).

Evidence: Accepted merged baseline: origin/main `51eab8648005186197d2fbb37a19bde4332aeaa5` (squash PR #32); exact-head CI #485 SUCCESS

Current governing authority: Exact verified current baseline e2e03f3a91e21e366af72e35beeeab73ed18cfdb CI559; CODEX says historical SHAs are dated evidence only.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Mark PR32/CI485 as dated OS-G0 closeout evidence; point readers to live verified task baseline rather than replacing all historical SHAs.

### R0-048 — Four-stage provider-only statement now false

Path: [docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md](../../docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md) (line 163).

Evidence: 5. Canonical stages 5-16 remain incomplete at OS/product level; Case State provider still only owns    the four prefix stages.

Current governing authority: Accepted ADR 0048/0049; A2 PR #76, A4 PR #80, A5R2 PR #85; A5 PR #86 MERGED at 9233429d43c99f7d22a3e87ba04c85ca7e3293f9; Issue #81 CLOSED 2026-10-03T04:15:17Z. ASSET_WORKBENCH+ remains gated.

Severity: **P1**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Reconcile current disposition to ASSET_REVIEW certified closed, retain downstream hold.

### R0-049 — Supersession index misses accepted Apply v2 and Asset Review successors

Path: [docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md](../../docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md) (line 55).

Evidence: /  ADR 0047  /  Explicit, versioned current Column Mapping selection and recovery for Pre-case  /  Accepted by Product Owner on 2026-09-29. F0 runtime implementation and public recovery GET are in a candidate PR pending merge and exact-main CI; G1.1H UI remains blocked.  /

Current governing authority: CODEX OS-G2 A1-A5 dispositions; ADR0048, ADR0049, accepted Case State/line decision contracts.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Add scoped navigation to ADR0048/0049 and current contracts; preserve ADR0029 Apply v1 frozen scope.

### R0-050 — Supplier-template baseline still allows XLSX

Path: [docs/design/assets/VALORA_TM01_BASELINE_v2.3.md](../../docs/design/assets/VALORA_TM01_BASELINE_v2.3.md) (line 60).

Evidence: - `XLSX` / `DOCX` có icon file tương ứng và hiển thị trực tiếp.

Current governing authority: Current TM04 addendum section A and Template Management section C: supplier quotation templates Word .docx only; old Excel TM03 historical.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Mark XLSX sample vocabulary as historical and link Word-only supplier-template authority.

### R0-051 — TM03/TM04 incorrectly remain unapproved

Path: [docs/design/assets/VALORA_TM01_BASELINE_v2.3.md](../../docs/design/assets/VALORA_TM01_BASELINE_v2.3.md) (line 96).

Evidence: TM03 và TM04 vẫn chưa có baseline authority cho tới khi người dùng duyệt rõ.

Current governing authority: Current TM04 baseline addendum sections A-D: TM01/TM03/TM04 already approved.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Replace stale approval wording with exact current baseline pointers.

### R0-052 — Literal master section reference no longer exists

Path: [docs/design/assets/VALORA_TM01_BASELINE_v2.3.md](../../docs/design/assets/VALORA_TM01_BASELINE_v2.3.md) (line 94).

Evidence: Khi có mâu thuẫn visual giữa mockup/iteration TM01 cũ và baseline này, **TM01 Iteration 1 + §11 của `VALORA_UIUX_HANDOFF_v2.3.md` là nguồn quyết định**.

Current governing authority: Current v2.3 master contains sections 0-7; TM04/current supplier baseline companion docs supply the current specific authority.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Replace nonexistent master section11 reference with current scoped addendum/baseline navigation.

### R0-053 — Current Word value labeled Document Revision

Path: [docs/design/VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md](../../docs/design/VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md) (line 74).

Evidence: Dữ liệu đang có trong Word (Document Revision)

Current governing authority: Master section1.4A and Working Change Observation addendum sections2-3 distinguish immutable accepted DocumentRevision from mutable Working observation W.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Clarify W/current Word observation separately from accepted revision baseline; preserve user comparison interaction.

### R0-054 — Conflict definition omits V/W semantic convergence exception

Path: [docs/design/VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md](../../docs/design/VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md) (line 31).

Evidence: Conflict tồn tại khi cùng một Managed Region: - dữ liệu VALORA mới khác giá trị ở snapshot/lần đồng bộ trước; và - nội dung hiện tại trong Word cũng đã được user chỉnh kể từ lần đồng bộ trước.

Current governing authority: Master section1.4, Return Revalidation section9 and Working Observation section7.5: true conflict V!=Old/W!=Old/V!=W; convergence may be non-conflict with audit/lineage.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Point definition to current exact three-way semantics and distinguish convergence; no new merge rule.

### R0-055 — Current relationship text preserves superseded publish board as authority

Path: [docs/design/VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md](../../docs/design/VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md) (line 138).

Evidence: - `Phát hành bộ tài liệu — Iteration 1`.

Current governing authority: Document Publish addendum status/section0 explicitly historical; current Release Preparation/Exception/Confirmation/Post-Publish addenda govern.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R3**.

Recommended remediation: Link current simplified Publishing authority; preserve old board as historical reference only.

### R0-056 — Retained authoritative staging contract lacks guarded Apply v2 successor navigation

Path: [docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md](../../docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md) (line 3).

Evidence: - **Status**: Authoritative API & Domain Contract

Current governing authority: Accepted ADR0048 and OS-G2 Asset Review Case State contract; CODEX A2 PR76 certified implementation.

Severity: **P2**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R6**.

Recommended remediation: Add scope/successor pointer for guarded post-Intake Apply v2 while leaving frozen s12-pr-004-v1 behavior unchanged.

### R0-057 — Machine-local E-drive authority/reference link

Path: [docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md](../../docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md) (line 64).

Evidence: - **S10-PR-005**: Handles full non-IT error message registry — completed (see &#91;VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md&#93;(file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md)).

Current governing authority: Live repository target exists: docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md or frontend/src/api/assetLines.ts or frontend/src/components/workbench/hooks/useAssetLineContext.ts respectively.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Replace file:///E: historical workstation link with verified repository-relative path.

### R0-058 — Machine-local E-drive authority/reference link

Path: [docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md](../../docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md) (line 84).

Evidence: - TypeScript declarations and the fetch helper function reside in &#91;assetLines.ts&#93;(file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/assetLines.ts).

Current governing authority: Live repository target exists: docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md or frontend/src/api/assetLines.ts or frontend/src/components/workbench/hooks/useAssetLineContext.ts respectively.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Replace file:///E: historical workstation link with verified repository-relative path.

### R0-059 — Machine-local E-drive authority/reference link

Path: [docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md](../../docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md) (line 113).

Evidence: - **Location**: &#91;useAssetLineContext.ts&#93;(file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/hooks/useAssetLineContext.ts).

Current governing authority: Live repository target exists: docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md or frontend/src/api/assetLines.ts or frontend/src/components/workbench/hooks/useAssetLineContext.ts respectively.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **UPDATE**. Target: **DOC-R6**.

Recommended remediation: Replace file:///E: historical workstation link with verified repository-relative path.

### R0-060 — Historical link drift (grouped, every affected path listed below)

Path: [docs/audits/AG_ONBOARD_001_ANTIGRAVITY_READINESS_AUDIT.md](../../docs/audits/AG_ONBOARD_001_ANTIGRAVITY_READINESS_AUDIT.md) (line 16).

Evidence: Historical machine-local, relocated or ambiguous references across 40 preserved artifacts.

Current governing authority: DOCUMENTATION_STATUS_INDEX.md §§5-8: immutable historical evidence; current relative references/index supersession, never reconstructed old bytes.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R6**.

Recommended remediation: Record a central link-disposition list; resolve current onboarding navigation outside immutable history; do not rewrite frozen audits/manifests.

| Preserved affected path | Future disposition |
| --- | --- |
| [docs/audits/AG_ONBOARD_001_ANTIGRAVITY_READINESS_AUDIT.md](../../docs/audits/AG_ONBOARD_001_ANTIGRAVITY_READINESS_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_001_DESIGN_BOOK_V1_3_AUDIT.md](../../docs/audits/S10_PR_001_DESIGN_BOOK_V1_3_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_002_ASTRYX_COMPONENT_MAPPING_AUDIT.md](../../docs/audits/S10_PR_002_ASTRYX_COMPONENT_MAPPING_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_003_ASTRYX_OFFICIAL_INTEGRATION_SPIKE_AUDIT.md](../../docs/audits/S10_PR_003_ASTRYX_OFFICIAL_INTEGRATION_SPIKE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_004_VIETNAMESE_I18N_LABEL_DICTIONARY_AUDIT.md](../../docs/audits/S10_PR_004_VIETNAMESE_I18N_LABEL_DICTIONARY_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_005_NON_IT_ERROR_MESSAGE_REGISTRY_AUDIT.md](../../docs/audits/S10_PR_005_NON_IT_ERROR_MESSAGE_REGISTRY_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_006_ASTRYX_APP_SHELL_ALIGNMENT_AUDIT.md](../../docs/audits/S10_PR_006_ASTRYX_APP_SHELL_ALIGNMENT_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S10_PR_007_SPRINT_10_FINAL_ACCEPTANCE_AUDIT.md](../../docs/audits/S10_PR_007_SPRINT_10_FINAL_ACCEPTANCE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_001_PROJECT_ASSET_LINES_API_CONTRACT_AUDIT.md](../../docs/audits/S11_PR_001_PROJECT_ASSET_LINES_API_CONTRACT_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_002A_WORKBENCH_ROUTE_PROJECT_UUID_RESOLUTION_AUDIT.md](../../docs/audits/S11_PR_002A_WORKBENCH_ROUTE_PROJECT_UUID_RESOLUTION_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_002_WORKBENCH_ASSET_GRID_READ_ADAPTER_AUDIT.md](../../docs/audits/S11_PR_002_WORKBENCH_ASSET_GRID_READ_ADAPTER_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_003_CONTEXT_DRAWER_DATA_ADAPTER_AUDIT.md](../../docs/audits/S11_PR_003_CONTEXT_DRAWER_DATA_ADAPTER_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_004_DRAFT_STATE_READ_MODEL_AUDIT.md](../../docs/audits/S11_PR_004_DRAFT_STATE_READ_MODEL_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_005_INLINE_DRAFT_EDITING_CONTRACT_AUDIT.md](../../docs/audits/S11_PR_005_INLINE_DRAFT_EDITING_CONTRACT_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_006_HUMAN_COMMIT_REVIEW_GATE_AUDIT.md](../../docs/audits/S11_PR_006_HUMAN_COMMIT_REVIEW_GATE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S11_PR_007_SPRINT_11_FINAL_ACCEPTANCE_AUDIT.md](../../docs/audits/S11_PR_007_SPRINT_11_FINAL_ACCEPTANCE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S12_PR_001_EXCEL_IMPORT_CONTRACT_STAGING_MODEL_AUDIT.md](../../docs/audits/S12_PR_001_EXCEL_IMPORT_CONTRACT_STAGING_MODEL_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S12_PR_002_EXCEL_FILE_UPLOAD_PARSER_INTAKE_AUDIT.md](../../docs/audits/S12_PR_002_EXCEL_FILE_UPLOAD_PARSER_INTAKE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S12_R_001_REPOSITORY_CI_GATE_REPAIR_AUDIT.md](../../docs/audits/S12_R_001_REPOSITORY_CI_GATE_REPAIR_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S1_PR_003_PERSISTENCE_ORM_MIGRATION_FOUNDATION_AUDIT.md](../../docs/audits/S1_PR_003_PERSISTENCE_ORM_MIGRATION_FOUNDATION_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S1_PR_004_ORGANIZATION_USER_ROLE_BASELINE_AUDIT.md](../../docs/audits/S1_PR_004_ORGANIZATION_USER_ROLE_BASELINE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S1_PR_005_REFERENCE_MASTER_DATA_TABLES_AUDIT.md](../../docs/audits/S1_PR_005_REFERENCE_MASTER_DATA_TABLES_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S1_PR_006_CUSTOMER_SUPPLIER_MASTER_DATA_TABLES_AUDIT.md](../../docs/audits/S1_PR_006_CUSTOMER_SUPPLIER_MASTER_DATA_TABLES_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S1_PR_007_PROJECT_PERSISTENCE_TABLES_AUDIT.md](../../docs/audits/S1_PR_007_PROJECT_PERSISTENCE_TABLES_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S6_PR_002_FRONTEND_APP_SHELL_LAYOUT_AUDIT.md](../../docs/audits/S6_PR_002_FRONTEND_APP_SHELL_LAYOUT_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S6_PR_003_VIRTUALIZED_ASSET_GRID_CORE_AUDIT.md](../../docs/audits/S6_PR_003_VIRTUALIZED_ASSET_GRID_CORE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S6_PR_004_SIDE_DRAWER_CONTEXT_PANELS_AUDIT.md](../../docs/audits/S6_PR_004_SIDE_DRAWER_CONTEXT_PANELS_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S6_PR_005_INLINE_DRAFTS_AUTOSAVE_UNDO_REDO_UI_AUDIT.md](../../docs/audits/S6_PR_005_INLINE_DRAFTS_AUTOSAVE_UNDO_REDO_UI_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S6_PR_006_REVIEW_QUEUE_ROLE_GATED_UI_AUDIT.md](../../docs/audits/S6_PR_006_REVIEW_QUEUE_ROLE_GATED_UI_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S6_PR_007_FRONTEND_HARDENING_FINAL_ACCEPTANCE_AUDIT.md](../../docs/audits/S6_PR_007_FRONTEND_HARDENING_FINAL_ACCEPTANCE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S7_PR_002_API_CLIENT_HEALTH_OPENAPI_SMOKE_AUDIT.md](../../docs/audits/S7_PR_002_API_CLIENT_HEALTH_OPENAPI_SMOKE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S7_PR_003_WORKBENCH_SESSION_HEARTBEAT_AUDIT.md](../../docs/audits/S7_PR_003_WORKBENCH_SESSION_HEARTBEAT_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S7_PR_004_SESSION_SCOPED_WORKBENCH_STATE_AUDIT.md](../../docs/audits/S7_PR_004_SESSION_SCOPED_WORKBENCH_STATE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S7_PR_005_INLINE_DRAFT_CHECKPOINT_UNDO_REDO_SYNC_AUDIT.md](../../docs/audits/S7_PR_005_INLINE_DRAFT_CHECKPOINT_UNDO_REDO_SYNC_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S7_PR_006_RBAC_CONFLICT_UI_HARDENING_AUDIT.md](../../docs/audits/S7_PR_006_RBAC_CONFLICT_UI_HARDENING_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S8_PR_002_POSTGRESQL_MIGRATION_SMOKE_AUDIT.md](../../docs/audits/S8_PR_002_POSTGRESQL_MIGRATION_SMOKE_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S8_PR_003_PRODUCTION_ENV_CORS_HARDENING_AUDIT.md](../../docs/audits/S8_PR_003_PRODUCTION_ENV_CORS_HARDENING_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S8_PR_004_DOCKER_COMPOSE_NGINX_CONFIG_AUDIT.md](../../docs/audits/S8_PR_004_DOCKER_COMPOSE_NGINX_CONFIG_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/audits/S8_PR_005_SECURITY_SCANS_CI_QUALITY_GATES_AUDIT.md](../../docs/audits/S8_PR_005_SECURITY_SCANS_CI_QUALITY_GATES_AUDIT.md) | Central historical link log only; original bytes unchanged |
| [docs/sprint-6/FRONTEND_WORKBENCH_IMPLEMENTATION_PLAN.md](../../docs/sprint-6/FRONTEND_WORKBENCH_IMPLEMENTATION_PLAN.md) | Central historical link log only; original bytes unchanged |

### R0-061 — Historical OPEN GitHub artifact is not current work

Path: [https://github.com/Reguluspt/valora-engineering/pull/19](https://github.com/Reguluspt/valora-engineering/pull/19).

Evidence: OPEN / DRAFT; Historical S13 mapping-memory packet; later certified G1.1 authority/implementation wins.

Current governing authority: Live CODEX task gates, current v2.3 authority and Unified Roadmap; Issue92 explicitly forbids closing/modifying/resuming/merging these artifacts.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R6**.

Recommended remediation: Later Gate Owner may decide administrative retirement/link-only clarification; DOC-R0 makes no GitHub changes. No semantic Product Owner decision required.

### R0-062 — Historical OPEN GitHub artifact is not current work

Path: [https://github.com/Reguluspt/valora-engineering/pull/20](https://github.com/Reguluspt/valora-engineering/pull/20).

Evidence: OPEN / DRAFT; Historical hybrid AI workflow proposal; live CODEX §§1.0/1.1 controls model roles/commit ownership.

Current governing authority: Live CODEX task gates, current v2.3 authority and Unified Roadmap; Issue92 explicitly forbids closing/modifying/resuming/merging these artifacts.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R6**.

Recommended remediation: Later Gate Owner may decide administrative retirement/link-only clarification; DOC-R0 makes no GitHub changes. No semantic Product Owner decision required.

### R0-063 — Historical OPEN GitHub artifact is not current work

Path: [https://github.com/Reguluspt/valora-engineering/pull/27](https://github.com/Reguluspt/valora-engineering/pull/27).

Evidence: OPEN / NON-DRAFT; Historical v1.8 handoff; current v2.3 master/index and accepted scoped ADRs win.

Current governing authority: Live CODEX task gates, current v2.3 authority and Unified Roadmap; Issue92 explicitly forbids closing/modifying/resuming/merging these artifacts.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R6**.

Recommended remediation: Later Gate Owner may decide administrative retirement/link-only clarification; DOC-R0 makes no GitHub changes. No semantic Product Owner decision required.

### R0-064 — Historical OPEN GitHub artifact is not current work

Path: [https://github.com/Reguluspt/valora-engineering/issues/37](https://github.com/Reguluspt/valora-engineering/issues/37).

Evidence: OPEN; Historical F2-PR003 task; merged PR38/integration and PR32 OS-G0 parent closeout supersede READY FOR DEV.

Current governing authority: Live CODEX task gates, current v2.3 authority and Unified Roadmap; Issue92 explicitly forbids closing/modifying/resuming/merging these artifacts.

Severity: **P3**. Semantics change: **NO**. PO decision required: **NO**. Action: **INDEX_ONLY**. Target: **DOC-R6**.

Recommended remediation: Later Gate Owner may decide administrative retirement/link-only clarification; DOC-R0 makes no GitHub changes. No semantic Product Owner decision required.

## Mandatory scan coverage and negative controls

| Scan | Requirement | Disposition |
| --- | --- | --- |
| S01 | Stale live SHA / CI / PR / Issue | Current undated README/roadmap/design-index sections flagged; explicitly dated PR32/old exact-SHA evidence retained. |
| S02 | A5 / ASSET_REVIEW resumed-active | CODEX header/live gate flagged against merged PR86 and closed Issue81. |
| S03 | G1 / G1.1 / G2 not started | Root governance, roadmap, design/ADR/retained contract metadata mapped to G1.1K and A2/A4/A5 closure; OS-G2 later stages still open. |
| S04 | README Adaptive Intake / mapping | Certified bounded G1.1H/K user journey contradicts README current-product gap list; future AI/identity expansion not declared complete. |
| S05 | Windows Docker stack production | No unresolved current conflict: ADR0050 and Issue89 amendments explicitly supersede it. Local developer Compose and historical Windows stack references remain evidence. |
| S06 | Architecture after Preview | No unresolved current conflict: ADR0050 D9 and reconciled Preview/roadmap §11.1 select architecture before formal UAT. |
| S07 | Foundation conflated with formal UAT | No unresolved current conflict: WIN0-5 explicit assignment, WIN6 after SoftwareCompletion, Linuxpilot separate; plans grant no runtime/deployment. |
| S08 | Local LLM / weights / GPU requirement | No unresolved current requirement: ADR0050 D7 forbids v1 dependency; AI plan/mock/review tooling mentions do not activate inference. |
| S09 | Cloud-staging sequencing | No unresolved current automatic grant: ADR0050 D9/current plans/Preview keep cloud deployment a separate owner gate; historical provider research preserved. |
| S10 | Astryx current visual authority | Current v2.3/Fluent2 authority is consistent. Retained PR02 amendment still calls active styling dark/Astryx; mark prior debt superseded by PR32. Old assets/audits are historical. |
| S11 | Legacy Review Queue / Validation / QC | No competing current workflow: retired PR00 route inventory needs disposition; historical/proposed/local-review mentions do not resurrect global routes. |
| S12 | OneDrive/document authority | ADR0043-45 and current amendments retain DB revision/CurrentHead + immutable blobs, nonauthoritative Working/Exchange. Child W/revision and conflict wording drift flagged, not new authority. |
| S13 | AI runtime/provider authorization | No current unsafe activation found: OS-G7/AI-PR001-012 and provider gates remain planned/unauthorized; no deployment dependency. Development review tools are distinct. |
| S14 | Competing guards/roadmaps and scoped authority | Old docs/02 guard explicitly historical; one unified OS-G roadmap. Generic restricted-field routing summaries and specific child template/Word/conflict prose need accepted successor pointers; no new semantics. |
| S15 | Active plans without explicit status | Three current execution-tooling/template documents lack explicit lifecycle status; planned Windows/Linux/Preview and token-pilot labels are explicit. |
| S16 | Obsolete documentation counts | 380/379 September24 totals are dated evidence, not arithmetic errors. Current index should link new559/562 scope census; old audits stay intact. |
| S17 | Broken authority/index links | Three current paths with four real link issues; historical path candidates recorded per artifact and centrally, including local drives/moved targets/ambiguous anchors. PDF #page fragments treated as viewer locators, not missing files; external HTTP URLs not availability-tested. |
| S18 | ADR/design/status index certification drift | Complete50-ADR map:26accepted (including partial supersession) /24declared proposed; status/index discrepancies map to exact certified checkpoints. ADR0050 doccert does not certify runtime. |
| S19 | Old open GitHub work | PR19/20/27 and Issue37 read live/in full, classified historical despite OPEN; later GateOwner admin action only. F2 READY headers remain original completed packets under PR32, not restarted work. |

All19 requirements were considered in marker scanning and scoped review, including zero-current-conflict outcomes. Historical future prompts/READY labels and explicit “noLLM/noDockerDesktop/nolegacyworkflow” rules are not treated as current authorizations. OpenGitHub is not an authority class.

## Evidence-based proposed DOC-R split

| Proposed batch | Primary artifact count | Scope / boundary |
| --- | --- | --- |
| DOC-R1 | 3 | Root current-state truth; accepted dedicated status-command/Apply successor pointers, no security/domain redesign. |
| DOC-R2 | 2 | Unified roadmap and AI plan current-snapshot disposition; ADR0050 architecture already selected, no deployment implementation. |
| DOC-R3 | 22 | Current design/index/retained contracts and accepted ADR implementation-disposition metadata; original decisions/frozen v1 bodies preserved. |
| DOC-R4 | 6 | Accepted A0/A5R plan dispositions, explicit tooling status, current onboarding references outside preserved historical handoff. |
| DOC-R5 | 0 | Omit: no justified new inline historical notice required; preserve all history. |
| DOC-R6 | 45 | Central lifecycle/count/status map, current links, immutable historical link-disposition list and final closeout; four external GitHub records separately. |
| NONE | 484 | Preserve; no remediation proposed. |

Recommend three docs-only candidate/CI rounds: **DOC-R1+DOC-R2** together for shared live checkpoint truth; **DOC-R3+DOC-R4** together for scoped successor/disposition/navigation reconciliation; **DOC-R6** final census/cross-links/closeout. Omit DOC-R5. Keep nominal ownership labels in the ledger so batch membership remains auditable; link fixes on a substantively edited file travel with that file. This consolidation is a proposal only, not an authorization to begin remediation.

Later batches must freeze their own exact HEAD/review/CI. They may add present disposition metadata or central links, preserve historical evidence and accepted semantic bodies, and must not infer product/runtime/provider/deployment authorization from documentation acceptance. Stop for a new PO decision only if a true semantic conflict remains after applying accepted scoped precedence. None remains in this audit.

## Historical GitHub disposition

| Artifact | Live observed state | Lifecycle / recommendation |
| --- | --- | --- |
| [https://github.com/Reguluspt/valora-engineering/pull/19](https://github.com/Reguluspt/valora-engineering/pull/19) | OPEN / DRAFT | Historical S13 mapping-memory packet; later certified G1.1 authority/implementation wins. Later Gate Owner may retire administratively; no DOC-R0 mutation. |
| [https://github.com/Reguluspt/valora-engineering/pull/20](https://github.com/Reguluspt/valora-engineering/pull/20) | OPEN / DRAFT | Historical hybrid AI workflow proposal; live CODEX §§1.0/1.1 controls model roles/commit ownership. Later Gate Owner may retire administratively; no DOC-R0 mutation. |
| [https://github.com/Reguluspt/valora-engineering/pull/27](https://github.com/Reguluspt/valora-engineering/pull/27) | OPEN / NON-DRAFT | Historical v1.8 handoff; current v2.3 master/index and accepted scoped ADRs win. Later Gate Owner may retire administratively; no DOC-R0 mutation. |
| [https://github.com/Reguluspt/valora-engineering/issues/37](https://github.com/Reguluspt/valora-engineering/issues/37) | OPEN | Historical F2-PR003 task; merged PR38/integration and PR32 OS-G0 parent closeout supersede READY FOR DEV. Later Gate Owner may retire administratively; no DOC-R0 mutation. |

## Preservation and candidate gate

Changed historical evidence: **NONE**. Runtime/source changes: **NO**. Unexpected current-authority edits: **NONE**. Outputs are only the inventory MD/JSON and this matrix. This diagnostic records source findings without fixing them. The zero-unresolved-material-P0–P3 candidate-review gate applies to the quality/completeness of these outputs; it does not require DOC-R1…R6 source remediation in DOC-R0. DeepSeek must independently challenge path completeness, classifications, current/historical boundaries, architecture scans, batch ownership and the complete50-ADR map. Gemini is N/A unless genuine authority ambiguity remains. Frozen exact-head CI and DraftPR evidence belong to the closeout; no Ready/merge.
