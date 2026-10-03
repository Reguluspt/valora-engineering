---
name: valora-high-risk-gate-review
description: Execute a Valora High, Product or Security gate review on one frozen candidate with independent reviews and exact SHA evidence.
---

# High risk review

Under live CODEX and the assigned contract:

HIGH risk → freeze ONE HEAD → two independent read-only reviewers → SAME exact HEAD → exact-head CI SUCCESS → Gate Owner independent review → expected-head guarded Ready/merge → squash merge → exact-main postmerge certification.

Give reviewers the exact SHA, changed-file/hash manifest, scoped authority and necessary evidence. Query live provider model lists. Missing required review is INCOMPLETE, never PASS. Adjudicate findings as VALID, INVALID, DUPLICATE, OUT_OF_SCOPE or ADVISORY with evidence; fix valid findings.

Any changed reviewed HEAD invalidates the prior candidate reviews and CI. Freeze a new candidate and obtain required evidence again. A successful parent commit cannot certify it.

Ready/merge require the current task's explicit integration authorization. Recheck live PR HEAD against the reviewed expected HEAD immediately before any state transition; stop on mismatch. Use GitHub's expected-head guard for the authorized squash merge. Capture merge SHA and require CI SUCCESS on that exact main SHA before certification. Never infer permission to merge from this reusable skill.

Memory is non-authoritative; apply the [profile](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md).
