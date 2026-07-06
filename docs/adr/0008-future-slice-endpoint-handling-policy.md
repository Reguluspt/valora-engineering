# ADR 0008 - Future-Slice Endpoint Handling Policy

## Status

Proposed

## Context

The Sprint 1 alpha Project API and state machine intentionally reference future-sprint capabilities: taxonomy, asset identity, AI parsing, document generation, knowledge update, workflow transitions, technical specifications, quotes, and appraised price decisions. The Sprint 1 task scope forbids implementing those domains early.

## Decision

Sprint 1 must handle future-slice endpoints explicitly and without side effects.

Policy:

- Implement only the Project and Master Data behavior assigned to Sprint 1.
- For endpoints whose primary behavior belongs to a later sprint, use one of these explicit responses:
  - `501 Not Implemented` when the endpoint is present but the capability belongs to a future sprint.
  - `422 Unprocessable Entity` when the command is known but Sprint 1 state/guards make the requested transition invalid.
- Do not silently no-op future-slice commands.
- Do not create placeholder AI, document, knowledge, taxonomy, pricing, or workflow behavior.
- Limited state skeleton is allowed only when the Sprint 1 data model requires storing the status field and no future-sprint side effect occurs.
- Nullable future-reference columns may exist when required by the Sprint 1 ProjectAssetLine design, but they must not enforce behavior for the future entity.

Endpoint examples requiring explicit deferral or limited handling:

- `POST /api/v1/projects/{project_id}/documents/generate-draft`
- `POST /api/v1/projects/{project_id}/qc/submit`
- future-dependent review completion and approval guards involving identity, taxonomy, knowledge, or appraised price

## Consequences

- Sprint 1 APIs remain honest about unsupported capabilities.
- Acceptance tests can verify explicit deferral instead of accidental behavior.
- Future sprint implementation can replace `501`/guarded `422` responses when the owning module is implemented.

## Design References

- `docs/04_MODULE_OWNERSHIP_MAP.md`
- `valora-design-book-v1.2-final-full-package/README.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `v1.2-alpha-project-master-data-completed/README.md`
- `v1.2-alpha-project-master-data-completed/04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `v1.2-alpha-project-master-data-completed/04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`
- `v1.2-alpha-project-master-data-completed/12_API/03_PROJECT_API.md`

## Sprint 1 Scope Impact

This ADR unblocks Project API work while preventing Sprint 2-6 behavior from leaking into Sprint 1.

## What Is Explicitly Not Implemented Yet

- No taxonomy or asset identity behavior.
- No AI parsing.
- No document generation.
- No QC workflow engine.
- No knowledge update processing.
- No quote/appraised price behavior.
- No workflow workbench behavior.

## Risks / Follow-up

- Some acceptance tests reference future-dependent guards; implementation PRs must classify each test as Sprint 1-safe or deferred.
- API clients must handle explicit `501` responses during Sprint 1.
- Replace deferral responses in the sprint that owns each capability.
