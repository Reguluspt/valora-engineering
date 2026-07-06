# Codex Prompts — Sprint 0

## Prompt 1 — Backend Foundation

```text
Implement only the Sprint 0 backend foundation for Valora.

Use FastAPI.
Create:
- app/main.py
- app/core/config.py
- app/core/logging.py
- app/api/health.py
- empty module folders matching the Design Book
- tests for /health

Do not implement business/domain logic.
```

## Prompt 2 — Frontend Foundation

```text
Implement only the Sprint 0 frontend foundation for Valora.

Use React + TypeScript + Vite.
Create:
- app shell
- health/status page
- placeholder navigation
- environment config

Do not implement Workbench or business UI.
```

## Prompt 3 — Worker Foundation

```text
Implement only the Sprint 0 worker foundation for Valora.

Create:
- worker main entrypoint
- config loading
- heartbeat logging
- empty job registry

Do not implement OCR, AI, rendering, imports, or domain jobs.
```

## Prompt 4 — CI Foundation

```text
Implement CI for Sprint 0.

CI should run:
- backend tests
- frontend lint/build placeholder
- worker tests
- basic formatting checks

Do not add deployment pipeline yet.
```
