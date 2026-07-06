# Valora Engineering Phase — Sprint 0 Starter

**Version:** sprint-0-starter  
**Created:** 2026-07-06  
**Source of truth:** Valora Design Book v1.2-final  
**Scope:** Repository foundation only

## Status

Engineering Phase is now open.

Sprint 0 creates the technical foundation only. It intentionally does **not** implement business/domain logic yet.

## Sprint 0 Goal

Create the baseline repository structure, local development environment, CI skeleton, and empty module boundaries for later implementation.

## What is included

```text
backend/             FastAPI skeleton
frontend/            React + TypeScript + Vite skeleton
worker/              Python worker skeleton
infra/               Docker, database, object storage, Redis notes
docs/                Sprint 0 plan, guardrails, DoD, Codex prompts
.github/workflows/   CI skeleton
docker-compose.yml   local infrastructure
Makefile             developer commands
.env.example         local env template
```

## Sprint 0 allows

```text
monorepo structure
Docker/dev environment
FastAPI skeleton
React skeleton
worker skeleton
PostgreSQL/Redis/S3-compatible storage wiring
CI skeleton
lint/test baseline
environment config
empty DDD module boundaries
```

## Sprint 0 forbids

```text
Project CRUD business logic
Master Data CRUD business logic
Taxonomy engine
Asset identity engine
Knowledge engine
AI extraction
Document rendering
Workbench full UI
```

## Start commands

```bash
cp .env.example .env
docker compose up -d
make backend-dev
make frontend-dev
```

## Design reference

Use `valora-design-book-v1.2-final-full-package.zip` as the implementation source of truth.

Codex must not invent domain behavior. If design ambiguity appears, create an ADR/change request.

## Codex / Engineering Rules

Before giving any implementation task to Codex, read:

```text
CODEX.md
ENGINEERING_GUARDRAILS.md
PR_RULES.md
```

For Sprint 0, Codex must stay inside repository foundation scope only.
