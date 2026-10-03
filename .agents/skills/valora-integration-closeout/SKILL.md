---
name: valora-integration-closeout
description: Close an authorized Valora integration gate through guarded squash merge and exact-main CI certification, then advance an already authorized bounded slice.
---

# Integration closeout

Verify live PR/Issue, task authorization, frozen candidate reviews and exact-head CI. Candidate PASS → authorized Ready → expected-head guarded squash merge → capture merge SHA → exact-main CI SUCCESS → only then certify/close task.

Before Ready/merge, verify live PR HEAD equals the reviewed expected SHA. Use an expected-head guard for squash merge, stop if it changed, and renew evidence on a changed HEAD. Draft-only tasks stay Draft; this skill grants no integration permission.

If GitHub auto-closes an Issue before exact-main certification, reopen when needed to keep it visibly uncertified. A green parent, branch CI or PR merge result is insufficient. Match postmerge CI's head SHA to the captured merge SHA and require completed SUCCESS.

After exact-main SUCCESS, if no PO/authority blocker exists, automatically open/resume the next bounded already-authorized slice without waiting for another Product Owner “continue” message. Verify its live baseline, scope and prerequisite first. Do not invent the next product gate; missing authorization is a blocker, as is a contract that explicitly stops at Draft.

Persist only certified durable lessons under the [profile](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md); never persist current merge SHA, CI status or active Issue state as durable truth.
