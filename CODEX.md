# CODEX.md — Valora Engineering Rules for Coding Agents

**Created:** 2026-07-06
**Last reconciled:** 2026-09-21 (Local G6 accepted; G8 offline Exchange complete; ADR 0045 Working Change Observation/Human Commit accepted)
**Applies to:** All agent-generated work in the Valora repository
**v2.3 gate:** PR-00 — **CLOSED**; PR-01 / PR-02 / PR-03 / PR-04 contracts — **ACCEPTED** and merged.

## 1. Source of Truth

Domain behavior must come from this read order:

```text
1. CODEX.md (this file) — live task gate and agent operating rules
2. ENGINEERING_GUARDRAILS.md — permanent security, tenant, audit, mutation invariants
3. docs/design/VALORA_UIUX_HANDOFF_v2.3.md — canonical UI/UX master
4. docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md — v2.3 reading order and scope
5. docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md — current product/development ordering
6. The v2.3 addendum directly governing the assigned PR
7. docs/implementation/VALORA_UIUX_V2_3_IMPLEMENTATION_CONTRACT.md — lightweight runtime guard
8. docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md — earlier-version relationship and history
9. docs/VALORA_PROJECT_HANDOFF.md — implementation history and verified baseline context
10. Valora Design Book v1.2-final plus v1.3/v1.4 addenda — established domain foundation
11. Feature contracts under docs/design/ and accepted docs/adr/* decisions
```

Do **not** invent domain behavior. If ambiguous: stop and request an ADR or Design Change Request.

Historical Sprint 0 planning docs under `docs/01_*` … `docs/05_*` and historical S12-R remediation prose are **historical records**, not the live gate.

## 2. Current Engineering Phase

```text
Engineering Phase / VALORA UI/UX v2.3 implementation alignment
```

### Live task gate (fetch origin/main before acting)

```text
Accepted merged code baseline remains `origin/main` at
`27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6` (PR #31). Always fetch and verify live main.

Active integration candidate: Draft PR #32 / `feat/operational-frontend-m365`.
It contains the operational frontend, Local immutable DocumentBlobStore, OneDrive Personal Exchange
and the later documentation reconciliation. Treat the live PR head as mutable; milestone SHAs below
are evidence, not evergreen branch heads.

PR-00 through PR-04 — MERGED by PR #29. PR-01 remains only the four-stage prefix foundation;
canonical stages 5-16 are still unavailable until their domain facts/providers are implemented.
PR-05 — MERGED by PR #30; delegated OneDrive Personal read/OAuth foundation accepted.
PR-06 — MERGED by PR #31; return/revalidation baseline and live read acceptance accepted.

Operational Frontend — IMPLEMENTED ON DRAFT PR #32 and locally browser-accepted against a simulated
provider. It is not yet merged into main and does not by itself prove the full North-star E2E.

VALORA-STORAGE-LOCAL-001 — G6 ACCEPTED. Reviewed snapshot commit
`d71a42e575f96d7cd8d9aac6c8aab2c60627c32f`; durable closeout evidence is recorded by
`VALORA_STORAGE_LOCAL_G6_CLOSEOUT_MANIFEST.json`. Local immutable blobs are the current VPS pilot
document-byte provider; PostgreSQL + DocumentRevision/CurrentHead remain authority.

VALORA-ONEDRIVE-EXCHANGE-001 — G8 OFFLINE IMPLEMENTATION COMPLETE at code milestone
`f896f15b0b18e8eb3a32619bee2418f3a4b92da4`. Exact-head CI run #302 passed all jobs; backend
reported 1659 passed and frontend 140 passed. G8 proves offline Exchange/storage behavior only;
live Files.ReadWrite.AppFolder/provider conformance remains a separately authorized G9 decision.

ADR 0045 + the Working Change Observation design addendum are now current authority for DOCX
Working-copy changes:
Word Save/provider notification -> observation/revalidation -> DocumentChangeCandidate -> Old/V/W review
-> explicit human-confirmed revision command -> G8 NEXT_REVISION storage boundary.
Word Save, notification, revalidation and DocumentChangeCandidate creation never create DocumentRevision
or mutate authoritative business data automatically.

The original PR-07 direct OneDrive replacement/write path remains blocked/historical. Its protected
value and three-way comparison semantics remain reusable, but new document-change runtime must be
re-baselined around ADR 0045 and a task-specific implementation contract before coding. Do not start
webhook/subscription/delta watcher runtime from ADR 0045 alone.

PR-08 through PR-13 remain not implemented as complete product stages. Software Completion still
requires the North-star product path, release/publishing, traceability/state/fidelity and exact-SHA
E2E acceptance before Windows Preview.

Known legacy Review Queue / standalone Validation Dashboard / old Workbench right-panel IA are debt
and must not expand or be treated as current product authority.

OneDrive Exchange is non-authoritative. Encrypted off-site Backup remains a separate unopened task.
No AWS live activity, live Exchange reconsent/provider probe, production deploy or release is
authorized unless the Product Owner explicitly opens that gate.
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
Microsoft Fluent 2 light compliance for Workbench/product UI; desktop-first, Vietnamese-first, data-heavy/table-first. Astryx is not current product visual authority.
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

## 10. Project AI Execution Policy

This section is the canonical reusable execution policy for AI-assisted VALORA work. Task-specific
instructions may narrow or override routing only when they are explicit, documented and consistent
with accepted architecture and security authority. A task override never grants cloud, credential,
merge, deploy or release authority that the task does not already have.

### 10.1 Roles and current implementations

```text
Lead / Architect / Product Owner
  -> Codex: writer, orchestrator, authority interpreter and final gate owner
  -> MECHANICAL_WORKER: Gemini 3.8 Flash High through Antigravity CLI
  -> Codex verification
  -> INDEPENDENT_REVIEWER_A: DeepSeek v4.1 Flash through OpenCode CLI
  +  INDEPENDENT_REVIEWER_B: Gemini 3.1 Pro High through Antigravity CLI
  -> Codex final gate, commit and push
