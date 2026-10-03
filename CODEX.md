# CODEX.md — Valora Engineering Rules for Coding Agents

**Created:** 2026-07-06
**Last reconciled:** 2026-10-02 (A5R2 certified; A5 product closure resumed)
**Applies to:** All agent-generated work in the Valora repository
**v2.3 gate:** PR-00 — **CLOSED**; PR-01 / PR-02 / PR-03 / PR-04 contracts — **ACCEPTED** and merged.

## 1. Source of Truth

This is authority precedence when a source is relevant, not a required reading list for every task.
The Gate Owner/Architect resolves project-wide authority and supplies a compact task contract;
Codex reads the contract and only the authority sections needed for its bounded implementation.

```text
1. Explicit current Product Owner decision — wins only in the scope it names
2. CODEX.md (this file) — live task gate and agent operating rules
3. ENGINEERING_GUARDRAILS.md — permanent security, tenant, audit, mutation invariants
4. docs/design/VALORA_UIUX_HANDOFF_v2.3.md — canonical UI/UX master
5. docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md — v2.3 reading order and scope
6. The current v2.3 addendum directly governing the assigned scope
7. docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md — current product/development ordering
8. docs/architecture/VALORA_AI_MASTER_PLAN_V1.md — OS-G7 / AI-readiness architecture detail; never runtime authorization by itself
9. Accepted scoped ADR governing the assigned boundary
10. Current task / implementation contract, including the lightweight v2.3 runtime guard where applicable
11. Current handoff / acceptance evidence
12. Historical Design Book / sprint / audit / remediation / research evidence

docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md is a supersession/navigation map for these sources; it
does not outrank the authority listed above.
```

Do **not** invent domain behavior. If ambiguous: stop and request an ADR or Design Change Request.

Historical Sprint 0 planning docs under `docs/01_*` … `docs/05_*` and historical S12-R remediation prose are **historical records**, not the live gate.

## 2. Current Engineering Phase

```text
Engineering Phase / VALORA UI/UX v2.3 implementation alignment
```

### Live task gate (fetch main and the assigned task branch before acting)

