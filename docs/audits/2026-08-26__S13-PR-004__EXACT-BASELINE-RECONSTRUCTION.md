# S13-PR-004 Exact-Baseline Reconstruction Evidence

**Task:** S13-PR-004 — Column Mapping Memory Persistence and Application Services

**Required baseline:** `2af753520ab6b7885555adc5b7945a28d32ee311`

**Reconstructed implementation SHA:** `9e24a49` (local only)

## Method

The accepted S13-PR-004 design/evidence packet and implementation changes were replayed onto a new local branch created directly from the required baseline. No S13-PR-005, S14, S15, S16, frontend remediation, or unrelated local commit was included.

## Design sources

- Design Book v1.4 Adaptive Intake / Column Mapping Memory.
- ADR 0030 and ADR 0033-compatible decision provenance.
- `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, and the S13-S16 remediation plan.
- `2026-07-19__S13-PR-004__EVIDENCE-GATE-DESIGN.md`.

## Verification

```text
Starting SHA                         2af753520ab6b7885555adc5b7945a28d32ee311
git diff --check baseline..HEAD     PASS
python -m ruff check app tests      PASS
python -m alembic heads             PASS; b4c5d6e7f8a9 (single head)
focused pytest                      47 passed, 4 skipped, 13 warnings
```

The four skipped tests are the explicit PostgreSQL concurrency/migration proof in `test_s13_pr_004_column_mapping_postgresql.py`. The local Docker daemon and local PostgreSQL service were unavailable, so these skips are **not** reported as PASS.

## Scope and limitations

- Scope respected: **Yes**; exact S13-PR-004 files only.
- ADR needed: **No**; the implementation follows the accepted ADR 0030 contract.
- No push, PR, merge, deployment, credential, or production-data operation.
- This reconstruction is a dependency baseline for local S14 remediation. It is not release acceptance until the PostgreSQL gate runs on the exact candidate SHA.
