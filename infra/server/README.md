# SRV-0 Linux Server release foundation

Issue [#101](https://github.com/Reguluspt/valora-engineering/issues/101) authorizes this foundation under [ADR 0050](../../docs/adr/0050-linux-server-windows-native-client.md), [Guardrails](../../ENGINEERING_GUARDRAILS.md) and the [Linux plan](../../docs/plan/VALORA_LINUX_SERVER_V1_PLAN.md). It authorizes no deployment, pilot, cloud staging, provider activation, Software Completion or ASSET_WORKBENCH+. Development `docker-compose.yml` is separate and must never be overlaid onto this foundation.

## Release contract

`release.example.json` is deliberately non-installable: its null fields require a later release packet. Manifest version 1 records a release identifier, exact 40-character server/web Git revisions, the existing single Alembic head, SHA-256 of Compose/proxy/startup artifacts and seven immutable `repository@sha256:digest` image references. Backend, worker and frontend must have the same revision; image records name their existing Dockerfile/build context. Vendor inputs must remain compatible with PostgreSQL 16's data path, Redis 7, the existing MinIO command/file-secret interface and Nginx's template/TLS interface. No Linux, Docker Engine or Compose support version is certified by this shape proof.

The later image build packet must verify `org.opencontainers.image.revision` against the declared source SHA, record actual registry digests, vulnerability/provenance evidence and build `VCS_REF` from that SHA. Source-context `.dockerignore` files exclude environment/secrets/key material; build only from an inspected clean checkout. Nothing supplies secret build arguments or embeds runtime credentials. `validate.py` validates declared inputs and local artifacts; it does not verify registry contents or attest that images were built, installed or deployed. Native-client compatibility/bridge negotiation remains a later WIN integration gate; SRV-0 does not invent a public handshake API.

## Topology and HTTPS

| Network | Members | Exposure |
| --- | --- | --- |
| edge | ingress | One explicitly selected private LAN IPv4 interface, TCP 443 |
| app, internal | ingress, frontend, backend | No host ports or external egress |
| data, internal | backend, worker, PostgreSQL, Redis, MinIO | No host ports or external egress |

Nginx terminates TLS 1.2/1.3 using externally supplied certificate/key files. Unknown SNI is rejected; only the configured hostname serves the app. No HTTP listener, redirect/downgrade or certificate bypass exists. `/api/` goes directly to the backend, preserving Host, cookies, Origin, Referer and CSRF headers. Forwarded protocol is fixed to HTTPS; untrusted forwarded-client headers are replaced. API access logs and both Nginx request logs are disabled to avoid OAuth query/token leakage. Backend does not trust proxy headers as identity. The frontend image serves existing React/Fluent 2 static content with a static-only production config. `/health`, Swagger and OpenAPI are not ingress routes. Application request/file limits remain server-owned; Nginx adds no smaller upload limit.

Final hostname, LAN interface, certificate issuer/source/trust enrollment/rotation and remote access require operator/owner decisions. Example `.invalid` hostname and synthetic digests are proof fixtures only. Later client acceptance must prove valid-chain/hostname success and untrusted/expired/wrong-host certificate rejection, without bypass. Internal container HTTP is private service transport, never a client HTTPS fallback. External-provider egress from API/worker is absent; adding it requires a separately authorized provider/network task. Ingress's edge network permits its supporting network traffic and is not a provider gateway.

## Config and secrets boundary

Copy `server.env.example` and the manifest outside the checkout for a later authorized release. The input file contains only hostname, LAN interface and absolute external secret/blob directory paths. `validate.py --write-env` produces non-secret Compose image/schema inputs outside the checkout and strips ambient `VALORA_*` overrides during validation. Use that reviewed input in a controlled operator environment; clear ambient `VALORA_*` before invoking Compose so environment overrides cannot select another image or origin.

Compose mounts external files as secrets: `postgres_password`, `app_secret_key`, `s3_access_key`, `s3_secret_key`, `tls_certificate.pem`, `tls_private_key.pem`. No secret values appear in examples, the manifest, Compose environment, image layers or validator output. PostgreSQL/MinIO use their file-secret interfaces. The Python startup adapter reads required files before importing existing Settings and overrides any ambient credential values in its own process. API/worker credentials necessarily live in private process memory/environment, not Docker's configured environment. Startup/dependency errors emit a fixed sanitized diagnostic.

Operators must restrict host directory/file access and ensure Compose bind-mounted app secret files are readable by UID 10001 (file-backed Compose secret ownership is host-controlled). Use at least 32 characters for PostgreSQL/app/S3-secret values, 16 for S3 access ID. Existing Settings embeds PostgreSQL credentials in a URL; this adapter requires an alphanumeric/underscore/hyphen password to avoid URL interpretation. Generate fresh high-entropy values outside git. Do not log, run shell tracing on or print resolved secret contents. TLS key access is restricted to ingress. MinIO credentials retain the existing dev adapter shape; scoped service accounts/credential rotation and stronger vendor isolation are SRV-1 hardening, not production certification here.

Pre-provision the local immutable-blob root outside git on a POSIX filesystem supporting atomic hard links, owned by UID/GID 10001 and mode 0700. Bind creation is disabled; missing/unsafe roots fail. API/worker are non-root, read-only except this root and `/tmp`, with all capabilities dropped and no privilege escalation. PostgreSQL and source-artifact data have distinct persistent volumes; immutable document bytes remain the existing app-owned filesystem authority. MinIO holds existing source artifacts, never CurrentHead authority. Redis is ephemeral support, never a job queue or business authority. This layout is not restore/retention/encryption certification. Do not delete volumes as an installation troubleshooting step.

## Startup and health contract

There is no automatic migration on startup and no new migration. A later SRV-2 task owns serialized one-writer migration, bucket provisioning, restart/recovery and rollback execution. On an empty database/bucket, startup exits and the restart policy retries: it neither self-migrates nor silently creates production resources.

Before API/worker exec, and on each container health probe, the adapter checks production HTTPS/local-blob config, mounted secrets, PostgreSQL connectivity and exact `alembic_version`, the existing local blob adapter's directory/no-replace hard-link probe, S3 `head_bucket` and Redis PING. The backend probe also calls the existing loopback `/health` liveness route; the worker probe checks the PID 1 worker process. Startup fails on a dependency/config mismatch. Vendor health gates PostgreSQL/Redis; backend gates worker/ingress startup. Process failures restart; Docker health becoming unhealthy alone does not restart a running container or remove ingress. After startup, health state is an operator signal, not a new API traffic-admission or business authorization mechanism.

Worker health proves process/dependency availability, not progress, lease freshness, queue drain or SLA. Those and total readiness latency/resource limits belong to SRV-2/4. No AI/provider credentials, OAuth calls, model downloads, inference/GPU service or external network is involved in readiness. Existing `/health`, session/cookie/CSRF, tenant/RBAC, business APIs and durable TaskJob/TaskJobAttempt handler/lease semantics remain unchanged.

## Deterministic proof and later preparation

From a clean checkout with Python 3.12+ and Docker Compose available:

```text
python infra/server/validate.py --template
python -m unittest discover -s infra/server/tests -v
git diff --check
```

Template validation renders normalized Compose using synthetic image references and nonexistent external paths; it pulls/starts nothing. Tests reject floating images, mismatched revisions, extra AI services, data-port exposure, non-private networks, host networking, inline secrets, missing mounted secrets, HTTP/wildcard origins and omitted schema inputs. CI repeats these and performs isolated TLS proxy and real dependency proof with disposable generated fixtures. The TLS proof uses the real Nginx envsubst entrypoint; the pinned existing MinIO proof verifies file-mounted credentials and rejection of vendor defaults. Those fixtures do not select the final certificate source or certify production install. The standalone proof commands below additionally require the existing backend dependencies `cryptography` and `boto3`; CI installs them and limits published proof ports to loopback.

```text
python infra/server/tests/proof_tls.py
python infra/server/tests/proof_minio.py
```

For a later authorized release packet only, fill manifest fields (artifact hashes can be obtained with `validate.hashes()`; schema with `validate.schema_head()`), then validate and write inputs:

```text
python infra/server/validate.py --manifest /external/release.json --env /external/server.env --write-env /external/compose.env
docker compose --env-file /external/compose.env -f infra/server/compose.yml config --quiet
```

These are preparation checks, not installation commands or deployment authority. Strict validation rejects the unfilled tracked example. Frozen review/CI evidence binds the foundation Git HEAD; a later installation additionally needs certified actual image set, approved OS/Engine/Compose support, valid TLS/trust, least-privilege provisioning, migration/persistence/recovery and an explicit owner gate.

## Deferred decisions

Hardware purchase; exact Linux release (Ubuntu Server LTS remains preferred family); final hostname; certificate source/trust enrollment; signing certificate; remote access; concurrency SLA; final backup transport/retention execution policy; production RPO/RTO certification; rollout/pilot timing remain OPEN. ADR 0043's accepted future production retention/key ownership/recovery targets are preserved, without claiming compliance. SRV-1 through SRV-4 and WIN-0 remain separate scopes.
