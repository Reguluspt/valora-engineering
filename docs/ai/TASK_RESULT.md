# VALORA Task Result Template

Use this format after implementation/review. Keep the main result concise and evidence-based.

```text
TASK_ID: VALORA-<AREA>-<NNN>
TITLE: <task title>
RISK: GREEN | YELLOW | RED
STATUS: PASS | PASS_WITH_FIXES | BLOCKED | FAIL
IMPLEMENTATION_STATUS_AT_START: ALREADY_IMPLEMENTED | PARTIAL | MISSING | CONFLICTING | BLOCKED_BY_AUTHORITY

WORKER_MODEL: <actual model>
REVIEWER_MODEL: <actual model | N/A>
OBSERVED_ORIGIN_MAIN: <sha>
TASK_BASELINE: <sha>
RESULT_HEAD: <sha | N/A>
BRANCH: <name | N/A>
```

## 1. Outcome

<2–6 bullets describing what is now true.>

## 2. Files changed

```text
- <path> — <why>
- <path> — <why>
```

If none, write `NONE`.

## 3. Implementation summary

<Short explanation of the smallest safe patch. Do not paste code unless needed to explain a blocker.>

## 4. Authority used

```text
- <file/ADR + section>
- <file/ADR + section>
```

```text
AUTHORITY_DEVIATION: NONE | YES
```

If `YES`:

```text
DEVIATION:
WHY:
OWNER_DECISION_REQUIRED:
```

## 5. Scope compliance

```text
SCOPE_DEVIATION: NONE | YES
OUT_OF_SCOPE_WORK_PERFORMED: NONE | <details>
UNRELATED_REFACTOR: NONE | <details>
```

If any deviation exists, explain why and whether it was required.

## 6. Tests / gates

Report exact commands and raw results where possible.

```text
- <command>
  RESULT: PASS | FAIL | SKIPPED | NOT_RUN
  EVIDENCE: <counts / relevant lines>

- <command>
  RESULT: ...
```

Summary:

```text
TESTS_PASSED: <number | unknown>
TESTS_FAILED: <number>
TESTS_SKIPPED: <number>
REQUIRED_GATE_MISSING: NONE | <gate>
```

Do not translate required skips into PASS.

## 7. Security / data / mutation review

```text
TENANT_AUTH_IMPACT: NONE | <details>
OFFICIAL_MUTATION_IMPACT: NONE | <details>
HUMAN_CONFIRMATION_IMPACT: NONE | <details>
AUDIT_LINEAGE_IMPACT: NONE | <details>
SCHEMA_MIGRATION_IMPACT: NONE | <details>
SENSITIVE_DATA_EXPOSURE: NONE | <details>
AI_AUTHORITY_CHANGE: NONE | <details>
```

Any material change above normally requires YELLOW/RED scrutiny according to `ROUTING_RULES.md`.

## 8. ADR / architecture

```text
ADR_REQUIRED: NO | YES | UNCERTAIN
ARCHITECTURE_CHANGE: NONE | <details>
NEW_MAJOR_DEPENDENCY: NONE | <details>
```

## 9. Reviewer result

```text
REVIEW_VERDICT: PASS | PASS_WITH_FIXES | FAIL | BLOCKED | N/A
REVIEWER_ATTENTION_POINTS:
- <point>
- <point>
```

If review was required but not performed, state why.

## 10. Known limitations

```text
- <limitation>
```

If none: `NONE`.

## 11. Unresolved / escalation

```text
UNRESOLVED: NONE | <issue>
OWNER_DECISION_REQUIRED: NO | YES
CHATGPT_ESCALATION_REQUIRED: NO | YES
```

If blocked/escalated:

```text
QUESTION:
EVIDENCE:
OPTIONS:
RECOMMENDATION:
```

## 12. Git / PR state

```text
PUSHED: YES | NO | N/A
PR_CREATED: YES | NO
PR_NUMBER: <number | N/A>
PR_READY: YES | NO | N/A
MERGED: YES | NO
```

Never claim a remote state without evidence.

---

# CONTROL_PLANE_SUMMARY

**Target: <= 250 words. This is the default payload returned to ChatGPT.**

Use this exact compact form:

```text
TASK: <id> — <title>
RISK: <GREEN/YELLOW/RED>
STATUS: <PASS/PASS_WITH_FIXES/BLOCKED/FAIL>

RESULT:
<2–4 concise bullets>

FILES_CHANGED:
<short list or count + key paths>

TESTS:
<commands/counts condensed>

REVIEW:
<verdict + reviewer model>

AUTHORITY_DEVIATION: NONE | YES
SCOPE_DEVIATION: NONE | YES
ADR_REQUIRED: NO | YES | UNCERTAIN
SECURITY_RISK: NONE | <short>
UNRESOLVED: NONE | <short>
OWNER_DECISION_REQUIRED: NO | YES

NEXT_ACTION:
<close / fix / owner decision / ChatGPT review / CI / merge review>
```

## 13. When ChatGPT needs more than the summary

Attach deeper evidence only when:

- status is not `PASS`;
- authority or scope deviation is non-empty;
- ADR/security/domain decision is required;
- reviewer verdict is not PASS;
- required test/gate is missing/failing;
- owner/ChatGPT explicitly requests the diff or logs.

Otherwise, do **not** send raw diff/log/document context to ChatGPT.
