# Infrastructure Notes — Sprint 0

## Local services

```text
PostgreSQL 16: localhost:5432
Redis 7: localhost:6379
MinIO S3 API: localhost:9000
MinIO console: localhost:9001
```

Local credentials are placeholders for developer machines only. Copy
`.env.example` to `.env` before starting local services.

## Production not included

Sprint 0 does not define production Kubernetes/Terraform.

Those can be added after baseline engineering decisions.

## Linux Server foundation

Issue #101's [SRV-0 release foundation](server/README.md) provides separate Compose, TLS/private-network, release-manifest and validation contracts under ADR 0050. It is not a production deployment or pilot authorization; use neither this development stack nor its credentials as production configuration.
