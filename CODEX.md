# CODEX.md — Valora Engineering Rules for Coding Agents

**Created:** 2026-07-06
**Last reconciled:** 2026-09-02 (UI/UX v2.3 PR-01a authority closeout)
**Applies to:** All agent-generated work in the Valora repository

## 1. Source of Truth

Domain behavior must come from this read order:

```text
1. CODEX.md (this file) — live task gate and agent operating rules
2. ENGINEERING_GUARDRAILS.md — permanent security, tenant, audit, mutation invariants
3. docs/design/VALORA_UIUX_HANDOFF_v2.3.md — canonical UI/UX master
4. docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md — v2.3 reading order and scope
5. The v2.3 addendum directly governing the assigned PR
6. docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md — lightweight runtime guard
7. docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md — earlier-version relationship and history
8. docs/VALORA_PROJECT_HANDOFF.md — implementation history and verified baseline context
9. Valora Design Book v1.2-final plus v1.3/v1.4 addenda — established domain foundation
10. Feature contracts under docs/design/ and accepted docs/adr/* decisions
```

Do **not** invent domain behavior. If ambiguous: stop and request an ADR or Design Change Request.

Historical Sprint 0 planning docs under `docs/01_*` … `docs/05_*` and historical S12-R remediation prose are **historical records**, not the live gate.

## 2. Current Engineering Phase

```text
Engineering Phase / VALORA UI/UX v2.3 implementation alignment
```

### Live task gate (fetch origin/main before acting)

```text
Accepted code baseline: `origin/main` at
`93f50f9ac81ab93e2361fffa8b71fc3bcfca57f6` (R-GATE-001 / PR #26).
Canonical UI/UX authority branch: `docs/uiux-handoff-v2.2` at
`1cf50460e54ba19d2f6a9d8f933ab123e4e615d6`.

PR-00 — Authority Alignment Guard: COMPLETE / CLOSED locally.
PR-01 — Case State Projection Foundation: OWNER-ASSIGNED; predicate/design gate remains open.
ADR 0036 accepts computed-on-read with no projection migration. Do not connect the runtime
endpoint until the canonical fact/completion matrix is owner-accepted; resume persistence remains
deferred.
PR-01a / ADR 0037 authority closeout is COMPLETE locally at `f0e7c73`: the
PreliminaryResultArtifact, durable official-intake fact and internal command passed independent
review and the PostgreSQL-backed baseline (`1111 passed`, `0 failed`, `0 skipped`). Do not add
artifact-generation/HTTP/case-state wiring without its next gate.
Next gate: owner acceptance of a bounded stage predicate matrix. PR-02 frontend wiring remains
unauthorized until the PR-01 read contract is implemented and accepted.
Known legacy QC/approval/standalone-validation surfaces are debt and must not expand or drive new UI.
The earlier S13-PR-004/005 execution sequence is historical implementation context, not the current
owner-authorized UI/UX track.
```

Agents must `git fetch origin` and verify live `origin/main`. Listed SHAs are **evidence**, not evergreen truth.

### Permanent S12 Apply v1 (frozen)

```text
Apply command remains ADR 0029 / staging contract §15 / contract_version = s12-pr-004-v1.
Upload/validate never mutate official ProjectAssetLine.
Upload lock order: Project FOR UPDATE → batch FOR UPDATE → staging mutation.
Apply lock order: Project FOR UPDATE → batch FOR UPDATE → ordered staging → inserts.
```

Do **not** re-open S12-PR-003, S12-PR-004, S13-PR-002 or S13-PR-003 as blocked/not started.

## 3. Permanent Hard Rules

```text
No domain invention outside Design Book / ADR / approved contract.
No AI auto-approval or auto-apply of official data.
No AI confirmation of mapping, identity, price, Apply, or active knowledge.
No R2 auto-draft/auto-stage/exception-only-review promotion in S13–S16.
AI/rules/providers/frontends produce typed proposals only; they never call persistence mutations directly.
Any future write-capable automation requires deterministic ExecutionPolicy plus an allowlisted,
  idempotent domain command with tenant/RBAC/state/version checks and atomic required audit.
Human, system and ai_service principals remain distinct; AI/system never impersonates approval.
AITaskRun/DecisionEpisode are provenance around authoritative domain decisions, not replacement truth.
Workflow patterns derive from domain commands and committed outcomes, never UI clickstream.
Temporary selections, autosave, failed/stale runs and unreviewed output are not positive feedback.
Long-running production AI/extraction tasks require durable outbox/job/attempt execution and stale-result protection.
ADR 0028 restricted Workbench fields (description, appraised_unit_price,
  review_status, validation_status) require draft-commit command path + authorization
  + human confirmation + version safety + atomic audit. Direct PATCH of those fields is blocked.
Non-restricted ProjectAssetLine fields may use direct PATCH under project:update and are
  outside the R004 Human Commit Gate / atomic-command guarantee.
Excel upload/validate still never mutate official ProjectAssetLine rows.
Apply (S12-PR-004) is the only approved promotion path for S12 staging; see ADR 0029.
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
No client-identifying data or real customer files in the public repository.
No direct bulk SQL into active knowledge from historical dossiers.
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
Raw observations remain immutable; only human-confirmed decisions become reusable feedback.
Column Mapping Memory and Asset Identity Memory are separate bounded memories (v1.4 / ADR 0030–0031).
AI task/context/attempt/decision provenance follows ADR 0033.
Future automation risk/policy/command/job boundaries follow ADR 0034 and remain deny-by-default.
Final price, QC approval, signature and report/certificate release remain human-only R4 actions.
```

## 5. Evidence Semantics

```text
Local SQLite/unit results: development evidence only.
PostgreSQL behavior: requires CI (or local) run with PostgreSQL service.
Audit PASS for a historical PR does not imply current slice READY.
Do not treat skipped tests as passed.
Do not claim Draft PR / Ready / merge without explicit authorization.
Historical audit prose never overrides code + CI at a cited SHA.
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
Protected files are involved without authorization.
S13 runtime is requested without an assigned runtime task ID, or from a baseline that does not match the task prompt.
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
Fail closed on missing identity, inactive user/org, cross-tenant access.
Frontend visibility is not security.
No production secrets in repository content or fixtures.
```
