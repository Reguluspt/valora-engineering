# S13-PR-002 Implementation Report — Legacy Workbook Adapter and Immutable Source Artifact

**Task ID:** S13-PR-002  
**Task name:** Legacy Workbook Adapter and Immutable Source Artifact  
**Date:** 2026-07-16  
**Implementer:** Grok (owner-authorized runtime)  
**Status:** **DRAFT — NOT READY / NOT MERGED** (pending exact-head CI + independent audit)

---

## 1. Owner assignment provenance

Owner directive (2026-07-16): **“Tiến hành S13-PR-002”** via implementation prompt  
`2026-07-16__VALORA_S13-PR-002__GROK_IMPLEMENTATION_PROMPT.md`.

Authorization scope:

- branch from accepted main;
- implement runtime adapters/storage/migration/API/tests/CI wiring in task scope;
- push branch and open **Draft** PR only;
- **no** Ready, squash, merge, or force-push.

---

## 2. Baseline

| Item | Value |
| --- | --- |
| Repository | https://github.com/Reguluspt/valora-engineering |
| Accepted `origin/main` at assignment | `949903f3912aa65f8b990852756aeef7981bca08` |
| Baseline provenance | Gate 0c closeout PR #14; main CI run `29508966217` PASS |
| Feature branch | `s13-pr-002-legacy-workbook-source-artifact` |
| Branch point | exact main tip above (no S12 residual branch) |

Pre-change verification:

- clean worktree (owner primary dirty tree left untouched);
- `git rev-parse origin/main` == baseline SHA.

---

## 3. Design / ADR sources

1. `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `PR_RULES.md`
2. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
3. `docs/VALORA_PROJECT_HANDOFF.md`
4. Design Book v1.4 §5.1–5.3, §16, §19–20
5. ADR 0030 (adaptive workbook intake / mapping memory boundary)
6. ADR 0034 (reliable commands; DB/object-storage reconciliation)
7. Remediation plan §S13-PR-002
8. Excel staging contract — frozen `s12-pr-004-v1` boundary

---

## 4. Dependency / security spike result

See: `docs/audits/2026-07-16__S13-PR-002__XLS_DEPENDENCY_SECURITY_SPIKE.md`

| Decision | Package | Pin |
| --- | --- | --- |
| `.xls` reader | xlrd | `>=2.0.1,<3` |
| Object storage client | boto3 | `>=1.34.0` |
| `.xlsx` | openpyxl (existing) | unchanged |

Rejected: Office automation; calamine for this PR; soft-accept of unsafe books.

---

## 5. Scope implemented

### 5.1 WorkbookAdapter (value-only, fail-closed)

- Domain contract: `domain/workbook_adapter.py` (format, cells, sheet summary, inspection result, `AdapterError`).
- `.xlsx` adapter: ZIP safety reuse + `openpyxl` `read_only` / `data_only` / no links/VBA path.
- `.xls` adapter: OLE signature + xlrd value-only open + resource limits.
- Format detection: extension **and** content signature.

### 5.2 ImportSourceArtifact + migration

- Table `import_source_artifacts` (tenant/project/batch scoped).
- Unique `(import_batch_id, generation)`, unique `storage_object_key`.
- Check constraints: generation > 0, size ≥ 0, checksum length 64.
- Batch pointer `project_asset_import_batches.current_source_artifact_id` (FK RESTRICT).
- Alembic: `f2a3b4c5d6e7` revises `e1f2a3b4c5d6` (single head).

### 5.3 Object storage port

- `ObjectStoragePort`: put_stream / head / open_stream / delete / ensure_bucket.
- `FakeObjectStorage` for unit tests (deterministic; can force put failure).
- `S3ObjectStorage` via boto3 for MinIO/S3-compatible endpoints.
- Server-owned keys: `org/{org}/project/{project}/import-batch/{batch}/source/{artifact_id}`.
- Strong verify: re-hash object bytes after put; never treat multipart ETag as SHA-256.

### 5.4 Recoverable protocol + reconciler

State machine (`VALID_TRANSITIONS`):

| From | To |
| --- | --- |
| pending | available, failed, orphaned |
| available | orphaned |
| failed | orphaned |
| orphaned | (terminal) |

Upload protocol:

1. Bounded spool + SHA-256.
2. Adapter safety inspection (must pass before available).
3. Reserve `pending` + audit `ImportSourceArtifactReserved` + commit.
4. Object put + re-hash verify.
5. Lock project/batch/artifact → `available` + set current + audit `ImportSourceArtifactAvailable`.
6. Object failure → `failed` + audit; prior current unchanged.
7. Stale generation after newer current → `orphaned` (does not win current).

Bounded reconciler (`reconcile_source_artifacts`): max_items, retention cutoff, never deletes current/available history, deletes orphan objects past retention only under lock.

### 5.5 API (Adaptive Intake v2 — separate from S12)

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/api/v1/projects/{project_id}/asset-imports/{batch_id}/source-artifacts` | `workbench:edit` |
| GET | same collection | `project:read` |
| GET | `.../source-artifacts/{artifact_id}` | `project:read` |

