# CODEX.md — Valora Engineering Rules for Coding Agents

**Created:** 2026-07-06
**Last reconciled:** 2026-07-14 (S12-R-008)
**Applies to:** All agent-generated work in the Valora repository

## 1. Source of Truth

Domain behavior must come from:

```text
1. Valora Design Book v1.2-final + v1.3 MVP completion addendum
2. docs/design/* contracts (including Excel staging contract §14–§15)
3. docs/adr/* decisions (including ADR 0028 + addendum, ADR 0029)
4. docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md (historical S12-R gates + recon notes)
5. docs/VALORA_PROJECT_HANDOFF.md
```

Do **not** invent domain behavior. If ambiguous: stop and request an ADR or Design Change Request.

Historical Sprint 0 planning docs under `docs/01_*` … `docs/05_*` are **historical foundation records**, not the active phase description.

## 2. Current Engineering Phase

```text
Engineering Phase / Post-Validation Apply Authority
Active task: S12-R-008 — Post-Validation Reconciliation & Apply Design Authority
```

### Active task rules (S12-R-008)

```text
Documentation / design-authority only.
No production code, tests, migrations, workflows, config, or dependency changes
unless a separate implementation task (S12-PR-004) explicitly authorizes them
after S12-R-008 merges.
```

### Completed (do not re-open as “blocked / not started”)

```text
S12-PR-003 — Excel Staging Validation Engine — MERGED to main (PR #8)
```

### Next implementation task (blocked until R008 acceptance + merge)

```text
S12-PR-004 — Excel Staging Apply Command & Provenance
```

May start **only after**:

```text
1. S12-R-008 Draft PR CI is green on the documentation head
2. Independent audit PASS for S12-R-008
3. S12-R-008 is merged to main
4. Project handoff marks S12-PR-004 unblocked
```

Do **not** implement Apply inside an R008 session. Do **not** invent Apply behavior outside ADR 0029 / contract §15.

## 3. Permanent Hard Rules

```text
No domain invention outside Design Book / ADR / approved contract.
No AI auto-approval or auto-apply of official data.
ADR 0028 restricted Workbench fields (description, appraised_unit_price,
  review_status, validation_status) require draft-commit command path + authorization
  + human confirmation + version safety + atomic audit. Direct PATCH of those fields is blocked.
Non-restricted ProjectAssetLine fields may use direct PATCH under project:update and are
  outside the R004 Human Commit Gate / atomic-command guarantee.
Excel upload/validate still never mutate official ProjectAssetLine rows.
Apply (S12-PR-004 after R008) is the only approved promotion path; see ADR 0029.
No tenant boundary bypass (organization_id / project / session fail-closed).
No secrets committed; no production credentials in repo.
No unbounded whole-file materialization on Excel runtime path
  (no bare .read(), no BytesIO(file.read()), no list(ws.iter_rows())).
Excel intake mutates only import batch + staging — never ProjectAssetLine.
Local PostgreSQL skips are NOT PASS.
No skipped tests to hide failures.
No unrelated refactors or formatting churn.
No deleting or weakening guardrails.
Vietnamese client-facing copy must keep correct diacritics.
Astryx compliance for Workbench UI.
```

## 4. Domain Non-Negotiables

```text
Valora Workbench is the main workspace.
Word/Excel are input/output, not source of truth.
Market Quote is not Appraised Price.
AI suggests; human reviews; system audits.
Evidence is immutable or append-only.
ReviewDecision is append-only.
Organization/tenant boundaries are enforced server-side.
```

## 5. Evidence Semantics

```text
Local SQLite/unit results: development evidence only.
PostgreSQL behavior: requires CI (or local) run with PostgreSQL service.
Audit PASS for a historical PR does not imply current slice READY.
Do not treat skipped tests as passed.
Do not claim Draft PR / Ready / merge without explicit authorization.
```

## 6. Required Output After Every Task

```text
Task ID
Files changed
Design/ADR sources
Tests/gates run (raw counts)
Known limitations
Whether scope was respected
Whether any ADR is needed
Git SHAs (local/remote) when pushing
```

## 7. Stop Conditions

Stop and ask when:

```text
Domain rule missing or Design Book conflict.
Permission / tenant rule ambiguous.
Architecture change required without ADR.
Task requires work outside the assigned task ID.
New dependency with architectural impact.
Secret/credential/production config required.
Starting baseline SHA does not match the task prompt.
Protected files are involved (e.g. unauthorized onboarding artifacts).
```

## 8. Pull Request Behavior

```text
One task, one responsibility, reviewable size.
Tests or explicit N/A for docs-only.
No silent refactors.
User/owner controls Draft PR creation, Ready, squash, and merge
unless a task explicitly authorizes otherwise.
```

## 9. Security Requirement

```text
deny by default
least privilege
server-side authorization
no X-User-Id identity spoofing in production paths
short-lived tokens + refresh rotation where auth applies
no sensitive payload logging
append-only audit events
```

## 10. Historical note (Sprint 0)

Sprint 0 originally constrained the repository to foundation-only work. That phase is **complete and historical**. Do not re-apply Sprint 0 “no business logic” as the current repository status. Current constraints are the S12-R / Design Book / ADR set above.