```

Role semantics are stable; model IDs and CLIs are current implementations and may change. At the
start of a delegated run, query the CLI-supported model list and use the exact current ID rather
than inventing or assuming one. Current implementations on 2026-09-19 are:

| Role | Current implementation | Authority |
|---|---|---|
| Writer/orchestrator/final gate | Codex | Interprets authority, plans, writes, verifies, accepts/rejects findings, commits and pushes when authorized |
| `MECHANICAL_WORKER` | `gemini-3.8-flash-high` via `agy` | May edit only exact bounded files in its task packet; never commits or pushes |
| `INDEPENDENT_REVIEWER_A` | `opencode-go/deepseek-v4.1-flash` via `opencode` | Read-only independent review |
| `INDEPENDENT_REVIEWER_B` | `gemini-3.1-pro-high` via `agy` | Read-only independent review |

Only Codex may commit or push delegated output unless the Product Owner explicitly changes this
policy. A worker must never merge, change PR state, deploy, release, use cloud credentials, mutate a
live provider, broaden scope or reinterpret accepted ADR semantics.

### 10.2 Routing rule

```text
HIGH MECHANICAL LOAD + LOW ARCHITECTURE AMBIGUITY
  -> delegate to MECHANICAL_WORKER

LOW CODE VOLUME + HIGH DECISION IMPACT
  -> Codex retains the work
```

Delegate boilerplate, repetitive tests from a locked matrix, fixtures, DTO/request plumbing,
deterministic transformations, documentation synchronization, mechanical refactors, renames,
lint/import/type corrections and targeted test execution. Codex retains architecture, ADR meaning,
security boundaries, transaction and concurrency semantics, idempotency, lost-response recovery,
authorization, storage authority, IAM/KMS policy, migration strategy and production gates.

For `VALORA-STORAGE-S3-SPIKE-001` G4, the task-specific instruction that Codex is the sole writer
overrides mechanical-worker write authority. DeepSeek and Gemini remain read-only reviewers.

### 10.3 Required worker task packet

Every delegated implementation uses a bounded packet with all of these fields:

```text
TASK ID
GOAL
AUTHORITY
CONTEXT
ALLOWED FILES
FORBIDDEN FILES
IMPLEMENTATION INSTRUCTIONS
INVARIANTS
TESTS TO RUN
STOP CONDITIONS
OUTPUT FORMAT
```

The packet must name exact files, invariants, tests and stop conditions. Prompts such as `fix
project`, `complete everything` or `solve all issues` are prohibited. The default workspace is
`F:\Project Valora\valora-operational-frontend`.

After worker execution, Codex must inspect the actual `git diff`; a worker summary is not acceptance
evidence. Codex then runs relevant tests and static gates before seeking independent review.

### 10.4 Review independence and snapshot discipline

Worker self-checks are labeled `WORKER SELF-CHECK`. If Gemini 3.8 Flash High implemented a change,
its own self-review is not independent acceptance evidence for that change. Independent acceptance
uses both configured reviewers unless a task explicitly defines another accepted gate.

DeepSeek and Gemini 3.1 Pro High are read-only. They must not modify/create files, apply patches,
commit, push, use credentials, run cloud commands, mutate networks/resources or decide a Product
Owner gate. Codex verifies every finding before applying it and classifies findings as `VALID`,
`INVALID`, `DUPLICATE`, `OUT_OF_SCOPE` or `ADVISORY`.

Both reviewers must receive the same frozen snapshot: Git HEAD, relevant-file manifest, SHA-256
hashes and governing docs/code. If any reviewed file changes, both reviews are invalid and must be
rerun on a new manifest. Do not report Codex review or worker self-review as independent evidence.
If a required provider is unavailable, record `INDEPENDENT REVIEW INCOMPLETE`; never fabricate or
substitute a verdict.

### 10.5 Stop and escalation rules

A worker stops on conflicting authority, undefined contract, architecture or security ambiguity,
persistence-semantic change, cloud credential/live-provider requirement, production migration or
unexpected blast radius. It must not work around the conflict. Codex escalates to the Lead/Architect
when a decision exceeds accepted authority.

The normal sequence is:

```text
Codex plans
  -> bounded worker implementation when routing permits
  -> Codex inspects diff and verifies/tests
  -> both independent reviewers inspect one exact snapshot
  -> Codex resolves verified findings and reruns invalidated reviews
  -> Codex commits
  -> Codex pushes only when authorized
```

### 10.6 Current provider command forms

DeepSeek read-only reviewer:

```text
opencode run -m opencode-go/deepseek-v4.1-flash "<strict read-only review prompt>"
```

Gemini read-only reviewer:

```text
agy -p "<strict read-only review prompt>" --mode plan --model gemini-3.1-pro-high --effort high --print-timeout 0 --add-dir "F:\Project Valora\valora-operational-frontend"
```

Gemini mechanical worker, after `agy models` confirms the exact ID:

```text
agy -p "<bounded worker task packet>" --mode accept-edits --model gemini-3.8-flash-high --effort high --print-timeout 0 --add-dir "F:\Project Valora\valora-operational-frontend"
```

If Antigravity headless read permissions block a reviewer, `--dangerously-skip-permissions` may be
used only to bypass the read gate with the same strict read-only prompt. It never grants repository,
credential, network or cloud mutation authority.
