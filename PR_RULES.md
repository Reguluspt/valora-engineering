# PR_RULES.md — Valora Pull Request Rules

**Created:** 2026-07-06
**Applies to:** Every PR in the Valora repository

## 1. PR Size

Each PR should be small and focused.

Preferred:

```text
one task
one module
one responsibility
clear tests
clear design reference
```

Avoid:

```text
large mixed PRs
unrelated cleanup
business logic mixed with infrastructure
silent refactors
hidden dependency changes
```

## 2. Required PR Description

Every PR must include:

```text
Task ID:
Task name:
Sprint:
Design source:
Scope implemented:
Files changed:
Tests run:
Known limitations:
ADR needed: yes/no
```

## 3. Design Source Requirement

Every PR must cite the exact design source.

Current work must cite the applicable source from the repository authority chain, for example:

```text
CODEX.md
ENGINEERING_GUARDRAILS.md
docs/design/VALORA_UIUX_HANDOFF_v2.3.md
docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md
the applicable current v2.3 addendum
docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md
docs/architecture/VALORA_AI_MASTER_PLAN_V1.md      # only for OS-G7 / AI-readiness scope
accepted scoped ADR
current task / implementation contract
```

Older Design Book and Sprint 0 sources may be cited as historical/domain evidence where still applicable,
but they do not override current v2.3 authority or the Unified Roadmap.

## 4. Scope Declaration

Every PR must say what was intentionally not implemented.

Example:

```text
Not implemented:
- no Project CRUD
- no domain DB models
- no auth logic
- no business workflow
```

## 5. Tests

Every PR must include tests when code is added.

Minimum expectations:

```text
backend code → pytest
frontend code → build/lint or component test
worker code → pytest
infra/docs only → smoke check or explanation
```

## 6. Security Checklist

Every PR must confirm:

```text
No secrets committed.
No production credentials added.
No auth bypass introduced.
No tenant boundary bypass introduced.
No sensitive data logging introduced.
No API key/token stored in plaintext.
```

## 7. Migration Checklist

If a PR adds migrations, it must state:

```text
why migration is needed
rollback behavior
whether data is tenant-scoped
whether audit/history is affected
```

Sprint 0 should not include business/domain migrations.

## 8. Dependency Checklist

If a PR adds a dependency, it must state:

```text
dependency name
purpose
license concern if known
why built-in/simple alternative is insufficient
ADR needed or not
```

## 9. Review Classification

Audit result should be one of:

```text
PASS
PASS WITH FIXES
FAIL
```

### PASS

Ready to merge.

### PASS WITH FIXES

Can merge after small non-architectural fixes.

### FAIL

Must not merge. Usually caused by:

```text
scope violation
invented domain behavior
security issue
missing required tests
architecture conflict
```

## 9.1 Exact-head baseline and handoff rule

Every implementation PR/task must state:

```text
Baseline branch:
Baseline SHA:
Baseline exact-head CI run:
Predecessor/dependency:
```

Rules:

```text
Do not begin implementation from an unverified moving HEAD.
The baseline CI must be SUCCESS for the exact recorded SHA.
A parent commit's green CI does not certify a descendant commit.
After code changes, required focused tests/reviews and exact-head CI must pass before closeout.
Do not release a dependent PR/task until the predecessor exact-head gate is green.
If HEAD changes after review/CI, refresh the required evidence for the new exact HEAD.
```

## 10. Merge Blockers

Do not merge if:

```text
PR exceeds sprint scope
PR contradicts current Design Authority, Unified Roadmap, or an accepted scoped ADR
PR implements domain logic not assigned
PR lacks required tests
PR commits secrets
PR weakens security guardrails
PR bypasses audit path
PR makes official data mutable without approved design
```

## 11. Codex Output Requirement

When Codex completes a PR, it must report:

```text
Task ID
Files changed
Design source used
Tests run
Known limitations
Scope compliance statement
Recommended reviewer attention points
```

## 12. Human Approval

Final merge approval belongs to the product/engineering owner.

Codex cannot self-approve.
