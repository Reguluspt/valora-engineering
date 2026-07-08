# Sprint 8 Production Deployment & Final Hardening Plan

**Task ID:** S8-PR-001  
**Sprint:** Sprint 8 — Production Deployment & Final Hardening  
**Status:** Implementation Plan (Scope Aligned)  

---

## 1. Goal Description

Establish local infrastructure smoke pipelines to verify the production readiness of Project Valora. Connect components (FastAPI backend, PostgreSQL database, Redis metadata cache, MinIO storage, and React client) under Docker environments.

---

## 2. Technical Design Areas

### 2.1 PostgreSQL Persistence Smoke
- Verify Alembic migrations successfully compile tables under local PostgreSQL database configurations.
- Alembic downgrade testing is permitted **only** on empty or isolated test databases. Production rollbacks are not guaranteed and must require backup/restore policies.

### 2.2 Docker Compose Production Configurations
- Formulate a production-like compose configurations setup:
  - Spawns PostgreSQL instances with health checks.
  - Spawns Redis and MinIO storage instances matching base layouts.
  - Builds FastAPI backend running Gunicorn processes.
  - Compiles frontend assets inside Nginx servers.
  - Real worker tasks, document rendering engines, and Celery jobs remain deferred.

### 2.3 Environmental Security & CORS Settings
- Hardening environment vars to use production settings:
  - Disable fastapi `/docs` in production environment configs.
  - Set `CORS_ALLOWED_ORIGINS` to target explicit production hosts.
  - Set token credentials securely.

### 2.4 Testing and Quality Gate Banners
- Require passing tests across both components before deployment triggers:
  - Backend: `pytest` must run successfully on SQLite/PostgreSQL configurations.
  - Frontend: `npm run lint` and `npm run build` must compile cleanly.

---

## 3. Persistent Gaps & Deferred MVP Features
The following features remain out-of-scope for Sprint 8:
1. **Live Grid Asset Loading**: Grid rows continue loading from local mock datasets.
2. **Context Drawer Fetching**: Context panels render from high-fidelity local mock data.
3. **Commit Draft Edits**: Saving cells creates local `InlineEditDraft` records on the backend.
4. **Worker Engines (AI/OCR/Rendering)**: Real worker jobs, rendering engines, and Celery worker executions remain deferred.

---

## 4. Verification Plan

### Manual Verification
- Execute `docker-compose up --build` on local infrastructure.
- Assert Nginx routes query health indices properly.