Response: metadata only — **no** `storage_object_key`, credentials, or signed URLs.  
Does **not** create/modify staging rows or `ProjectAssetLine`.

S12 `POST .../upload` remains `.xlsx` + fixed alias + staging v1; still rejects `.xls`.

### 5.6 Audit events

- `ImportSourceArtifactReserved`
- `ImportSourceArtifactAvailable`
- `ImportSourceArtifactFailed`
- `ImportSourceArtifactOrphaned`
- `ImportSourceArtifactObjectDeleted`

Payloads: safe IDs, generation, format, checksum/size, failure codes — no cell content/paths/secrets.

### 5.7 CI

- Pin MinIO image `minio/minio:RELEASE.2024-12-18T13-15-44Z`.
- Bootstrap bucket; set `CI=true` + `S3_*` env for backend tests so MinIO integration cannot silent-skip in CI.

### 5.8 Live-state docs

Updated assignment truth only (in progress / not merged): `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, Authority Index, handoff, remediation plan.

---

## 6. Explicit non-goals (confirmed not implemented)

- Header/table discovery changes on S12 path; semantic column mapping; ColumnMappingProfile.
- Mapping confirmation UI; row classification; RawAssetObservation; asset identity memory.
- Excel–Word aggregate; AI runtime; staging materialization from Adaptive v2.
- Changes to S12 Apply / `s12-pr-004-v1`; `ProjectAssetLine` mutation.
- Office automation; real customer fixtures; frontend UX.

---

## 7. Files changed (implementation set)

**New**

- `backend/app/modules/excel_import/domain/workbook_adapter.py`
- `backend/app/modules/excel_import/domain/source_artifact.py`
- `backend/app/modules/excel_import/application/adapters/__init__.py`
- `backend/app/modules/excel_import/application/adapters/xlsx_adapter.py`
- `backend/app/modules/excel_import/application/adapters/xls_adapter.py`
- `backend/app/modules/excel_import/application/source_artifact_service.py`
- `backend/app/modules/excel_import/infrastructure/object_storage.py`
- `backend/app/modules/excel_import/models.py`
- `backend/app/modules/excel_import/schemas.py`
- `backend/alembic/versions/f2a3b4c5d6e7_create_import_source_artifacts.py`
- `backend/tests/test_s13_pr_002_source_artifacts.py`
- `docs/audits/2026-07-16__S13-PR-002__XLS_DEPENDENCY_SECURITY_SPIKE.md`
- `docs/audits/2026-07-16__S13-PR-002__LEGACY-WORKBOOK-AND-SOURCE-ARTIFACT__REPORT.md`

**Modified**

- `backend/app/api/projects.py` — source-artifact routes
- `backend/app/modules/project_master_data/models.py` — `current_source_artifact_id` column mapping
- `backend/alembic/env.py` — register excel_import models
- `backend/pyproject.toml` — xlrd, boto3
- `.github/workflows/ci.yml` — MinIO + S3 env for tests
- Live docs listed above

**Not committed:** local spool junk (`backend/t.xlsx`), egg-info, `__pycache__`.

---

## 8. Migration

| Field | Value |
| --- | --- |
| revision | `f2a3b4c5d6e7` |
| down_revision | `e1f2a3b4c5d6` |
| Single head | required (CI + local `alembic heads`) |
| Downgrade | drops FK + column + table; does not rewrite historical source bytes already in object storage |

---

## 9. Partial-failure proof matrix

| Scenario | Expected | Test / mechanism |
| --- | --- | --- |
| Happy path upload | `available`, current set, object present, no staging delta | `test_source_artifact_upload_available_and_no_staging` |
| Object put fails after reserve | artifact `failed`, prior current unchanged | `test_failure_keeps_prior_current` + `FakeObjectStorage.fail_put` |
| Checksum mismatch after put | delete attempt + fail path | service re-hash gate |
| Stale generation after newer current | orphaned; does not become current | service finalize branch |
| Cross-tenant | 404 fail-closed | `test_cross_tenant_denied` |
| Response key leakage | no `storage_object_key` | list/get/upload assertions |
| Reconciler vs current | never deletes current object | `test_reconciler_skips_current` |
| S12 still rejects `.xls` | 400 | `test_s12_upload_rejects_xls` |
| MinIO integration | put/head/get/delete | `test_s3_integration_when_configured` (required when `CI=true`) |

---

## 10. Tests and gates

### Local (pre-push)

Commands (backend):

```text
python -m pip install -e ".[dev]"
ruff check .
alembic heads
pytest tests/test_s13_pr_002_source_artifacts.py tests/test_asset_imports.py -rs
# full suite + alembic upgrade + check_security + pip-audit when PG/MinIO available
```

Raw counts are recorded in the final owner report after the pre-commit run on this branch.

### CI (authoritative for Draft green)

PostgreSQL 16 service + MinIO container + `pytest -rs` with `CI=true` and `S3_*` set.  
Silent skip of MinIO proof in CI is forbidden by test assertion.

---

## 11. Security / tenant proof

- All source-artifact queries filter `organization_id + project_id + batch_id`.
- Cross-tenant user cannot upload/list/get foreign batch.
- Object keys server-generated from UUIDs only.
- API schemas omit storage key.
- Adapter errors Vietnamese + stable codes; no internal paths in `detail`.

---

## 12. Known limitations

1. Local environment may lack PostgreSQL/MinIO; full PASS is CI-owned.
2. `.xls` merged-region metadata not exposed (xlrd 2.x without formatting_info).
3. VBA *presence* deny-list via full OLE stream inventory is residual (non-execution is enforced).
4. Reconciler is an application service, not a Sprint 15 scheduler job.
5. No signed download URL in this task (by design).

---

## 13. ADR needed?

**No new ADR required** for this PR. Runtime implements ADR 0030 intake boundary + ADR 0034 storage reconciliation patterns already accepted. Spike recorded in audit doc.

---

## 14. Rollback / downgrade limits

- Alembic downgrade removes pointer + table.
- Objects already written to bucket are not automatically bulk-deleted by downgrade.
- S12 path remains independent; rolling back Adaptive routes does not unwind Apply history.

---

## 15. Reviewer attention points

1. Confirm S12 upload/Apply paths untouched in behavior (`s12-pr-004-v1`).
2. Confirm no `ProjectAssetLine` writes from source-artifact service.
3. Review state machine + reconciler “never delete current/available history”.
4. Review CI MinIO pin and `CI=true` fail-closed integration test.
5. Review live docs claim **in progress / not merged** only.

---

## 16. Ready criteria (not claimed)

READY requires:

- exact-head GitHub CI PASS (backend full suite + MinIO integration + alembic single head + security scans);
- independent audit PASS;
- owner Ready command.

Until then: **DRAFT — NOT READY / NOT MERGED**.
