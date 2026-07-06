# Antigravity Valora Design + Engineering Rules Onboarding Audit

**Task ID:** AG-ONBOARD-001  
**Task Name:** Antigravity Valora Design + Engineering Rules Onboarding  
**Audit Date:** 2026-07-06  
**Current Phase:** Engineering Phase / Sprint 1 — Project + Master Data  
**Next Intended PR:** S1-PR-003 — Persistence / ORM / Migration Foundation  
**Final Result:** PASS  
**Recommendation:** Ready for S1-PR-003  

---

## 1. Files Read

### Repository Rules and Foundation Files
- [README.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/README.md)
- [CODEX.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/CODEX.md)
- [ENGINEERING_GUARDRAILS.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/ENGINEERING_GUARDRAILS.md)
- [PR_RULES.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/PR_RULES.md)
- [.gitignore](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/.gitignore)
- [docs/04_MODULE_OWNERSHIP_MAP.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/04_MODULE_OWNERSHIP_MAP.md)
- [docs/adr/0001-record-architecture-decisions.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0001-record-architecture-decisions.md)

### Sprint 0 Closure & Sprint 1 Planning Audits
- [docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md)
- [docs/audits/S1_PR_001_PROJECT_MASTER_DATA_DESIGN_INTAKE.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S1_PR_001_PROJECT_MASTER_DATA_DESIGN_INTAKE.md)
- [docs/sprint-1/PROJECT_MASTER_DATA_IMPLEMENTATION_PLAN.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/sprint-1/PROJECT_MASTER_DATA_IMPLEMENTATION_PLAN.md)
- [docs/sprint-1/PROJECT_MASTER_DATA_PR_BREAKDOWN.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/sprint-1/PROJECT_MASTER_DATA_PR_BREAKDOWN.md)
- [docs/audits/S1_PR_002_ADR_PACK_DESIGN_GAP_RESOLUTION_AUDIT.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S1_PR_002_ADR_PACK_DESIGN_GAP_RESOLUTION_AUDIT.md)

### Sprint 1 Architecture Decision Records (ADRs)
- [docs/adr/0002-persistence-orm-migration-strategy.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0002-persistence-orm-migration-strategy.md)
- [docs/adr/0003-auth-session-password-hashing-strategy.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0003-auth-session-password-hashing-strategy.md)
- [docs/adr/0004-rbac-enforcement-and-permission-snapshot.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0004-rbac-enforcement-and-permission-snapshot.md)
- [docs/adr/0005-audit-event-persistence-strategy.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0005-audit-event-persistence-strategy.md)
- [docs/adr/0006-fuzzy-duplicate-matching-policy.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0006-fuzzy-duplicate-matching-policy.md)
- [docs/adr/0007-project-file-upload-storage-policy.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0007-project-file-upload-storage-policy.md)
- [docs/adr/0008-future-slice-endpoint-handling-policy.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0008-future-slice-endpoint-handling-policy.md)
- [docs/adr/0009-sprint-1-migration-and-seed-plan-clarification.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0009-sprint-1-migration-and-seed-plan-clarification.md)