```text
`origin/main` is the accepted merged code baseline. Fetch and verify its live HEAD before acting.
OS-G0 / PR #32 is MERGED/CLOSED via squash. The source integration branch
`feat/operational-frontend-m365` is completed historical branch evidence, not an active integration
authority. Record the exact implementation baseline and its exact-head CI in each task packet; never
infer current branch state or a later HEAD's CI result from a SHA recorded here.

Last verified merged-main OS-G0 closeout (2026-09-27): `origin/main` is
`51eab8648005186197d2fbb37a19bde4332aeaa5`, the squash result of PR #32, with exact-head
CI #485 SUCCESS. The pre-squash integration source head was
`0ccc9c14aba520d2f6ae405129018e5d5ec26cb2`. These SHAs and the CI result are dated evidence only.

PR-00 through PR-04 — MERGED by PR #29. PR-01 remains only the four-stage prefix foundation;
canonical stages 5-16 are still unavailable until their domain facts/providers are implemented.
PR-05 — MERGED by PR #30; delegated OneDrive Personal read/OAuth foundation accepted.
PR-06 — MERGED by PR #31; return/revalidation baseline and live read acceptance accepted.

Operational Frontend — MERGED TO MAIN BY PR #32. F2-PR-001 removed the legacy global Review
Queue/Validation Dashboard production routes; F2-PR-002 established Fluent 2 light tokens;
F2-PR-003 replaced the production Astryx shell/login/shared-state primitives.
F2-PR-001 — CLOSED ON MAIN THROUGH PR #32.
F2-PR-002 — CLOSED ON MAIN THROUGH PR #32.
F2-PR-003 — CLOSED ON MAIN THROUGH PR #32.
F2-PR-004 — CLOSED ON MAIN THROUGH PR #32 (Case Overview / Project List).
F2-PR-005 — CLOSED ON MAIN THROUGH PR #32 (Workbench asset context / drawer).
F2-PR-006 — CLOSED ON MAIN THROUGH PR #32 (NCC selection).
F2-PR-007 — CLOSED ON MAIN THROUGH PR #32 (provider-neutral Document Workspace / M365 return).
F2-PR-008 — CLOSED ON MAIN THROUGH PR #32 (Fluent 2 residual sweep / Astryx retirement).
OS-G0 Fluent 2 engineering closeout is COMPLETE ON MAIN at `51eab8648005186197d2fbb37a19bde4332aeaa5`,
with exact-head CI #485 SUCCESS. G1.0 current-result integrity gate was subsequently merged by
PR #51 at `7db69708b4668b77f49c97ec59b195be2b0f6037` (exact-head CI #491 SUCCESS).
OS-G1 authority history: ADR 0046 accepts optional Pre-case Customer, an explicit current
batch pointer and versioned analysis/result currentness. G1.1A implements only nullable Customer
snapshots, the current-batch persistence pointer, null-safe lineage constraints and first-batch
initialization under `VALORA-TASK-OS-G1-1A-PRECASE-IDENTITY-CURRENT-BATCH-FOUNDATION`.
G1.1B implements internal `BindPreliminaryProjectCustomer` and
`SwitchCurrentPreliminaryImportBatch` commands with durable replay receipts, Project-locked
transactions and atomic audit under `VALORA-TASK-OS-G1-1B-PRECASE-LIFECYCLE-COMMANDS`. Official
Intake accepts a valid historical result with a NULL Customer snapshot while requiring an ACTIVE
same-tenant bound Customer for the first commit. G1.1C makes the explicit Project current-batch pointer
authoritative for PRELIMINARY_REQUEST, allocates immutable Preliminary Analysis versions under the
Project lock, and selects the highest valid analysis version matching the current batch/source and
materialized mapping lineage. G1.1D generates immutable Preliminary Result versions against that
selected analysis, allocating `max(version)+1` under the Project lock after object IO and revalidation.
`PRELIMINARY_READY` selects the highest valid Result version matching the current Analysis; valid
historical Results do not create ambiguity. First Official Intake accepts exactly that selected
Result, and new Result generation closes after Intake while true prior command replay remains valid.
G1.1E exposes optional-Customer Project creation and authenticated project-scoped Customer binding,
explicit current-batch switching, Preliminary Analysis finalization, Preliminary Result generation
and Official Intake through the existing application commands. The public case-state read includes
authoritative current Pre-case IDs, versions and the Project CAS token. Standard `owner` and
`appraiser` roles receive the dedicated Analysis, Result and Official Intake permissions through a
data-only migration; other standard roles do not. G1.1F adds the first bounded Pre-case frontend
entry: authenticated users can open a Fluent 2 light `Tạo yêu cầu sơ bộ` surface from the Project
list; users with `project:create` permission can create an unbound Pre-case Project through the G1.1E
optional-Customer API. This slice stops before dedicated `Quản lý yêu cầu sơ bộ` state management,
Upload & Mapping, Analysis/Result/Official Intake UI and browser acceptance. G1.1G exposes
authenticated Project/batch-scoped Column Mapping proposal, human confirmation or correction,
rejection and staging materialization commands through the existing application services. Mapping
mutations require the explicit current Preliminary batch, allow unbound Pre-case Projects without
Customer memory, forbid Customer-scoped memory until binding, retain NULL historical Customer
snapshots and close new mapping mutations after Official Intake. True command-ID replays remain
available for already committed mapping facts. G1.1G does not add Upload & Mapping UI or alter Apply.
ADR 0047 is ACCEPTED by the Product Owner on 2026-09-29. The F0 mapping-authority runtime is
MERGED/CERTIFIED through PR #62 and exact-main CI #514 at
`1f85e3d547c188d23424ec2e9cc7aa53cf92efc7`. It adds a versioned Project selection slot,
conservative legacy bootstrap, CAS-protected confirmation/materialization, pointer invalidation and
a Project/batch recovery GET. G1.1H Pre-case Intake & Mapping UX is MERGED/CERTIFIED
through PR #63 and exact-main CI #516 at `ccf857a95365251f305132178aa0010182b3df0e`.
G1.1I Preliminary Analysis & Review UX is MERGED/CERTIFIED through PR #64 and exact-main CI #518
at `181c48ce007d8885c49c0dbd52040a38fbaf8cec`. VF0 Frontend Visual Fidelity Alignment is
MERGED/CERTIFIED through PR #65 and exact-main CI #520 at
`e87f645f8ac44bfb7dd5d2688dbaa4e7411873a6`. G1.1J Result & Official Intake UX is
MERGED/CERTIFIED through PR #66 and exact-main CI #523 at
`21eb2e264a0f819cd3caa053fa0769128c5d06a0`. RBAC-001 standard operator Workbench edit
alignment is MERGED/CERTIFIED through PR #67 and exact-main CI #525 at
`5fcb110c379b25079dd1b374de8a2e5b9c494dfd`. The data-only grant gives the existing
`workbench:edit` permission to standard `owner` and `appraiser` roles; endpoint checks and other
standard-role grants are unchanged. G1.1K / PR #68 is MERGED/CERTIFIED at
`d283c690b9f014833fa5c98e1125939351966b81` with exact-main CI #527 SUCCESS. OS-G1 is
CERTIFIED/CLOSED at this baseline. OS-G2 A0 accepted entry authority / PR #72 is MERGED/CERTIFIED
at `a293395c53ab12aa27cac86d82046a6a9f59983b`, exact-main CI #533 SUCCESS. The accepted decision
record is `docs/plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md`.
OS-G2 A1 / Issue #73: the Product Owner accepted ADR 0048
(`docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md`) and
`docs/implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md` on 2026-10-02 in the task chat.
PR #74 is MERGED/CERTIFIED at `f8d708c06ab00f3315c712647ef198b50549ed6c`, exact-main CI #536 SUCCESS.
OS-G2 A2 / Issue #75 / PR #76 is MERGED/CERTIFIED at
`b3085242d083e03f1663aa79ea3241bd48592c84`, exact-main CI #538 SUCCESS. It implements only guarded
Apply v2, the atomic initial-set seal and shared Case State v2 / `asset_review_v1` backend slice.
OS-G2 A3 / Issue #77 authority was ACCEPTED by the Product Owner on 2026-10-02. ADR 0049 and
`docs/implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md` are accepted authority.
PR #78 is MERGED/CERTIFIED at `27bebb73e35c540c7cea870b1b2fd5a26a55b2c9`, exact-main CI #542
SUCCESS; ADR 0049 and the Line Decision Contract are certified accepted authority.
OS-G2 A4 / Issue #79 / PR #80 is MERGED/CERTIFIED at
`416157e6330f861127455a66fd5df9c0972bc02a`, exact-main CI #545 SUCCESS. A5R / Issue #82 / PR #83 is
MERGED/CERTIFIED at `d20f121b0f62c539836fde35308edbfc6d928e5d`, exact-main CI #549 SUCCESS.
A5R D1 was ACCEPTED by the Product Owner on 2026-10-02. A5R2 / Issue #84 is CLOSED/CERTIFIED:
PR #85 squash merged at `7c52a41a84b21b63182429d5c5740e76783ea4e6`, exact-main CI #552 SUCCESS.
Alembic head `b5c6d7e8f9a0` grants existing `workbench:open` to standard `owner` and `appraiser` only.
OS-G2 A5 / Issue #81 resumes the authorized ASSET_REVIEW product-closure UX/E2E slice in the
existing Workbench. Membership mutation, further RBAC and ASSET_WORKBENCH+ remain UNAUTHORIZED.
With a NULL current-batch pointer, a Project with no batches is INCOMPLETE; retained batches mean
current-batch authority is unresolved and PRELIMINARY_REQUEST is NOT_AVAILABLE pending audited
remediation. A Result lineage manifest records the Result artifact's Customer snapshot at generation;
READY verification does not compare it to the Analysis snapshot's historical Customer.
Each new runtime slice requires a Gate Owner compact task contract under current Product Owner
authority. These SHAs are dated evidence, not a live-head claim. G1.0 alone did not close OS-G1;
the G1.1K merge and exact-main CI above certified its Pre-case product journey.

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

Legacy global Review Queue / standalone Validation Dashboard production routing was removed by
F2-PR-001. Workbench asset context / drawer IA was remediated by F2-PR-005; none of the retired
legacy concepts may be revived as product authority.

OneDrive Exchange is non-authoritative. Encrypted off-site Backup remains a separate unopened task.
No AWS live activity, live Exchange reconsent/provider probe, production deploy or release is
authorized unless the Product Owner explicitly opens that gate.
```

