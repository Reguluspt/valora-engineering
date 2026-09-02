# VALORA Agent Rules

**Status:** Coordination contract only — subordinate to repository authority  
**Applies to:** OpenCode workers and reviewers, regardless of model

## 1. Mandatory authority behavior

Do not invent domain behavior.

Before acting, obey the active hierarchy beginning with `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`, and the exact authority references in the Task Packet.

If authority is missing, contradictory, stale relative to live code/merged evidence, or insufficient to safely implement the requested behavior: **STOP_AND_ESCALATE**.

## 2. Session bootstrap

For every implementation/review task:

```text
1. Read the Task Packet.
2. Verify repository / branch / live origin/main.
3. Record observed baseline SHA.
4. Read only the exact authority refs first.
5. Search the repo for existing implementation and tests.
6. Expand context only when evidence requires it.
```

Do not load the whole docs tree by default.

## 3. Required execution sequence

```text
INSPECT
  -> CLASSIFY GAP
  -> PLAN SMALLEST SAFE PATCH
  -> IMPLEMENT
  -> TEST/GATE
  -> REVIEW
  -> REPORT
```

### INSPECT

Determine whether requested behavior is:

- `ALREADY_IMPLEMENTED`
- `PARTIAL`
- `MISSING`
- `CONFLICTING`
- `BLOCKED_BY_AUTHORITY`

Do not edit before inspection unless the Task Packet explicitly authorizes a mechanical/docs-only change.

### PLAN SMALLEST SAFE PATCH

Prefer the narrowest change that satisfies the acceptance criteria.

Do not perform unrelated cleanup, broad refactoring, architecture modernization, dependency churn, or formatting sweeps.

### IMPLEMENT

Follow existing module/application-service/domain-command boundaries. Reuse established patterns before adding new abstractions.

### TEST/GATE

Run the task-required gates plus the minimum relevant repository gates. Report raw pass/fail/skip counts when available.

A skipped PostgreSQL/integration test is **not PASS** evidence.

### REVIEW

When practical, use a different model from the implementer. Reviewer must inspect the Task Packet, changed files/diff, tests, and relevant authority — not rely on the implementer summary alone.

## 4. Permanent prohibitions

Unless an accepted authority explicitly changes them, do not:

- invent product/domain rules;
- weaken tenant isolation, authentication, authorization, audit, optimistic versioning, or human confirmation boundaries;
- allow AI/rules/providers/frontends to bypass approved mutation commands;
- auto-approve mapping, identity, price, Apply, active knowledge, QC/signature/release actions;
- silently mutate immutable/append-only evidence or decisions;
- treat Word/Excel as the authoritative database state;
- bypass staging / Apply semantics;
- mix supplier quote semantics with final appraised-price semantics;
- add hidden fallback/mock/demo production data;
- commit secrets or real customer material;
- add a multi-user workflow, approval chain, separate KSCL workflow, role layer, or business process merely because it seems useful;
- claim PR/CI/merge status without evidence;
- create or merge a PR unless the owner/task explicitly authorizes that action.

## 5. Context discipline

Low-cost model context should be evidence-driven.

### Read first

- Task Packet
- exact authority references listed by the Task Packet
- directly relevant code/tests

### Read only if needed

- adjacent ADRs/contracts
- module-wide implementation
- historical audits
- remediation documents

### Avoid unless explicitly required

- entire repository dumps
- full chat histories
- full terminal transcripts
- unrelated sprint documents
- large generated files

Use path + section references in summaries instead of copying long text.

## 6. Data handling

Do not place secrets, tokens, production credentials, real client files, client-identifying data, private evidence, or production database dumps into low-cost/public/free model prompts.

Use anonymized fixtures and the smallest useful excerpt.

If real sensitive data is required to perform the task, stop and escalate instead of improvising a transfer path.

## 7. STOP_AND_ESCALATE triggers

Stop implementation and return a blocked result if any of these occur:

```text
- missing or conflicting domain rule
- authority contradicts requested behavior
- task baseline does not match required baseline and the mismatch matters
- canonical status appears stale and authorization cannot be proven
- architecture change requires an ADR/design decision
- new major dependency has architectural/security impact
- migration may lose/rewrite authoritative data
- tenant/auth/security behavior would change
- official mutation or human-confirmation boundary would change
- AI write capability or approval authority would increase
- immutable/audit lineage semantics would change
- price/evidence semantics are ambiguous
- task requires work outside declared scope
- protected/sensitive data is required
- reviewer finds a RED-risk deviation
```

Use this escalation format:

```text
STATUS: BLOCKED
REASON:
EVIDENCE:
AUTHORITY_REFS:
OPTIONS:
RECOMMENDATION:
OWNER_DECISION_REQUIRED:
```

## 8. Review rules

Reviewer must actively search for:

- scope creep;
- authority deviation;
- invented domain behavior;
- missing loading/empty/error states for UI tasks;
- mutation/audit/version/tenant regressions;
- unsafe fallback behavior;
- missing tests;
- false PASS claims caused by skips;
- migration/schema drift;
- hidden data exposure;
- unrelated refactor noise.

Reviewer verdict:

```text
PASS
PASS_WITH_FIXES
FAIL
BLOCKED
```

For YELLOW/RED tasks, reviewer should be a different model when available.

## 9. Result discipline

Every task must produce `TASK_RESULT.md`-compatible output.

Do not paste raw diffs or full logs into the result unless needed to explain a blocker. Prefer:

- changed file list;
- concise implementation summary;
- tests/gates with counts;
- deviations;
- risks;
- exact evidence references;
- compact Control Plane summary.

## 10. Git discipline

- one task / one responsibility;
- clean task branch when code changes are expected;
- preserve unrelated working-tree changes;
- do not force-push or rewrite history unless explicitly authorized;
- do not merge without owner authorization;
- record baseline and resulting head SHA when available.
