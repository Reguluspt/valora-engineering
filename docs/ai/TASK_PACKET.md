# VALORA Task Packet Template

Use one copy of this template per task. Keep it short. Prefer repository paths/sections over pasted background text.

```text
TASK_ID: VALORA-<AREA>-<NNN>
TITLE: <short action title>
RISK: GREEN | YELLOW | RED
STATUS: READY_FOR_INSPECTION
OWNER: <human owner / project owner>
CONTROL_PLANE: ChatGPT | N/A
EXECUTION_PLANE: OpenCode
PREFERRED_WORKER: DeepSeek V4 Flash | Muse Spark 1.2 | cheapest-capable
PREFERRED_REVIEWER: different-model | N/A

TARGET_BRANCH: <task branch or TO_BE_CREATED>
EXPECTED_BASELINE: <sha | live origin/main | explicit ref>
```

## 1. Goal

<One concise paragraph describing the observable outcome.>

## 2. Why this task exists

<1–3 bullets only. Do not paste conversation history.>

## 3. Authority references

Read these first, in order:

```text
1. <exact file path + section/ADR>
2. <exact file path + section/ADR>
3. <only if necessary>
```

Repository authority hierarchy still applies. If these refs conflict with higher authority, stop/escalate.

## 4. Scope — IN

```text
- <module/path/component>
- <behavior to implement/fix>
- <tests/docs required>
```

## 5. Scope — OUT

```text
- <explicitly excluded behavior>
- no unrelated refactor
- no new domain/workflow/approval/role behavior unless explicitly authorized
- no authority rewrite unless this is a docs-authority task
```

## 6. Required inspection before editing

The worker must determine:

```text
IMPLEMENTATION_STATUS: ALREADY_IMPLEMENTED | PARTIAL | MISSING | CONFLICTING | BLOCKED_BY_AUTHORITY
OBSERVED_ORIGIN_MAIN: <sha>
OBSERVED_TASK_BASELINE: <sha>
RELEVANT_FILES: <paths>
RELEVANT_TESTS: <paths>
GAP_SUMMARY: <short>
```

If `EXPECTED_BASELINE` materially differs from the observed baseline, do not silently continue.

## 7. Acceptance criteria

Use testable statements:

```text
AC1. <observable behavior>
AC2. <security/domain invariant preserved>
AC3. <error/loading/empty state if UI-relevant>
AC4. <no regression / compatibility condition>
AC5. <test/gate evidence requirement>
```

## 8. Required tests / gates

```text
- <targeted test command>
- <lint/build/security command>
- <PostgreSQL/CI evidence if required>
```

Do not claim skipped required tests as PASS.

## 9. Implementation constraints

```text
- smallest safe patch
- reuse existing application-service/domain-command boundaries
- no unrelated formatting/refactor churn
- no new major dependency without escalation
- preserve tenant/auth/audit/version/human-confirmation semantics
- preserve immutable/append-only evidence semantics
- no secrets or real customer data in prompts, fixtures, or repo
```

Add task-specific constraints below:

```text
- <constraint>
- <constraint>
```

## 10. STOP_AND_ESCALATE conditions

In addition to `docs/ai/AGENT_RULES.md`, stop if:

```text
- <task-specific ambiguity>
- <task-specific protected boundary>
- <decision that requires owner/ChatGPT>
```

## 11. Execution instructions

```text
1. Inspect first.
2. Classify the gap.
3. Implement the smallest safe patch only if authorized.
4. Run required gates.
5. Cross-review using a different model when required by risk.
6. Produce output matching docs/ai/TASK_RESULT.md.
7. Do not create/ready/merge a PR unless explicitly authorized below.
```

## 12. Git / PR authorization

```text
CREATE_BRANCH: YES | NO | EXISTING
CREATE_PR: YES | NO
MARK_READY: YES | NO
MERGE: YES | NO
PUSH: YES | NO
```

Default unspecified write-side actions to `NO`.

## 13. Required final output

Return a `TASK_RESULT.md`-compatible report containing:

```text
status
baseline/head SHA
gap classification
files changed
implementation summary
tests/gates with raw evidence
authority deviation
scope deviation
security/data concerns
ADR required
reviewer verdict
unresolved issues
CONTROL_PLANE_SUMMARY
```

### Token rule

`CONTROL_PLANE_SUMMARY` should normally be <= 250 words and sufficient for ChatGPT to decide whether deeper review is needed.

Do **not** attach raw diffs, entire logs, or full documents unless the task is blocked/deviated or explicitly requests them.
