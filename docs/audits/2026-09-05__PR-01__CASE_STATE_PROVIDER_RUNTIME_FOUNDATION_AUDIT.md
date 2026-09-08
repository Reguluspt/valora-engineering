# PR-01 — Case State Provider Runtime Foundation Audit

**Date:** 2026-09-05
**Status:** OWNER-DIRECTED LOCAL CLOSEOUT — TECHNICAL ACCEPTANCE PASS
**Branch:** `pr-01-case-state-projection-foundation`
**Baseline HEAD:** `aa5cd3a433e0f94d7b53c3331ef2145a2c672767`
**Candidate:** uncommitted local 25-file dirty set; staged state empty
**Authority:** ADR 0036, ADR 0037, ADR 0038 and `VALORA-PR01-IMPL-003`

## Accepted Local Slice

The local candidate implements the offline, computed-on-read foundation for the contiguous prefix:

`PRELIMINARY_REQUEST → PRELIMINARY_ANALYSIS → PRELIMINARY_READY → OFFICIAL_INTAKE`.

It includes four tenant-scoped read-only providers, a static 16-stage capability registry, the
internal aggregator, deterministic `case_version`, total `current_stage`, typed internal
`next_action`, typed 403/safe 404 behavior, separate non-blocking warnings and accepted
OFFICIAL_INTAKE blocker precedence.

The slice does not add an endpoint, public schema, projection persistence, cache, migration,
frontend/resume integration, row lock, write, flush, commit or audit event to the projection path.
It does not use `Project.status` or legacy workflow state as completion authority.

## PRELIMINARY_READY Lineage Acceptance

`PRELIMINARY_READY` rebuilds the production `_build_lineage_manifest` from current authoritative
records and compares its canonical JSON bytes with the stored manifest. The comparison covers:

- source workbook ID, generation, checksum and detected format;
- structure snapshot ID, version, rule version and analysis digest;
- mapping decision/usage IDs, both digests, template fingerprint and mapping contract version;
- analysis snapshot ID/version, canonical digest, line-manifest digest, finalizer and finalized time;
- generation contract; organization, project, customer and import-batch identity;
- mapped region, quantity column, output layout and line-locator count.

Canonical JSON comparison makes JSON types significant while ignoring object-key order. Missing,
additional, value-mutated and type-mutated fields therefore produce raw `INCOMPLETE`; preliminary
stages never become `STALE` or `BLOCKED`.

## Verification Evidence

All commands used the approved Python 3.12 engineering environment. PostgreSQL checks used the
disposable repair database `valora_pr01_impl002_repair_20260904161313_7a848026` through its derived
loopback port. The password was reconstructed only inside the test process, was not printed or
written, `DATABASE_URL` was cleared and only `TEST_DATABASE_URL` was set.

- provider and aggregator: `40 passed`, `0 failed`, `0 skipped`;
- PostgreSQL projection: `3 passed`, `0 failed`, `0 skipped`;
- existing v2.3 design contract: `5 passed`, `0 failed`, `0 skipped`;
- all `test_pr01*.py` files plus the design contract with `CI=true`: `226 passed`, `0 failed`,
  `0 skipped`, `0 deselected`, `0 xfail`;
- Ruff on touched Python files: PASS;
- Python compile: PASS;
- `git diff --check`: PASS;
- trailing whitespace and final newline: PASS;
- Alembic: single head `c159fab13c3a`;
- Git: expected branch/HEAD, staged empty and exactly 25 dirty files;
- protected baseline: all 18 hashes matched;
- credential helper `pr01_impl001_env.ps1`: absent.

The coordinator also exercised 126 missing/value/type mutations through the real aggregator. Every
negative case returned `INCOMPLETE`; a fully matching manifest and a manifest with reordered object
keys returned `COMPLETE`. A fresh read-only PostgreSQL transaction evaluated eight artifacts created
by the production generator; all eight retained `COMPLETE` for the three preliminary stages.

## Review Record

A fresh Qwen read-only review (`ses_f907db260ffe0ceOqOxQhZVLj7`) returned `PASS` with no blocking
finding after the type-sensitive correction.

The attempted formal Sol review did not inspect any repository file because
`codex-code-mode-host.exe` was unavailable. Its environment-only `FAIL` is not represented as a code
finding or acceptance review. The Product Owner then directed the coordinator to perform the gate in
its place. The coordinator found a false-`COMPLETE` path caused by Python equality treating
`True == 1`, reproduced it through the real aggregator, corrected it with canonical JSON equality,
and repeated the full verification above. The owner-approved replacement gate concluded `PASS`.

## Closeout Conclusion

`VALORA-PR01-IMPL-003` is technically accepted and closed locally as an offline provider/aggregator
foundation. This closeout does not authorize the projection endpoint or publication, does not close
the whole PR-01 read endpoint, and does not authorize PR-02.

## Explicitly Deferred

- `GET /api/v1/projects/{project_id}/case-state` and public response schemas;
- API/router wiring and permission exposure;
- frontend Case Overview or resume-context integration;
- projection persistence, cache or migration;
- downstream stage providers after `OFFICIAL_INTAKE`;
- owner acceptance for the next implementation slice;
- commit, push and pull-request creation.

## Subsequent Authorized Work

After this provider-only closeout, the Product Owner separately authorized
`VALORA-PR01-IMPL-004` to expose the accepted provider through
`GET /api/v1/projects/{project_id}/case-state`. That later endpoint task does not alter the
historical scope or conclusion recorded above.
