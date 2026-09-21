# 2026-09-21 — Documentation Reconciliation Audit — Handoff v2.3 / Unified Roadmap / Fluent 2

**Status:** COMPLETE — CURRENT-LIVING-DOC RECONCILIATION  
**Branch:** `feat/operational-frontend-m365` / Draft PR #32  
**Inventory:** 350 documentation/config-document files enumerated from the branch tree.  
**Authority basis:** current UI/UX Handoff v2.3 + Authority Index + applicable addenda + accepted scoped ADRs; Unified Appraisal OS Roadmap v2.3 for development sequencing.

## 1. Reconciliation rule

Current authority roles are:

```text
Explicit current Product Owner decision — named scope only
→ UI/UX Handoff v2.3 + Authority Index + applicable addenda + scoped ADRs
   → product semantics / workflow / IA / interaction / Microsoft Fluent 2 light visual authority
→ Unified Appraisal OS Roadmap v2.3
   → development sequencing / architecture integration
→ current task/implementation contracts
→ historical evidence
```

Historical sprint/audit/remediation records are not rewritten to pretend they knew later decisions.

## 2. Major stale directions removed from living docs

### Visual-system authority

Superseded:
- Astryx as product visual authority;
- Astryx compliance as an engineering requirement;
- dark/cyan/glassmorphic styling as accepted product presentation.

Current:
- Microsoft Fluent 2 light;
- desktop-first;
- Vietnamese-first;
- data-heavy/table-first;
- approved S10/S12/S13/NCCQ/NCC Selection/Document Workspace baselines as golden visual evidence;
- screenshot/visual-regression acceptance required for authority-defined golden screens.

Astryx package/component mapping remains historical/low-level reference only.

### Roadmap sequencing

Superseded for current ordering:
- Part 2C `PR-00 → PR-13` execution sequence;
- S13–S16 historical roadmap;
- provider/storage sub-roadmaps as product-order authority.

Current:
```text
OS-G0 Authority + Fluent 2 visual reconciliation
→ OS-G1 Pre-case
→ OS-G2 Appraisal Core
→ OS-G3 Document Runtime
→ OS-G4 Release / Publishing
→ OS-G5 Template Intelligence / Fidelity
→ OS-G6 Product E2E
→ OS-G7 Controlled AI Expansion
```

Historical PR numbers remain acceptance/evidence labels only.

### Document Workspace terminology

Superseded:
- Microsoft 365/OneDrive as the product workspace name.

Current:
- `Không gian tài liệu / Bộ tài liệu hồ sơ` is the provider-neutral parent surface;
- Microsoft 365/Word/OneDrive/SharePoint are integration/editing surfaces/actions only.

### Document version semantics

Superseded:
- standalone `Khóa phiên bản` workflow/command;
- Working Save or re-import directly authorizing Revision N+1;
- provider-copy success as authoritative sync success.

Current:
```text
GeneratedDocumentCandidate
→ verification
→ explicit Tạo/Xác nhận phiên bản
→ immutable DocumentRevision
```

Working change:
```text
Word Save
→ observation/revalidation
→ DocumentChangeCandidate
→ Old/V/W
→ review/conflict
→ human-confirmed command
→ Revision N+1
```

Publishing:
```text
accepted DocumentRevision(s)
→ ReleasePlan
→ readiness/exception
→ ReleaseManifest bind exact accepted revisions
→ explicit Publish
→ immutable Published release
```

## 3. Living documents updated in this sweep

Repository entry/governance:
- `README.md`
- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `docs/DOCUMENTATION_STATUS_INDEX.md`
- `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
- `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`

Canonical roadmap/design:
- `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`
- `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md`
- provider-neutral M365/document addenda already reconciled in the same branch remain current.

Implementation/evidence interpretation:
- `docs/implementation/VALORA_UIUX_V2_3_PR05_M365_INTEGRATION_FOUNDATION_CONTRACT.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR06_M365_RETURN_REVALIDATION_CONTRACT.md`
- `docs/implementation/VALORA_OPERATIONAL_FRONTEND_M365_BROWSER_ACCEPTANCE_CLOSEOUT.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md`

Historical design-system reference:
- `docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md`

## 4. Intentional residual historical wording

The repository still contains terms such as:
- Astryx;
- Review Queue;
- Validation Dashboard;
- PR-08/PR-13;
- Microsoft 365 Document Workspace;
- Khóa phiên bản.

Residual occurrences are acceptable only when they are explicitly labeled:
- historical;
- superseded;
- forbidden/deprecated;
- low-level reference;
- acceptance/evidence history.

They are not current product/runtime authority.

## 5. Historical classes intentionally preserved

No semantic rewriting was applied to:
- `docs/audits/**` historical evidence;
- `docs/sprint-1/**` … `docs/sprint-8/**`;
- `docs/remediation/**`;
- `docs/handoff/**`;
- `docs/plan/done/**`;
- older UI/UX handoffs v1.8–v2.2.

These are interpreted through `docs/DOCUMENTATION_STATUS_INDEX.md`.

## 6. Current implementation gaps not fixed by documentation

This reconciliation does not claim runtime completion.

Still open:
- Fluent 2 light frontend remediation and visual regression;
- removal of reachable Review Queue / standalone Validation Dashboard;
- S13 four-tab implementation;
- full Pre-case product surface;
- canonical stages 5–16;
- Appraisal Core vertical closure;
- ADR-0045 Working Change Observation runtime;
- ReleasePlan/ReleaseManifest/Publish runtime;
- full Template Fidelity platform;
- North-star exact-SHA E2E;
- live AppFolder conformance where separately authorized.

## 7. Maintenance rule

Future authority changes must:
1. update Handoff/addendum/ADR first;
2. update Unified Roadmap if ordering changes;
3. update Documentation Status Index and docs index;
4. amend living contracts that would otherwise mislead;
5. preserve historical evidence;
6. rerun stale-marker sweep before declaring documentation reconciled.
