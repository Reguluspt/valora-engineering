# VALORA Certification Comment Template

**Lifecycle/status:** CURRENT SUPPORTING CERTIFICATION TEMPLATE — 2026-10-05.
**Authority role:** Closeout evidence format only. It does not grant product/runtime authority or permission to merge.

Use this template only after the applicable Gate Review and integration authority have been satisfied.

```markdown
## GATE OWNER CERTIFICATION

### Task
`<TASK ID>`

Issue: #<issue>
PR: #<pr>
Risk: `<Low | Medium | High/Product/Security>`

### Authority / scope

Certified bounded scope:
- <scope>

Explicitly NOT certified / NOT authorized:
- <downstream scope>
- <adjacent product/runtime authority>

Runtime/product authority changed:
`<NONE | exact accepted change>`

### Candidate evidence

Base SHA:
`<40-char SHA>`

Frozen candidate HEAD:
`<40-char SHA>`

Required reviews:
- <reviewer/evidence or N/A with contract reason>

Unresolved material findings:
`0`

Exact-head CI:
- run: `<number / URL>`
- head SHA: `<candidate SHA>`
- status: `completed`
- conclusion: `success`

Task-specific acceptance evidence:
- <tests/checks>
- <limitations/skips, if any>

### Integration

Gate Review:
`PASS`

Merge method:
`SQUASH`

Expected-head guard:
`<frozen candidate SHA>`

Captured merge SHA:
`<40-char SHA>`

### Exact-main certification

Live `main` SHA:
`<40-char SHA>`

Exact-main CI:
- run: `<number / URL>`
- head SHA: `<captured merge SHA>`
- status: `completed`
- conclusion: `success`

Certification invariant:
`live main == captured merge SHA == exact-main CI head SHA`

### Disposition

`CERTIFIED / CLOSED`

The task is certified only for the bounded scope above. This certification does not infer authority for any item listed under Explicitly NOT certified / NOT authorized.

Next authorized action:
`<one already-authorized bounded action | STOP — PRODUCT/AUTHORITY DECISION REQUIRED>`
```

## Rules

1. Do not post `CERTIFIED / CLOSED` before exact-main CI is completed SUCCESS on the captured merge SHA.
2. A merged PR with pending/failed exact-main CI is `MERGED / UNCERTIFIED`.
3. Candidate CI cannot replace post-merge exact-main certification.
4. A same-SHA rerun may be cited when current policy/evidence supports a transient failure classification; record the successful attempt accurately.
5. If code changes after a failed merge-state remediation, use the new SHA's applicable evidence; never reuse stale exact-head certification.
6. State both certified scope and explicitly unauthorized downstream scope so closure cannot be misread as a product-gate expansion.
7. After certification, rebaseline live repository before opening or resuming another slice.
