# RBAC-001 standard operator Workbench edit — implementation evidence

Task: `VALORA-TASK-OS-G1-RBAC-001-STANDARD-OPERATOR-WORKBENCH-EDIT`.
This file records verification of the scoped Product Owner decision; it is not a new permission or endpoint contract.

## Baseline and pause boundary

- Live `origin/main` at start: `21eb2e264a0f819cd3caa053fa0769128c5d06a0`.
- Live `CODEX.md` read in full; blob: `8c1f8ae48d13a54b3f18386e46dfb22571b811db`.
- PR #66 merged as that SHA; exact-main CI #523, run `36823627276`, completed successfully on the same SHA.
- The separate G1.1K worktree remains paused and untouched at `F:\Project Valora\valora-g1-1k-precase-product-closure-e2e`, branch `codex/os-g1-1k-precase-product-closure-e2e`. At handoff it contained uncommitted `frontend/src/api/client.ts`, its focused test, `docs/implementation/g11k-screenshots/` and `tests/`. None are included here.

## Authority and root cause

Read: live `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, identity baseline migration, G1.1E grant migration and PostgreSQL test, Role/UserRole/effective-permission code, Excel Import/Staging and Workbench API contracts, asset-import/source-artifact/structure/mapping routes, and ADR 0029 Apply contract. Alembic had one predecessor head, `d1e2f3a4b5c6`.

The accepted batch-create endpoint and Excel Import contract require existing `workbench:edit`. Its 403 for the standard G1.1K owner actor was the correct RBAC result: the original standard role seed predates the Workbench/Excel mutation family and omitted that permission. G1.1E subsequently granted owner/appraiser three dedicated Analysis, Result and Official Intake permissions, without granting `workbench:edit`. The Product Owner now explicitly accepts adding that existing, coarse permission to standard owner/appraiser. Endpoint permission checks remain unchanged.

## Migration and role matrix

Migration `e2f3a4b5c6d7` follows `d1e2f3a4b5c6`. It locks each target Role row, validates a distinct string permission list, preserves existing values, and appends `workbench:edit` only when missing. Each upgrade writes `G1KStandardOperatorWorkbenchEditGrantAdded` with the Role entity ID, revision command name, role code, and exactly added permissions (`["workbench:edit"]` or `[]`). Downgrade reads its own audit provenance and removes only a permission added by this migration. A missing/malformed standard role fails and rolls back the transaction.

| Seeded standard role | At predecessor | After upgrade | Changed by RBAC-001 |
| --- | --- | --- | --- |
| owner | absent | present once | yes |
| appraiser | absent | present once | yes |
| admin | absent | absent | no |
| reviewer | absent | absent | no |
| knowledge_curator | absent | absent | no |
| viewer | absent | absent | no |

No custom role or individual User record is changed.

## Existing `workbench:edit` route inventory

The grant has the existing coarse Workbench scope. Static inventory from `backend/app/api/projects.py` and `backend/app/api/workbench.py` found **21** routes that require `workbench:edit`; none was edited.

`/api/v1/projects` prefix (13):

| Method | Suffix | Existing operation |
| --- | --- | --- |
| POST | `/{project_id}/asset-imports` | Create import batch |
| POST | `/{project_id}/asset-imports/{batch_id}/upload` | Legacy Excel upload |
| POST | `/{project_id}/asset-imports/{batch_id}/source-artifacts` | Source-artifact upload |
| POST | `/{project_id}/asset-imports/{batch_id}/source-artifacts/{artifact_id}/structure-snapshots` | Structure analysis |
| POST | `/{project_id}/asset-imports/{batch_id}/column-mapping/proposals` | Mapping proposal |
| POST | `/{project_id}/asset-imports/{batch_id}/column-mapping/confirmations` | Mapping confirmation |
| POST | `/{project_id}/asset-imports/{batch_id}/column-mapping/legacy-selections` | Explicit legacy selection |
| POST | `/{project_id}/asset-imports/{batch_id}/column-mapping/rejections` | Mapping rejection |
| POST | `/{project_id}/asset-imports/{batch_id}/column-mapping/materializations` | Staging materialization |
| POST | `/{project_id}/asset-imports/{batch_id}/validate` | Staging validation |
| POST | `/{project_id}/asset-imports/{batch_id}/apply` | ADR 0029 Apply |
| PATCH | `/{project_id}/asset-lines/{line_id}/draft` | Draft save |
| POST | `/{project_id}/asset-lines/{line_id}/draft/commit` | Human draft commit |

`/api/v1/workbench` prefix (8): POST `/sessions/{session_id}/heartbeat`, `/close`, `/layout`, `/grid-view`, `/selection`, `/inline-edit`, `/checkpoint`, and `/panel-state`. These still require an existing authorized session and their own downstream checks. The asset-line draft command also checks `workbench:edit` within its application boundary. The grant passes the existing RBAC gate only; tenant, Project, workflow, CAS, confirmation, Apply and human commit guards remain required.

## PostgreSQL proof

`backend/tests/test_g1_rbac_001_postgresql.py` creates isolated PostgreSQL databases and runs real Alembic upgrades from the predecessor. It verifies baseline absence, target-only grant, exact audit payloads, effective permissions from standard Role/UserRole bindings, safe downgrade, and preservation of a pre-existing owner grant. It also verifies transaction rollback when appraiser is missing or malformed.

The endpoint proof uses the repository's test-auth actor header convention while reading real migrated PostgreSQL roles and executing the real FastAPI route. Standard owner and appraiser each create a batch (201); viewer remains 403, cross-tenant appraiser receives safe 404, and an unauthenticated request receives 401. No permission is mocked in the test. The separate G1.1K browser journey remains paused.

## Verification and delivery

- Focused PostgreSQL migration/effective-permission/endpoint matrix: **5 passed, 0 skipped, 14 existing deprecation warnings** (`test_g1_rbac_001_postgresql.py` plus `test_g11e_rbac_postgresql.py`).
- Migration smoke: local PostgreSQL upgraded to single head `e2f3a4b5c6d7`; isolated tests exercised upgrade/downgrade round trips.
- Full backend suite, run once against local PostgreSQL/S3 test services: **1775 passed, 1 skipped, 145 warnings** in 555.49s. The single skip is the pre-existing POSIX-only `LocalFilesystemDocumentBlobStore` hard-link test on Windows; it is not counted as a pass. Warnings are existing SQLAlchemy/API deprecations.
- Ruff `ruff check .`: passed. Security baseline `python tests/check_security.py`: passed with no blocker regressions. Dependency audit after upgrading local pip to 26.2.1: no known vulnerabilities; the local editable `valora-backend` package is not on PyPI and was skipped by `pip-audit`. `git diff --check`: passed.
- `G1_RBAC_001_CHANGED_FILES.txt` lists all changed repository paths; `G1_RBAC_001_SHA256SUMS.txt` hashes the other six files from staged Git blob bytes, excluding itself to avoid a self-referential hash. This makes verification independent of checkout line endings.
- Independent reviews, Draft PR and exact-head PR CI: pending frozen-snapshot gate.

G1.1K may resume only after this RBAC PR merges and its resulting exact-main CI succeeds. OS-G1 remains incomplete; OS-G2 is not authorized.