Agents must `git fetch origin` and verify live `origin/main` and the assigned task branch HEAD. Listed
SHAs are **evidence**, not evergreen truth.

### Deployment/client v1 authority — Issue #89 (2026-10-03)

The Product Owner accepts [ADR 0050](docs/adr/0050-linux-server-windows-native-client.md): single-node Linux Server / Docker Engine + Compose, HTTPS LAN, WinUI 3 + WebView2 Evergreen, server-hosted React / Fluent 2 light, small typed allowlisted native bridge and MSIX; Windows 11 x64 first, admin-configured URL and no automatic LAN discovery. Native shell and web frontend are not business authority. Server owns auth/session, tenant/RBAC, domain commands/validation, Case State/Next Action, audit/CAS, PostgreSQL, immutable documents, worker/jobs and providers. No backend/database/worker in MSIX, React rewrite or Docker Desktop local-stack production direction.

Server v1: local inference runtime NOT DEPLOYED; model weights/GPU NOT REQUIRED; core workflow AI dependency NONE; future provider-backed AI remains OS-G7 gated. Preserve ADR 0026 session/CSRF and ADR 0043/0045 immutable storage/human revision authority. No broad host objects, arbitrary process/file/PowerShell bridge, injected auth/provider secrets or certificate bypass.

[Windows Client plan](docs/plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md) and [Linux Server plan](docs/plan/VALORA_LINUX_SERVER_V1_PLAN.md) are planned, not runtime authorization. Architecture/skeleton before Software Completion needs an explicit Product Owner task. Formal [Windows Preview/UAT](docs/implementation/VALORA_WINDOWS_PREVIEW_TASK_BRIEF.md) stays after Software Completion; Linux Deployment Pilot is separate. Architecture selection no longer follows Preview. Issue #89 is docs-only, does not open ASSET_WORKBENCH+ or reorder OS-G0→OS-G7, and permits Draft PR only. Repository-wide reconciliation is Issue #90 after ADR certification on main; historical evidence stays unchanged.

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
Long-running production AI/extraction tasks must reuse the existing durable `TaskJob`/`TaskJobAttempt`/worker execution boundary, including lease/retry/dead-letter/stale-generation protection; do not create a second AI queue.
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

