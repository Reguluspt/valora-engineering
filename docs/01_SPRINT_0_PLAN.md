# Sprint 0 Plan — Repository Foundation

## Objective

Prepare the Valora engineering foundation without implementing business logic.

## Deliverables

- Monorepo structure.
- Backend FastAPI skeleton.
- Frontend React/Vite skeleton.
- Worker skeleton.
- Docker Compose for local services.
- PostgreSQL, Redis, MinIO/S3-compatible storage.
- Environment configuration.
- CI skeleton.
- Test/lint baseline.
- Empty bounded-context folders.
- ADR template.
- Pull Request template.
- Sprint 0 Definition of Done.

## Bounded context folders

```text
backend/app/modules/project_master_data/
backend/app/modules/taxonomy_asset_identity/
backend/app/modules/knowledge_evidence/
backend/app/modules/workflow_workbench/
backend/app/modules/document_engine_intelligence/
backend/app/modules/ai_governance_security/
```

## Not included

- No domain tables.
- No migrations beyond technical readiness placeholder.
- No business APIs.
- No UI beyond health/status page.
- No AI provider integration.

## Sprint 0 exit criteria

- `docker compose up -d` starts core infra.
- Backend `/health` returns healthy.
- Frontend dev server starts.
- Worker starts and logs heartbeat.
- CI runs lint/test placeholders.
- Folder boundaries match v1.2-final.
- Engineers can start Sprint 1 from alpha-completed.