### Final Design Handoff Package
- `valora-design-book-v1.2-final-full-package/README.md`
- `valora-design-book-v1.2-final-full-package/manifest.json`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/01_FINAL_RELEASE_NOTE.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/02_ENGINEERING_HANDOFF_GATE.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/03_SPRINT_SEQUENCE_FINAL.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/05_FINAL_RELEASE_CHECKLIST.md`

### Sprint 1 Alpha Completed Design ZIP Entries
- `valora-design-book-v1.2-alpha-project-master-data-completed/README.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/01_SCOPE_AND_COMPLETION_GATE.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/09_DATA_MODEL/01_PROJECT_MODEL.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/12_API/03_PROJECT_API.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/12_API/05_MASTER_DATA_API.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/13_SECURITY/02_AUTHENTICATION.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/04_DOMAIN/04B_MASTER_DATA_COMMANDS_EVENTS.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`
- `valora-design-book-v1.2-alpha-project-master-data-completed/15_CROSS_REFERENCE_MAP.md`

---

## 2. Design Source Summary

- **Primary Authority:** `Valora Design Book v1.2-final` is the sole source of truth for all domain behaviors.
- **Sprint 1 Source Slice:** `v1.2-alpha-completed` provides the data models, API endpoints, commands, events, state machine, and acceptance tests for the Project and Master Data boundaries.
- **Core Entities Defined:**
  - *Organization/Identity:* `OrganizationProfile`, `User`, `Role`, `UserRole`, `UserPermissionSnapshot`
  - *Master Data:* `Customer`, `CustomerAlias`, `Supplier`, `SupplierAlias`, `Country`, `Province`, `Brand`, `Manufacturer`, `Unit`, `Currency`, `SignerProfile`
  - *Project Context:* `Project`, `ProjectAssetLine`, `ProjectFile`

---

## 3. Current Sprint and Next PR

- **Current Phase:** Engineering Phase / Sprint 1 — Project + Master Data
- **Current Git Branch:** `s1-pr-003-persistence-orm-migration-foundation`
- **Next Intended PR:** `S1-PR-003 — Persistence / ORM / Migration Foundation` (which will establish the persistence baseline, SQLAlchemy models, Alembic environment, migrations, and PostgreSQL test boundary).

---

## 4. Sprint 1 Allowed Scope

Sprint 1 is authorized to implement the following features:
- **Persistence & Migrations:** Initialize SQLAlchemy 2.x ORM, Alembic migrations, database models, and seeding for Sprint 1 tables.
- **Identity Foundation:** Organization slug + email login identity structure.
- **Standard RBAC:** Seed roles (`owner`, `admin`, `appraiser`, `reviewer`, `knowledge_curator`, `viewer`) and authorization permissions. Enforce deny-by-default access check server-side.
- **Master Data APIs & Commands:** Create, update, list, deactivate, and merge operations for Customer/Supplier, reference data (Country, Province, Brand, Manufacturer, Unit, Currency), and SignerProfiles.
- **Project APIs & Commands:** Create, read, update, file upload (metadata only), review start/complete, reject, approve, and archive command flows.
- **Fuzzy Duplicate Warnings:** Warning-only, deterministic matching for Customers on legal/display names (trim, lowercase, punctuation removal).
- **File Upload Boundary:** File metadata storage in DB and objects in local MinIO/S3-compatible storage.
- **Audit Trails:** Append-only transaction audit records for all mutation commands.
- **Future Endpoints Handling:** Returning explicit `501 Not Implemented` or guarded `422` error codes for future capabilities (AI parsing, document generation, appraising).

---

## 5. Sprint 1 Forbidden Scope

Sprint 1 must **not** implement the following future-sprint capabilities:
- **Taxonomy Engine (Sprint 2):** Taxonomy tree, node assignment, or attribute templates.
- **Asset Identity (Sprint 2):** Canonical asset matching, variant suggestions, or alias maps.
- **Knowledge Base & Evidence (Sprint 3):** Evidence library, technical specification extraction (KTKT), quote lines/appraised price decisions, or lineage path formulas.
- **Workflow & Workbench UI (Sprint 4):** Project workflow editor, workbench session state, autosave, undo/redo, or change requests/reversals.
- **Document Engine & Intelligence (Sprint 5):** Render jobs, template generation, computing document placeholders, or OCR parsing.
- **AI Governance & Hardening (Sprint 6):** AI task registry, prompt safety filters, API key hashing admin UI, or automated log auditing.
- **Infrastructure:** Production cloud services, Kubernetes configurations, Terraform scripts, or paid external APIs.

---

## 6. ADR Decisions Summary

- **ADR 0002 (Persistence):** SQLAlchemy 2.x ORM, Alembic, PostgreSQL authoritative target, UUID primary keys, timezone-aware timestamps, `row_version` optimistic locking, and PostgreSQL-backed tests.
- **ADR 0003 (Authentication):** `organization_slug + email` login key, Argon2id password hash (bcrypt fallback), HTTP-only secure cookie sessions, server-side session store.
- **ADR 0004 (RBAC):** Server-side permission middleware checks (deny-by-default), active `UserRole` mapping, permission snapshot as derived cache only.
- **ADR 0005 (Audit):** Same-transaction, append-only minimal audit/event log records for Project and Master Data mutations.
- **ADR 0006 (Fuzzy duplicates):** Warning-only duplicate names based on deterministic normalization. Tax code duplicate remains hard blocking.
- **ADR 0007 (File upload):** ProjectFile metadata in DB + object storage in local MinIO. No parser/OCR processing.
- **ADR 0008 (Future slices):** Explicit `501 Not Implemented` or guarded `422` for future-slice endpoints.
- **ADR 0009 (Seed/Migration plan):** Derive migration and seeds from alpha completed data models and security files. Seed standard roles and permissions.

---

## 7. Current Repo Status

- **Working Repository:** `E:\Project Valora\valora-engineering-phase-sprint-0-starter`
- **Active Git Branch:** `s1-pr-003-persistence-orm-migration-foundation`
- **Workspace Status:** Clean (`git status --short` yields no differences).
- **Files Modified:** Only the newly created onboarding audit report: `docs/audits/AG_ONBOARD_001_ANTIGRAVITY_READINESS_AUDIT.md`.

---

## 8. Missing/Unclear Files

- **Missing Design Package Artifacts:**
  - `02_DESIGN_PRINCIPLES.md` (Not present; final implementation guardrails govern)
  - `16_MIGRATION_AND_SEED_PLAN.md` (Not present; resolved/clarified by ADR 0009)
  - `17_CODEX_PROMPTS_V1_2_ALPHA.md` (Not present; resolved/clarified by implementation prompts and ADR rules)
- **Extracted Directory Completeness:** The extracted completed alpha design slice contains only 5 summary files. The detailed design files are present inside the `valora-design-book-v1.2-alpha-project-master-data-completed.zip` package and have been successfully read.

---

## 9. Confirmation of Code Integrity

This onboarding task was performed as a **READ-ONLY** audit. 
- No backend code has been added, modified, or deleted.
- No frontend code has been added, modified, or deleted.
- No worker code has been added, modified, or deleted.
- No package files or dependency configurations were changed.
- No database tables, models, or migrations were created.

---

## 10. Final Result

```text
PASS
```

---

## 11. Recommendation

Ready for **S1-PR-003 — Persistence / ORM / Migration Foundation** implementation. All guardrails, scoping, constraints, and architecture decision records have been assimilated.