## 6. Bounded Output After Every Task

```text
Task ID and exact baseline/CI
Files changed and scoped authority references; scope respected and ADR need
Tests/gates run with raw results; known limitations and unresolved stops
Local/remote HEAD and PR/CI status when applicable
Ready or blocked for the assigned gate, without claiming a later gate
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

### 8.1 Exact-head baseline and dependent-task gate

```text
A task may be handed to implementation only from an explicitly recorded baseline SHA whose required
CI has completed SUCCESS on that exact SHA.

A successful CI run on a parent/earlier commit does not certify a later HEAD. There is no
"green by inheritance", including for docs-only commits when they become the execution baseline.

Every implementation task packet must record:
- baseline branch;
- exact baseline SHA;
- exact-head CI run number/status;
- dependency/predecessor task state.

Normal delivery sequence:
green exact-head baseline
→ bounded implementation
→ focused tests/static/browser/visual gates required by the task
→ review on a frozen snapshot where required
→ resulting exact-head CI SUCCESS
→ task/PR closeout
→ only then release dependent task(s) to implementation.

If HEAD changes after CI/review, the prior evidence remains historical evidence only; re-run or
revalidate the gates required for the new exact HEAD before closeout or dependent-task handoff.
```

## 9. Security Requirement

```text
Fail closed on missing identity, inactive user/org, cross-tenant access.
Frontend visibility is not security.
No production secrets in repository content or fixtures.
```

## 10. Project AI Execution Policy

OpenViking is NON-AUTHORITATIVE developer tooling for Codex, never a Valora product/runtime
dependency. Live repository/CODEX/accepted scoped authority always wins. Default mode is
`VALORA_LEAN_MCP`: manual MCP recall only after live authority bootstrap; automatic recall/capture
and memory injection remain off. Follow the [OpenViking profile](docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md)
for supported hook controls, budgets, privacy, fallback and the six canonical local skills.
EVERY Dev/Codex handoff must begin with a populated `CODEX MODEL` block naming the exact model,
reasoning, selection reason and escalation, including resumed tasks and tiny corrections;
without it the prompt is INVALID. See [Dev handoff skill](.agents/skills/valora-dev-handoff/SKILL.md).

The [Lean Agent Protocol](docs/plan/VALORA_LEAN_AGENT_PROTOCOL_V1.md) defines the operating
tiers; the [Compact Task Contract](docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) is the
task handoff. Sections 3–9 and the permanent ENGINEERING_GUARDRAILS.md invariants remain binding.
A task contract may narrow scope or require stronger gates, never weaken domain, security, tenant,
audit, idempotency, human-approval or exact-SHA requirements.

### 10.1 Responsibilities

- Gate Owner / Architect interprets project-wide authority, classifies risk, supplies a compact
  contract and owns integration decisions. An agent task never grants itself the next product gate.
- Codex verifies the exact baseline and CI, implements the bounded contract, inspects the actual
  diff, runs risk-appropriate checks, adjudicates review findings and reports the exact result.
  Codex commits or pushes only when the task authorizes it.
- A mechanical worker is optional for specified repetitive work on exact files. It cannot reinterpret
  authority, commit, push, change PR state, merge, deploy or use live credentials; its self-check
  is not independent.
- Independent reviewers are read-only and cannot mutate files, credentials, networks or cloud
  resources. A required unavailable reviewer leaves the review INCOMPLETE.

Current provider implementations are unchanged: optional mechanical worker
`gemini-3.8-flash-high` via `agy`; independent reviewers `opencode-go/deepseek-v4.1-flash`
via `opencode` and `gemini-3.1-pro-high` via `agy`. Query the model list when invoking a provider;
do not add one by inference. If Antigravity headless read permissions block a reviewer,
`--dangerously-skip-permissions` may bypass only that read gate with the same strict read-only
prompt; it grants no write or resource-mutation authority.

### 10.2 Task-scoped context and resume

Begin with the compact contract, applicable permanent rules, its named authority sections, affected
code and tests. The Section 1 list is precedence, not a requirement to read every source. Expand
to neighboring subsystems only for a named dependency. Read whole files/authority sets or scan the
repository only when the task explicitly requires it or a concrete conflict cannot be resolved
within scope; record the reason. If the contract omits a needed domain or permission decision, stop
for Gate Owner clarification rather than reconstructing or inventing it.

Every contract declares risk, baseline branch/SHA and exact CI, authority, allowed/forbidden scope,
acceptance, tests and stop conditions. Keep a compact TASK_STATE with verified SHA, completed checks,
blocker and next action when pausing. On resume, fetch and revalidate HEAD and CI; stale state is
not authority.

### 10.3 Proportional verification

- T0: focused edit-loop checks.
- T1: affected subsystem regression.
- T2: candidate lint, type, build and security gates appropriate to the changed scope.
- T3: full local, real-stack or E2E only for Product/Security/high-risk closeout or an explicit task
  requirement. Full suites are not mandatory on every edit loop.
- T4: exact-head PR CI and, after merge, exact-main CI wherever the existing gate requires them.
  No parent/earlier green run certifies a changed HEAD, including a docs-only baseline.

Low risk uses Codex verification and required CI. Medium risk adds one independent reviewer only
when materially useful and named in the contract. High/Product/Security risk requires a frozen
snapshot, two independent reviewers, Gate Owner and applicable CI/E2E. Thus dual review is not the
default for Low/Medium work. Reviewers receive the same exact HEAD, changed-file/hash evidence and
scoped authority. A changed reviewed file invalidates its prior review; Codex classifies findings
as VALID, INVALID, DUPLICATE, OUT_OF_SCOPE or ADVISORY and reruns required review on the new HEAD.

### 10.4 Delivery

Prefer one PR per coherent vertical capability where practical, with machine-generated evidence
and a bounded final report. Tests or an explicit docs-only N/A are required. Keep the PR Draft
until its authorized gate owner advances it; do not infer Ready, merge, deployment or later-phase
authorization from implementation completion. Stop on baseline mismatch, conflicting authority,
security/tenant ambiguity, missing prerequisite, unapproved architecture change or scope expansion.
