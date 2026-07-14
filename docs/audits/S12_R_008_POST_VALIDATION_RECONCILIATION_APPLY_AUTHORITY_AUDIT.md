# S12-R-008 — Post-Validation Reconciliation & Apply Design Authority Audit

## Status

```text
S12-R-008 LOCAL AUTHORITY RECONCILIATION COMPLETE — AWAITING DRAFT PR, CI, AND INDEPENDENT AUDIT
```

| Field | Value |
| --- | --- |
| Task | S12-R-008 Post-Validation Reconciliation & Apply Design Authority |
| Mode | Documentation / design authority only |
| Starting `origin/main` | `c2f154dda3ba9c9dd4bdbdb8ce23676315bba1b7` (S12-PR-003 PR #8 merge) |
| Branch | `s12-r-008-post-validation-reconciliation-apply-authority` |
| Commit A | `18725a6fafca1e630b09da2fc6b24e5a12ae9f69` |
| Commit B | this audit-only evidence commit |
| Draft PR | **Not created in this session** (awaiting owner/process) |
| CI | **Pending** Draft PR / branch CI |
| Independent audit | **Pending** |

## Scope

### In scope

- Encode owner-approved Apply D1–D17 as repository authority
- Reconcile post-merge S12-PR-003 truth in operator docs
- ADR 0029, staging contract §15, ADR 0028 addendum
- Historical audit addenda only (no rewrite of past SHAs/CI/conclusions)

### Out of scope

- Backend/frontend/worker/migrations/models/tests/dependencies/CI workflows
- S12-PR-004 implementation branch or production Apply code
- PR Ready / merge / main mutation
- Protected onboarding report

## Commit A changed paths (exact)

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

Commit A subject: `docs: approve S12-PR-004 Apply command and lineage authority`

## Commit B paths

```text
docs/audits/S12_R_008_POST_VALIDATION_RECONCILIATION_APPLY_AUTHORITY_AUDIT.md
```

**Confirmation:** Commit B is audit-only (this file only).

## Authority matrix D1–D17

| ID | Owner decision (encoded) | Authority location |
| --- | --- | --- |
| D1 | S12-R-008 docs; S12-PR-004 backend Apply + lineage; no frontend | ADR 0029; CODEX; handoff |
| D2 | `POST …/apply` + `{ "confirm": true }`; no auto-apply/worker/AI | ADR 0029; contract §15A |
| D3 | `workbench:edit`; DRAFT-only; safe 404; no session required | ADR 0029; contract §15A |
| D4 | `ready_for_review`; all rows `valid`; non-empty; all-or-nothing | ADR 0029; contract §15B |
| D5 | Explicit mapping registry; description via Apply only; exclusions | ADR 0029; contract §15C |
| D6 | Append only; no upsert/dedup/delete | ADR 0029; contract §15D |
| D7 | Single transaction; full rollback | ADR 0029; contract §15D |
| D8 | Success → `applied`; re-apply 409; new batch for corrections | ADR 0029; contract §15E |
| D9 | Project → batch → staging locks; fingerprint; stale guard | ADR 0029; contract §15F |
| D10 | Retain staging; reject upload/validate/apply on applied | ADR 0029; contract §15G |
| D11 | Lineage FKs nullable; unique staging row id | ADR 0029; contract §15H |
| D12 | Apply command/events + safe payload keys | ADR 0029; contract §15I |
| D13 | Distinct official command; description exception; ADR 0028 addendum | ADR 0028 addendum; ADR 0029 |
| D14 | No reverse/delete; DRAFT corrections via Workbench | ADR 0029 |
| D15 | Response shape + Vietnamese error table | ADR 0029; contract §15J |
| D16 | Backend-only; future UI separate | ADR 0029; contract §15K |
| D17 | Acceptance + PG matrix zero-skip CI | ADR 0029; contract §15L |

### Source contradictions found and resolution

| Issue | Resolution |
| --- | --- |
| Operator docs still said R007 active / PR-003 blocked | Reconciled to PR-003 merged; R008 active; PR-004 next |
| Contract had Apply only as future mermaid step | Added authoritative §15 |
| ADR 0028 silent on Apply description create | Addendum: description via Apply only; other restricted spreadsheet fields forbidden |
| PR-003 audit still “AWAITING INDEPENDENT RE-AUDIT” | **Addendum only** — merge truth recorded; historical body retained |
| R007 audit “PR-003 not started” | **Addendum only** — labeled historical |

No ADR 0028 vs 0029 contradiction after addendum: PATCH remains blocked; Apply is a separate command; description create is the sole owner exception.

## Static consistency scans (local)

Commands:

```text
Select-String on README/CODEX/guardrails/handoff for "S12-PR-003.*(blocked|not started)"
Select-String for S12-R-008 / S12-PR-004 / ADR 0029
Select-String for apply endpoint and lineage fields in ADR 0029 + contract
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
git diff --name-only origin/main...HEAD | production path filter
```

Results:

| Check | Result |
| --- | --- |
| Current authority claims PR-003 blocked/not started | **No** (only explicit “must not describe as blocked” guidance) |
| R008 / PR004 roles present and not conflated | **Yes** (R008 = docs active; PR004 = next implementation after R008 merges) |
| Apply endpoint/mapping/lineage in current authority | **Yes** (ADR 0029 + contract §15) |
| Production/test/config/dependency paths changed | **None** |
| `git diff --check origin/main...HEAD` | Clean after whitespace normalize |
| Prompt / discovery reports tracked | **No** |

## Documentation gates

| Gate | Result |
| --- | --- |
| Docs-only change set | **Yes** |
| Backend/frontend/worker pytest | **Not re-run** (docs-only; no production change) — do not claim PASS from prior CI |
| Ruff / npm / Alembic | **Not required** for this docs-only commit set |
| Truthful CI for this branch | **Awaiting** push + Draft PR workflow |

## Protected artifacts

| Artifact | Status |
| --- | --- |
| `docs/remediation/S12_R_004_ONBOARDING_REPORT_2026_07_12.md` | Untracked; **untouched** |
| Transport prompt | Removed from working tree after read; not staged |

## Remaining process steps

1. Open **Draft PR** for branch `s12-r-008-post-validation-reconciliation-apply-authority` (owner/process; not done in this session per prompt).
2. Wait for GitHub Actions green on documentation head.
3. Independent audit of S12-R-008.
4. Owner-controlled Ready / merge.
5. Only then start **S12-PR-004** implementation.

## Final verdict

```text
S12-R-008 LOCAL AUTHORITY RECONCILIATION COMPLETE — AWAITING DRAFT PR, CI, AND INDEPENDENT AUDIT
```
