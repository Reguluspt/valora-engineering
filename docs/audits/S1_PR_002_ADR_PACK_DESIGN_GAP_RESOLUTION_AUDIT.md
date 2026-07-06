# S1-PR-002 ADR Pack + Design Gap Resolution Audit

**Task ID:** S1-PR-002  
**Task name:** Sprint 1 ADR Pack + Design Gap Resolution  
**Audit date:** 2026-07-06  
**Sprint:** Sprint 1 - Project + Master Data  
**Final result:** PASS  
**Recommendation:** Ready for S1-PR-003 implementation

## Files Checked

Repo guardrails and planning:

- `README.md`
- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `PR_RULES.md`
- `docs/04_MODULE_OWNERSHIP_MAP.md`
- `docs/adr/0001-record-architecture-decisions.md`
- `docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md`
- `docs/audits/S1_PR_001_PROJECT_MASTER_DATA_DESIGN_INTAKE.md`
- `docs/sprint-1/PROJECT_MASTER_DATA_IMPLEMENTATION_PLAN.md`
- `docs/sprint-1/PROJECT_MASTER_DATA_PR_BREAKDOWN.md`

Design reference package:

- `E:\Project Valora\valora-design-book-v1.2-final-full-package\README.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\manifest.json`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\README.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\01_SCOPE_AND_COMPLETION_GATE.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\15_CROSS_REFERENCE_MAP.md`

Alpha source ZIP inspected:

- `E:\Project Valora\valora-design-book-v1.2-final-full-package\01_SOURCE_ZIPS\valora-design-book-v1.2-alpha-project-master-data-completed.zip`

Relevant ZIP entries confirmed:

- `09_DATA_MODEL/01_PROJECT_MODEL.md`
- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `12_API/03_PROJECT_API.md`
- `12_API/05_MASTER_DATA_API.md`
- `13_SECURITY/02_AUTHENTICATION.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`
- `04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `04_DOMAIN/04B_MASTER_DATA_COMMANDS_EVENTS.md`
- `04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`

## ADRs Created

- `docs/adr/0002-persistence-orm-migration-strategy.md`
- `docs/adr/0003-auth-session-password-hashing-strategy.md`
- `docs/adr/0004-rbac-enforcement-and-permission-snapshot.md`
- `docs/adr/0005-audit-event-persistence-strategy.md`
- `docs/adr/0006-fuzzy-duplicate-matching-policy.md`
- `docs/adr/0007-project-file-upload-storage-policy.md`
- `docs/adr/0008-future-slice-endpoint-handling-policy.md`
- `docs/adr/0009-sprint-1-migration-and-seed-plan-clarification.md`

Each ADR includes:

- Status: Proposed.
- Context.
- Decision.
- Consequences.
- Design references.
- Sprint 1 scope impact.
- What is explicitly not implemented yet.
- Risks / follow-up.

## Design Gaps Resolved

Persistence/ORM/migration:

- Resolved by ADR 0002.
- Decision: SQLAlchemy 2.x ORM, Alembic, PostgreSQL, UUID primary keys, timezone-aware timestamps, `row_version`, PostgreSQL-backed test strategy.

Auth/session/password hashing:

- Resolved by ADR 0003.
- Decision: Sprint 1 baseline auth only, `organization_slug + email`, Argon2id preferred with bcrypt fallback, HTTP-only cookie-backed sessions preferred.

RBAC enforcement and permission snapshot:

- Resolved by ADR 0004.
- Decision: server-side permission dependency, deny-by-default checks, active UserRole-derived permissions, snapshot as derived/cache only if needed.

Audit/event persistence:

- Resolved by ADR 0005.
- Decision: minimal append-only audit/event records for Sprint 1 Project and Master Data mutation commands.

Fuzzy duplicate matching:

- Resolved by ADR 0006.
- Decision: deterministic warning-only fuzzy matching; exact tax code duplicate remains blocking.

Project file upload storage:

- Resolved by ADR 0007.
- Decision: ProjectFile metadata plus local MinIO/S3-compatible storage boundary; no OCR/import/rendering processing.

Future-slice endpoint handling:

- Resolved by ADR 0008.
- Decision: explicit `501 Not Implemented` or guarded `422 Unprocessable Entity` for future-sprint capabilities; no silent no-op and no future behavior.

Migration/seed plan:

- Resolved by ADR 0009.
- Decision: derive Sprint 1 migration/seed plan from alpha data model and security sources; seed standard roles and permissions only; no real business data.

## Missing Design Files Status

S1-PR-001 identified these missing files:

- `02_DESIGN_PRINCIPLES.md`
- `16_MIGRATION_AND_SEED_PLAN.md`
- `17_CODEX_PROMPTS_V1_2_ALPHA.md`

Resolution:

- `16_MIGRATION_AND_SEED_PLAN.md` gap is explicitly resolved by ADR 0009.
- `02_DESIGN_PRINCIPLES.md` remains a design-package completeness gap but is not blocking Sprint 1 coding because final guardrails and alpha scope files provide the governing implementation constraints.
- `17_CODEX_PROMPTS_V1_2_ALPHA.md` remains a design-package completeness gap but is not blocking implementation because repo task prompts and ADRs now define the Sprint 1 implementation constraints.

## Scope Compliance

Result: PASS.

This task created ADR and audit documentation only. It did not:

- Modify backend source.
- Modify frontend source.
- Modify worker source.
- Modify pyproject/package files.
- Add dependencies.
- Create database models.
- Create migrations.
- Implement APIs.
- Implement auth or RBAC logic.
- Modify the design reference package.
- Invent domain behavior beyond the Design Book.

## Checks Run

- `git status --short` before edits.
- Required repo files read.
- Required final handoff and alpha extracted files read.
- Alpha source ZIP entry listing inspected via .NET `System.IO.Compression.ZipFile`.
- Backend/frontend/worker paths confirmed present but not modified.

Post-write checks required:

- Confirm only ADR/audit docs changed.
- Confirm no backend/frontend/worker diff.
- Confirm design reference package remains read-only.
- Confirm ADR files 0002 through 0009 exist.

## Recommendation

Ready for S1-PR-003 implementation.

Implementation may start with the next assigned Sprint 1 task, provided it stays within the ADR decisions and its own allowed file scope. The next coding PR must still add implementation and tests explicitly; this ADR pack adds no implementation code.
