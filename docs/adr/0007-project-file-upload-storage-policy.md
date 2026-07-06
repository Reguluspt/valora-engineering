# ADR 0007 - Project File Upload Storage Policy

## Status

Proposed

## Context

The Sprint 1 Project API includes project file upload, and the Project model includes ProjectFile metadata. Sprint 0 local infrastructure includes MinIO/S3-compatible storage. Later sprints own OCR, document intelligence, import processing, and rendering jobs.

## Decision

Sprint 1 supports ProjectFile metadata and storage boundary only.

Policy:

- Persist `ProjectFile` metadata for uploaded files.
- Store file objects in local MinIO/S3-compatible storage when the implementation environment provides it.
- The database stores object keys and metadata, not file blobs.
- Required metadata includes original filename, storage key, MIME type, size, checksum, category, processing status, uploaded_by, and timestamps as defined by the Project model.
- Initial processing status is `uploaded`.
- No OCR, AI parsing, import, rendering, or derived-file generation runs in Sprint 1.
- Failed storage writes must not leave committed ProjectFile metadata without a corresponding stored object unless the failure is explicitly represented.
- Sensitive file access logging must be added when file read/download behavior is implemented.

## Consequences

- Sprint 1 can support file upload acceptance without implementing later processing pipelines.
- The storage boundary aligns with Sprint 0 MinIO infrastructure.
- Future worker jobs can consume ProjectFile records later.

## Design References

- `infra/README.md`
- `docker-compose.yml`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/01_PROJECT_MODEL.md`
- `v1.2-alpha-project-master-data-completed/12_API/03_PROJECT_API.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`

## Sprint 1 Scope Impact

This ADR unblocks the Project file upload endpoint at a metadata/storage level only.

## What Is Explicitly Not Implemented Yet

- No upload endpoint.
- No storage client dependency.
- No OCR job.
- No AI parsing.
- No document rendering.
- No import processing.
- No worker queue consumer.

## Risks / Follow-up

- Confirm storage client dependency during the implementation PR dependency checklist.
- Confirm local test strategy for MinIO unavailable scenarios.
- Confirm checksum algorithm in implementation before tests are written.
- Add download/read access logging when file retrieval is added.
