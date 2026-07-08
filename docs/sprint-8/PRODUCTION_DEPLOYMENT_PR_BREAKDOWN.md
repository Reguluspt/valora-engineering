# Sprint 8 Production Deployment PR Breakdown

**Task ID:** S8-PR-001  
**Sprint:** Sprint 8 — Production Deployment & Final Hardening  
**Status:** PR Sequencing Plan (Scope Aligned)  

---

## 1. Sequencing Strategy
To ensure incremental reviewability, infrastructure hardening tasks are separated into distinct PR cycles.

---

## 2. PR Matrix

### S8-PR-002: PostgreSQL Migration Smoke & Schema Alignment
- **Scope**:
  - Run database validation schema checks.
  - Execute migration scripts in PostgreSQL containers.
  - Alembic downgrade testing is permitted **only** on empty or isolated test databases. Production rollbacks are not guaranteed and must require backup/restore policies.

### S8-PR-003: Production Env Config & CORS Hardening
- **Scope**:
  - Production environment variable configurations.
  - Secure CORS mapping setup in `app/main.py` routing.
  - Disable Swagger `/docs` routes for production environment flags.

### S8-PR-004: Docker Compose Stacks & Nginx Config
- **Scope**:
  - Compose configuration file mapping DB, Redis, MinIO, API, and Web containers.
  - Nginx configuration templates routing requests safely.
  - Real worker tasks, document rendering engines, and Celery jobs remain deferred.

### S8-PR-005: Security Scans & CI Quality Gates
- **Scope**:
  - Integrate linter, typescript compilers, and pytest gates inside build pipelines.
  - Scan for mock bypasses or mock data leakages.

### S8-PR-006: Final Acceptance & Release Gate Check
- **Scope**:
  - Run regression checks.
  - Confirm all audit logs are updated.
