# VALORA Linux Server v1 Plan

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME OR DEPLOYMENT
**Date:** 2026-10-03
**Task:** `VALORA-TASK-ARCH-WINDOWS-CLIENT-SERVER-001` / Issue #89
**Spec:** [ADR 0050](../adr/0050-linux-server-windows-native-client.md)

## Goal and entry gate

Plan a single-node Linux LTS Server (Ubuntu Server LTS preferred; exact release later) with Docker Engine + Compose, HTTPS LAN ingress and server-hosted React/Fluent 2. PostgreSQL, domain services, app-owned immutable blobs and durable worker remain authoritative/supporting server components. No Kubernetes/HA requirement, Docker Desktop production direction, local LLM, model weights or GPU dependency.

Issue #89 creates no manifest, image, migration or deployment runtime. Each phase requires a separate explicit Product Owner task, green exact baseline, accepted scoped contract and appropriate environment/data boundary. Linux Server Deployment Pilot is distinct from Windows foundation and formal Windows Preview/UAT; it does not certify Software Completion or grant production/cloud/provider activity.

## Bounded sequence

| Phase | Deliverable in a later task | Acceptance evidence |
|---|---|---|
| SRV-0 — release shape | Freeze Linux release, Docker Engine/Compose versions, service/image digest manifest and supported compatibility matrix | Exact server/web/image revisions and repeatable install on isolated fresh Linux; no unstated production-provider or hardware selection |
| SRV-1 — ingress/security | Production-oriented Compose/manifest; reverse proxy/TLS, private networks, service isolation, least-privilege secrets outside repo | HTTPS only to clients; database/Redis/blob/admin ports not exposed to LAN/Internet; invalid certificate fails; exact origins/cookie/CSRF contract preserved; no secrets in repo/images/logs |
| SRV-2 — persistence/startup | Persistent PostgreSQL/blob volumes, supporting Redis policy, deterministic migration step, health/readiness, restart/resource/log limits | Single Alembic head, controlled one-writer migration before readiness, fail closed on mismatch; durable data survives restart/redeploy; worker uses existing job/lease/retry/dead-letter boundary |
| SRV-3 — recovery | Encrypted PostgreSQL + immutable blob backup with release/config manifest, keys managed separately, retention/legal-hold-aware restore runbook | Isolated restore proves consistent revision/CurrentHead/binding/checksum reads and critical workflow smoke; no customer data in public evidence; backup transport outage does not break unrelated transactions |
| SRV-4 — operations/pilot | Sanitized observability, support/rebuild/rollback runbook and separately authorized Linux Deployment Pilot | Operator proves install, restart, recovery, certificate rotation, disk-full/storage/provider failure and rollback; exact pilot evidence plus explicit owner acceptance, no inherited production certification |

Exact manifest/runbook paths and commands must be frozen in each future contract after inspecting live infra. Existing development Compose is an input, not accepted production config. Preserve the selected app-owned immutable storage port; do not silently swap provider or treat Redis/object listings as business truth.

## Security, readiness and operations

- Reverse proxy terminates validated TLS; admin-configured URL and exact trusted origin work across clients. Certificate issuer/trust enrollment/rotation and final hostname are later decisions. No certificate bypass even on LAN.
- Separate ingress from private backend/data service networks; expose only approved ingress. Secrets are provisioned outside git with restricted access and rotation; credentials/signing/backup keys never appear in logs or evidence.
- PostgreSQL and blobs use persistent volumes and least-privilege access. Migrations are deterministic, serialized and release-controlled; readiness checks accepted schema plus required database/blob/worker dependencies without requiring optional providers or AI.
- Backup binds database metadata/CurrentHead to verified exact blob bytes. Document capture ordering, consistency point, encryption/key recovery, retention, restore verification and interruption recovery are explicit SRV-3 contract requirements. Exchange folders are not backup evidence.
- Monitor health/readiness, errors/correlation, worker lease/retry/dead-letter, database locks/connections/WAL, blob failures, disk/capacity, certificate expiry and backup/restore status. Sanitize payloads and rotate logs. Runbooks cover rebuild, restore, migration failure, degraded providers, disk full, restart and controlled rollback.
- No Ollama, vLLM, model downloads/weights, LLM service or GPU service in manifests/install/readiness. Core workflow has no AI dependency. Future provider-backed AI remains [OS-G7 gated](../architecture/VALORA_AI_MASTER_PLAN_V1.md) and reuses existing jobs.

## Preserved authority and deferred choices

[ADR 0043](../adr/0043-app-owned-immutable-document-storage.md) retains immutable bytes, CurrentHead CAS, ten-year minimum retention/legal hold, production key ownership/encryption and future production targets `RPO <= 15 minutes`, `RTO <= 4 hours`. The local pilot does not claim these targets achieved; final operational RPO/RTO and evidence are decided at the later gate without silently weakening accepted production targets. [ADR 0045](../adr/0045-working-copy-change-observation-and-human-confirmed-document-revision.md) preserves human-confirmed revision authority. OneDrive Exchange/Backup and live provider credentials remain separately gated.

Do not freeze hardware purchase, final hostname/certificate source, backup transport/retention execution policy, remote access, concurrency SLA or production rollout here. Operational capacity and restore results must inform those decisions. Formal Windows Preview/UAT remains after Software Completion under the [Preview brief](../implementation/VALORA_WINDOWS_PREVIEW_TASK_BRIEF.md); the [Windows Client plan](VALORA_WINDOWS_CLIENT_V1_PLAN.md) does not embed server operations in MSIX. Product sequencing stays with the [Unified Roadmap](../VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md).
