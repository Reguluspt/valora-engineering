# S8-PR-001: Sprint 8 Production Deployment & Final Hardening Design Intake Report

This report documents the design intake and initial architecture alignment for Sprint 8 (**Production Deployment & Final Hardening**) of Project Valora.

## 1. Scope Verification
- **Allowed Scope**: Plan final release gates, postgresql migrations check, docker compile configuration, environment file security parameters, CORS boundaries, and PR timelines.
- **Forbidden Scope**: Zero lines of frontend or backend implementation code modified. Zero backend schema adjustments, API clients, or database migrations created.

## 2. Infrastructure & Deployment Hardening Parameters

The following outlines the core security and configuration controls to be verified in Sprint 8:

| Verification Context | Hardening Control / Standard | Target Configurations | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **PostgreSQL Persistent** | Alembic database migrator | `backend/alembic/env.py` | Runs schema creations in local postgres environments |
| **Docker Compose** | Local compose stacks | `docker-compose.yml` | Spawns healthy DB, Redis, MinIO, API, and Nginx instances |
| **Backend Environment** | CORS and database URLs | `.env.production` | Restricts API access to trusted origins |
| **Security Headers** | CORS configurations | `backend/app/main.py` | Block unauthorized origins |
| **RBAC Scanners** | Scope-based auth checks | `backend/app/core/rbac.py` | Reject requests lacking permission |

---

## 3. Persistent Gaps & Deferred MVP Features
The following items remain out-of-scope for the MVP foundation and are formally deferred to post-MVP sprints:
1. **Live Asset Grid Row Querying**: Frontend retains local virtualized mock asset lines.
2. **Context Drawer Live Context Details**: Renders via local mock context dictionary assets.
3. **Commit Draft Edits**: Saving cells creates backend `InlineEditDraft` records. Official mutations to `ProjectAssetLine` or valuation data are blocked.
4. **Worker Engines (AI/OCR/Rendering)**: Real worker jobs, rendering engines, and Celery worker executions remain deferred. Redis is run as a basic cache service container only; no background job workers are scheduled.

---

## 4. Final Result
- **Result:** PASS WITH FIXES
- **Recommendation:** Proceed to implementation planning.
