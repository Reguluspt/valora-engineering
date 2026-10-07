# VALORA Gate Review Checklist

**Lifecycle/status:** CURRENT SUPPORTING GATE-REVIEW TEMPLATE — 2026-10-05.
**Authority role:** Review checklist only. It does not grant Ready, merge, product or runtime authority.

Use this checklist when a Dev/Codex handoff reports `READY FOR GATE REVIEW: YES`.

## 1. Live authority

- [ ] Rebaseline live repository before review.
- [ ] `PROJECT AUTHORITY READY: YES`.
- [ ] Current task/Issue is still authorized.
- [ ] Product/domain authority has not changed since candidate freeze.
- [ ] Current `main` / prerequisite state does not invalidate this candidate.
- [ ] No missing prerequisite or conflicting accepted ADR/decision.

If any item fails: **STOP — GATE BLOCKED**.

## 2. Candidate identity

Record:

```text
Task:
Issue:
PR:
Base SHA:
Frozen candidate HEAD:
Live PR HEAD:
```

- [ ] Live PR HEAD equals the frozen candidate HEAD exactly.
- [ ] PR base is the expected integration branch.
- [ ] Candidate was not changed after required review/CI evidence.

If HEAD differs: **STOP — HEAD DRIFT; renew applicable candidate evidence.**

## 3. Scope

- [ ] Changed-path list has been inspected.
- [ ] Every changed path is allowed by the task contract or explicitly reconciled before freeze.
- [ ] No forbidden/downstream gate has been implemented.
- [ ] No unrelated refactor or dependency change is hidden in the candidate.
- [ ] Shared-boundary changes (workflow, process authority, schema, shared API, RBAC, selectors, root config/dependencies) have the required explicit authority.
- [ ] Frontend Architecture Rule was applied if frontend scope requires it.

Record exceptions or scope adjudication:

```text
None | <evidence-backed disposition>
```

## 4. Acceptance / behavior

- [ ] Every task-specific acceptance criterion has direct evidence.
- [ ] Required negative cases are covered.
- [ ] Human approval/domain-command gates remain intact where applicable.
- [ ] Tenant/RBAC/security/audit/idempotency invariants remain intact where applicable.
- [ ] Currentness/concurrency/migration semantics have task-required evidence where applicable.
- [ ] Documentation says only what implementation/authority actually supports.

## 5. Reviews

Risk tier: `Low | Medium | High/Product/Security`

Required review count / type: `<...>`

- [ ] All required independent reviews exist.
- [ ] Required reviewers inspected the same exact frozen HEAD.
- [ ] Reviewer packets named base/HEAD, scope, authority and evidence.
- [ ] Findings were adjudicated as `VALID`, `INVALID`, `DUPLICATE`, `OUT_OF_SCOPE` or `ADVISORY`.
- [ ] All material `VALID` findings are fixed.
- [ ] Unresolved material findings = `0`.
- [ ] If a material fix changed HEAD, required reviews were renewed.

Reviewer evidence:

```text
Reviewer 1:
Reviewer 2:
Other:
```

Missing required review means **INCOMPLETE**, never PASS.

## 6. Verification / exact-head CI

Record:

```text
Candidate HEAD:
Exact-head CI run:
CI head SHA:
Status:
Conclusion:
```

- [ ] Required local/focused evidence is recorded with raw results.
- [ ] Local Saturation Gate before first push is evidenced, or a valid Early Push Exception records all four required fields and the mandatory remote evidence is now complete; use the [operating protocol](../plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md#local-saturation-gate).
- [ ] First Push Maturity and CI attempts (including failures/reruns) are recorded truthfully under [delivery metrics](../plan/VALORA_PM_OPERATING_PLAYBOOK_V1.md#19-delivery-metrics).
- [ ] Limitations and skips are explicit.
- [ ] No skip is represented as PASS.
- [ ] Exact-head CI belongs to the frozen candidate HEAD.
- [ ] CI status is `completed`.
- [ ] CI conclusion is `success`.

A green parent/earlier SHA does not certify this candidate.

After any CI trigger, sanity-check and record exact run/SHA, schedule a condition check and move to other authorized work. Resume on terminal result; IN PROGRESS waits without user noise. Do not repeatedly poll CI manually.

## 7. Gate Owner independent review

- [ ] Gate Owner inspected the exact diff/changed paths.
- [ ] Candidate behavior matches the accepted bounded authority.
- [ ] No evidence relies only on chat, memory or local claims when GitHub evidence is required.
- [ ] `READY FOR GATE REVIEW: YES` is supported by evidence.

Gate verdict:

```text
PASS | PASS WITH REQUIRED FIXES | FAIL | INCOMPLETE
```

Do not integrate on `PASS WITH REQUIRED FIXES`, `FAIL` or `INCOMPLETE` until a new applicable candidate gate is satisfied.

## 8. Pre-integration live check

Immediately before any Ready/merge transition:

- [ ] Refetch live PR metadata.
- [ ] Live PR HEAD still equals reviewed expected HEAD.
- [ ] Task explicitly authorizes Gate Owner integration.
- [ ] No new authority/baseline conflict appeared.

Expected head for merge:

```text
<40-character SHA>
```

## 9. Integration

Only after Gate Review PASS and explicit authorization:

- [ ] Mark Ready if required and authorized.
- [ ] Use squash merge unless current task/repository authority specifies otherwise.
- [ ] Use expected-head guard with the frozen reviewed HEAD.
- [ ] Capture resulting merge SHA.

Record:

```text
Merge method:
Expected HEAD:
Merge SHA:
```

A successful merge is **MERGED / UNCERTIFIED**.

## 10. Exact-main certification

Record:

```text
Captured merge SHA:
Live main SHA:
Exact-main CI run:
CI head SHA:
Status:
Conclusion:
```

- [ ] Live `main` is the captured merge SHA for this certification checkpoint.
- [ ] Exact-main CI head SHA equals captured merge SHA.
- [ ] CI status is `completed`.
- [ ] CI conclusion is `success`.

Only after all four conditions are true may the Gate Owner post `CERTIFIED / CLOSED`.

## 11. Post-merge failure handling

If exact-main CI is not SUCCESS:

- [ ] Keep/reopen task as uncertified when needed.
- [ ] Use the [CI failure taxonomy](../plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md#ci-failure-taxonomy); record failed run/SHA/job, log-backed classification and authorized next action. UNKNOWN remains blocked pending diagnosis.
- [ ] Do not waive a security/dependency/test failure without evidence.
- [ ] Rerun only when classification, current policy and evidence justify it; record the reason/attempt and preserve failures. No blind rerun.
- [ ] Any code change creates a new SHA and requires the applicable new evidence.

## 12. Certification and next action

- [ ] Post the certification record using `docs/templates/VALORA_CERTIFICATION_COMMENT_TEMPLATE.md`.
- [ ] Close the task only after exact-main SUCCESS.
- [ ] State explicitly what authority changed and what did not.
- [ ] Rebaseline after certification.
- [ ] Open/resume the next slice only if it was already authorized and prerequisites are met.
- [ ] Otherwise stop for Product Owner/authority decision.

Final status:

```text
CERTIFIED / CLOSED | MERGED / UNCERTIFIED | GATE BLOCKED
```
