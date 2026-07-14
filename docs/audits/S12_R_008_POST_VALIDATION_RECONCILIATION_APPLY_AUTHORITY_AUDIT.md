# S12-R-008 — Post-Validation Reconciliation & Apply Design Authority Audit

## Status

```text
S12-R-008 CORRECTIVE AUTHORITY COMPLETE — AWAITING DRAFT PR, CI, AND INDEPENDENT RE-AUDIT
```

| Field | Value |
| --- | --- |
| Task | S12-R-008 Post-Validation Reconciliation & Apply Design Authority |
| Mode | Documentation / design authority only |
| Independent audit (prior) | **PASS WITH FIXES** — merge blocked pending corrective authority |
| S12-R-008 starting baseline | `c2f154dda3ba9c9dd4bdbdb8ce23676315bba1b7` (S12-PR-003 PR #8; label only, not evergreen current-main) |
| Branch | `s12-r-008-post-validation-reconciliation-apply-authority` |
| Commit A | `18725a6fafca1e630b09da2fc6b24e5a12ae9f69` |
| Commit B | `6b70bcd56970ba71eff1e111d23b78f826755b69` |
| Commit C (corrective) | `39352d15b63ecd06deecad0b69d9f9776d55887f` |
| Commit D | this audit-only corrective evidence commit |
| Draft PR | **Not created in corrective session** |
| CI | **Pending** Draft PR / branch CI |
| Independent re-audit | **Pending** |

## Scope

### In scope

- Encode owner-approved Apply D1–D17 as repository authority
- Independent-audit corrective findings F-1…F-5
- Historical audit addenda only (no rewrite of past SHAs/CI/conclusions)

### Out of scope

- Backend/frontend/worker/migrations/models/tests/dependencies/CI workflows
- S12-PR-004 implementation branch or production Apply code
- PR Ready / merge / main mutation
- Protected onboarding report

## Commit A changed paths (historical)

```text
CODEX.md
ENGINEERING_GUARDRAILS.md
README.md
docs/VALORA_PROJECT_HANDOFF.md
docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md
docs/adr/0029-excel-staging-apply-command-and-lineage.md
docs/audits/S12_PR_003_EXCEL_STAGING_VALIDATION_ENGINE_AUDIT.md
docs/audits/S12_R_007_DOCUMENTATION_RECONCILIATION_FINAL_ACCEPTANCE_AUDIT.md
docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md
docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md
```

## Commit B paths (historical audit-only)

```text
docs/audits/S12_R_008_POST_VALIDATION_RECONCILIATION_APPLY_AUTHORITY_AUDIT.md
```

## Commit C changed paths (exact)

```text
CODEX.md
ENGINEERING_GUARDRAILS.md
README.md
docs/VALORA_PROJECT_HANDOFF.md
docs/adr/0029-excel-staging-apply-command-and-lineage.md
docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md
docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md
```

Subject: `docs: close S12-R-008 Apply authority ambiguities`

## Commit D paths

```text
docs/audits/S12_R_008_POST_VALIDATION_RECONCILIATION_APPLY_AUTHORITY_AUDIT.md
```

**Confirmation:** Commit D is audit-only (this file only).

## Independent-audit findings F-1…F-5 resolution

| ID | Finding | Resolution evidence |
| --- | --- | --- |
| F-1 | Freeze `contract_version` | ADR 0029 + contract §15: exact `s12-pr-004-v1` in success/failure audits |
| F-2 | Freeze audit cardinality | Identical outcome matrix in ADR 0029 and contract §15 F3 |
| F-3 | Failure-state preservation; no `apply_failed` | Explicit preserve list; batch stays `ready_for_review`; no `apply_failed` status |
| F-4 | Deterministic mapping mechanics | Stage order `source_row_number ASC, id ASC`; Unicode trim/case-fold exact match; unit/currency priority; Decimal-only |
| F-5 | Operator docs transition-safe | Live R008/PR-004 gate; `c2f154d…` labeled **starting baseline**; fetch live `origin/main` |

## Authority matrix D1–D17 (unchanged ownership; freezes added)

| ID | Decision | Authority location |
| --- | --- | --- |
| D1 | S12-R-008 docs; S12-PR-004 backend Apply + lineage; no frontend | ADR 0029; live gate in operator docs |
| D2 | `POST …/apply` + `{ "confirm": true }` | ADR 0029; contract §15A |
| D3 | `workbench:edit`; DRAFT-only; safe 404 | ADR 0029; contract §15A |
| D4 | `ready_for_review`; all rows `valid`; all-or-nothing | ADR 0029; contract §15B |
| D5 | Explicit registry + F-4 mechanics; `s12-pr-004-v1` | ADR 0029; contract §15C/C2 |
| D6 | Append only | ADR 0029; contract §15D |
| D7 | Single transaction; full rollback | ADR 0029; contract §15D |
| D8 | Success → `applied`; re-apply 409 | ADR 0029; contract §15E |
| D9 | Project → batch → staging locks; fingerprint | ADR 0029; contract §15F |
| D10 | Retain staging; reject applied | ADR 0029; contract §15G |
| D11 | Lineage FKs | ADR 0029; contract §15H |
| D12 | Apply events + F-1/F-2 audit freezes | ADR 0029; contract §15I / F3 |
| D13 | Distinct command; description exception | ADR 0028 addendum; ADR 0029 |
| D14 | No reverse/delete | ADR 0029 |
| D15 | Response + VI errors | ADR 0029; contract §15J |
| D16 | Backend-only | ADR 0029; contract §15K |
| D17 | Acceptance + PG matrix | ADR 0029; contract §15L |

## Static consistency scans (corrective)

| Check | Result |
| --- | --- |
| Exact `s12-pr-004-v1` in ADR 0029 and contract §15 | **Yes** |
| Audit matrix identical in both | **Yes** |
| Failure preservation + no `apply_failed` | **Yes** |
| Row order / unit-currency priority / Unicode / Decimal rules | **Yes** |
| Operator docs live before/after merge gate | **Yes** |
| Frozen SHA labeled starting baseline | **Yes** |
| Production/test/config/dependency paths | **None** |
| Prompt/report artifacts tracked | **No** |

## Documentation gates

| Gate | Result |
| --- | --- |
| Docs-only change set | **Yes** |
| Backend/frontend/worker pytest | **Not re-run** (docs-only) |
| `git diff --check origin/main...HEAD` | Recorded after Commit D |

## Protected artifacts

| Artifact | Status |
| --- | --- |
| `docs/remediation/S12_R_004_ONBOARDING_REPORT_2026_07_12.md` | Untracked; **untouched** |
| Transport prompts | Removed after read; not staged |

## Remaining process steps

1. Open **Draft PR** for branch `s12-r-008-post-validation-reconciliation-apply-authority`.
2. Wait for GitHub Actions green on documentation head.
3. Independent **re-audit** of S12-R-008 corrective authority.
4. Owner-controlled Ready / merge.
5. Only then start **S12-PR-004** when live gate says main contains R008 / ADR 0029.

## Final verdict

```text
S12-R-008 CORRECTIVE AUTHORITY COMPLETE — AWAITING DRAFT PR, CI, AND INDEPENDENT RE-AUDIT
```
