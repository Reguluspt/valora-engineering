# VALORA immutable document-storage provider selection

**Start time:** 2026-09-19, Asia/Saigon
**Status:** amended 2026-09-19 — S3 adapter locally ready; live AWS run not authorized
**Task:** `VALORA-STORAGE-ARCH-001`

## Initial purpose

Compare Azure Blob Storage and AWS S3 for the first isolated validation of app-owned immutable DOCX
storage. The comparison must preserve create-only publication, exact checksum recovery, server-side
least privilege and staged-upload cleanup. It selects a spike target, not a production provider.

## Strategy

1. Evaluate the exact final object-creation operation, not only the staging API.
2. Prefer official provider contracts for conditional create, multipart/block commit and cleanup.
3. Keep database current-head CAS independent of provider version semantics.
4. Quantify capacity and request drivers without pretending that a region/account price is fixed.
5. Choose one adapter for a bounded spike and defer generic multi-cloud design.

## Checklist

- [x] Compare create-only single-request and staged/multipart final commit.
- [x] Compare ambiguous-response observation and full-checksum verification needs.
- [x] Compare server-side identity and least-privilege options.
- [x] Compare incomplete-upload lifecycle and local test support.
- [x] Define capacity/request/egress cost equations and sample volumes.
- [x] Select exactly one isolated-spike target.
- [ ] Accept retention, deletion, residency, RPO/RTO and cost ceiling.
- [ ] Approve and run a live provider spike.
- [ ] Select a production provider.

## Result

### Provider comparison

| Criterion | AWS S3 | Azure Blob Storage |
|---|---|---|
| Create-only small object | `PutObject` supports `If-None-Match: *`; an existing current key returns `412` | `Put Blob` supports conditional headers; create-only use requires `If-None-Match: *` validation in the chosen SDK/API version |
| Staged final commit | `CompleteMultipartUpload` accepts `If-None-Match`; bucket policy can require the header | `Put Block List` commits staged blocks and supports conditional request headers |
| Concurrent outcomes | Official guidance defines `412` for an existing key and `409` for a conflicting delete/write race | Conditional failure is documented; the exact SDK exception/status mapping must be captured in the spike |
| Stable identity | Bucket + opaque object key; optional version ID when versioning is enabled | Account/container + opaque blob name; response includes ETag and can include version ID |
| Full integrity | Do not infer SHA-256 from ETag; verify provider checksum when exact mode supports it or stream-read and hash | Do not infer SHA-256 from ETag; stream-read and hash unless the exact API returns accepted full checksum proof |
| Lost response | `HEAD`/`GET` same key, then exact size/checksum classification | Get properties/download same blob, then exact size/checksum classification |
| Incomplete upload | Lifecycle can abort incomplete multipart uploads | Uncommitted blocks are garbage-collected after the documented inactivity period; explicit policy is still required |
| Server identity | IAM role/workload identity; bucket policy can enforce conditional request shape | Microsoft Entra managed identity and RBAC are recommended over account keys |
| Local validation | S3-compatible fakes/emulators are available, but the final spike must use AWS S3 for AWS semantics | Azurite is documented for emulator use, but the final spike must use Azure for Azure semantics |
| Ecosystem fit | New cloud/security operating model for this project | Strong Microsoft identity alignment, but independent from consumer OneDrive and its delegated scopes |
| Price drivers | Stored GiB-month, request classes, retrieval tier, replication, KMS/observability and egress | Stored volume, redundancy/tier, operations per transaction band, retrieval, replication and bandwidth |

### Why AWS S3 is the first isolated-spike target

AWS S3 is selected for the first isolated spike because its official documentation explicitly covers
`If-None-Match: *` on both `PutObject` and `CompleteMultipartUpload`, documents competing-write
outcomes and shows a bucket policy that requires the conditional header. That gives the spike a
clear normative predicate: the adapter must prove create-only final publication for both small and
multipart objects.

This choice is deliberately narrow:

- it does not select AWS S3 for production;
- it does not authorize an AWS account, credentials or live request;
- it does not introduce an S3-compatible production promise;
- it does not reject Azure Blob Storage.

Azure remains the second candidate. Its managed-identity fit may dominate production selection once
hosting, account ownership and residency are known. Its isolated spike would need to prove
`Put Block List` create-only behavior, exact checksum reconciliation and lifecycle behavior using
the frozen API/SDK version.

### Isolated S3 spike acceptance outline

The later provider-specific plan must freeze region, bucket, versioning/lifecycle settings, SDK
version, identity policy and object-key format. It must then prove:

1. `PutObject` create succeeds once and the same key is rejected by `If-None-Match: *`.
2. Multipart staging is invisible as a committed object until `CompleteMultipartUpload`.
3. Final multipart commit carries `If-None-Match: *` and a competing committed object wins safely.
4. A deliberately lost create/complete response is reconciled by the same key and exact SHA-256.
5. An existing key with different bytes becomes `RECONCILIATION_REQUIRED`, never overwrite/retry.
6. Incomplete multipart uploads and unbound committed candidates are cleaned under separate rules.
7. Request capture contains no secret or preauthenticated URL.
8. All T1–T14 domain scenarios pass before and after the live-provider evidence.

## Storage economics

### Cost equation

Provider cost must be calculated for a selected region and account using:

```text
stored_GiB_month = sum(retained_revision_bytes × fraction_of_month_retained) / 2^30

monthly_cost =
    stored_GiB_month × storage_rate_by_tier_and_redundancy
  + create_or_write_requests × write_request_rate
  + observe_and_verify_requests × read_request_rate
  + retrieval_GiB × retrieval_rate
  + internet_or_cross_region_egress_GiB × transfer_rate
  + replication_GiB_and_requests
  + encryption_key_calls
  + logs_metrics_inventory_and_backup
```

For a multipart upload with `p` parts, the request model is approximately one initiate, `p` part
writes, one final commit, one observation and optionally one full verification read. A small
single-request upload is approximately one create, one observation and optionally one full read.
Provider SDK behavior must be measured because extra list/probe calls also incur requests.

### Capacity scenarios

These are retained-volume examples, not monthly price quotes:

| Scenario | Documents | Revisions kept/document | Mean DOCX | Retained volume |
|---|---:|---:|---:|---:|
| Small | 1,000 | 10 | 2 MiB | 19.53 GiB |
| Medium | 10,000 | 20 | 5 MiB | 976.56 GiB |
| Large | 50,000 | 40 | 10 MiB | 19,531.25 GiB / 19.07 TiB |

At the medium scenario, initial creation of 200,000 revisions means at least 200,000 write commits
and 200,000 observations. Full read-back verification adds 200,000 read requests and about 976.56
GiB of data read. Multipart use adds initiation and part-write requests. Replication creates another
copy and additional write/transfer charges according to the selected provider policy.

For decision modelling, let `S` be the regional storage price per GiB-month, `W` the write price per
1,000 requests, `R` the read price per 1,000 requests and `E` the applicable retrieval/egress price
per GiB. The medium retained set contributes approximately:

```text
storage       = 976.56 × S
base writes   = 200 × W
observations  = 200 × R
full verify   = 200 × R + 976.56 × E
```

If 10% of those 10,000 documents each produce two new 5 MiB revisions per month, growth is 2,000
objects or 9.77 GiB/month before retention expiry, plus at least 2,000 write and 2,000 observation
requests. This model makes retention duration the dominant controllable storage variable and full
read-back frequency a potentially material retrieval/compute variable.

The following inputs remain required before a monetary estimate is decision-grade:

- hosting region and permitted storage/replica regions;
- current document count and monthly growth;
- DOCX size percentiles, not only average;
- revisions per document per month and retention duration;
- legal-hold fraction and deletion behavior;
- download/export/revalidation frequency and destination network;
- storage tier, redundancy, replication, key and observability choices.

Do not compare providers using a single headline per-GB number. Request class, verification reads,
replication, egress and operational ownership can change the result.

## Verification and corroborating links

Official sources checked on 2026-09-19:

- [AWS S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
  documents `If-None-Match`, `412`/`409` outcomes, multipart behavior and incomplete-upload lifecycle
  guidance.
- [AWS policy enforcement for conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html)
  shows requiring `If-None-Match` for `PutObject` and `CompleteMultipartUpload`.
- [AWS CompleteMultipartUpload API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)
  includes the `If-None-Match` request header.
- [AWS S3 pricing](https://aws.amazon.com/s3/pricing/) identifies storage, request, retrieval,
  replication and transfer dimensions; exact rates depend on region/tier.
- [Azure Put Block List](https://learn.microsoft.com/en-us/rest/api/storageservices/put-block-list)
  documents staged-block commit, conditional headers, response identity, authorization and cleanup of
  inactive uncommitted blocks.
- [Azure Blob conditional headers](https://learn.microsoft.com/en-us/rest/api/storageservices/specifying-conditional-headers-for-blob-service-operations)
  defines conditional request evaluation.
- [Azure Blob authorization](https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-data-operations-cli)
  recommends Microsoft Entra authorization over account keys.
- [Azure Blob pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/) identifies
  volume, operation, transfer and redundancy inputs; displayed rates depend on selected region.

The comparison intentionally does not rely on emulator behavior as production-provider proof.

## Decision

**Select AWS S3 for one isolated architecture spike; keep production provider selection open.**

No live spike starts from this report. First accept ADR 0043's product/governance gates, implement
the provider-neutral fake and independently verify T1–T14. Then prepare a separate S3-specific plan
with cleanup and action-time authority. If the S3 spike fails create-only final commit or exact
lost-response reconciliation, stop; do not silently switch providers inside the same run.

Cross-references:

- [ADR 0043](../adr/0043-app-owned-immutable-document-storage.md)
- [Document Blob Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Completed architecture task](../plan/done/valora-storage-arch-001.md)
- [Initial fallback research](pr07-storage-fallback-options.md)

## Amendments

- 2026-09-19 · § Checklist / Decision: the Product Owner accepted Model A export-only and the
  storage policy baseline. Finalized valuation revisions have a minimum ten-year policy-driven
  retention period; legal hold blocks purge; there is no ordinary finalized-revision hard delete;
  later physical purge must be explicit, authorized and audited. Production targets server-side
  encryption with a VALORA-controlled customer-managed key, separate production/non-production
  boundaries, `RPO <= 15 minutes` and `RTO <= 4 hours`. AWS S3 remains only the future isolated-spike
  target. Production provider and residency are not selected, and no live spike or real customer data
  is authorized by this amendment.
- 2026-09-19 · § Decision: after the provider-neutral fake, PostgreSQL CAS evidence, T1–T14 and
  independent review passed, the Product Owner opened `VALORA-STORAGE-S3-SPIKE-001`. The authority
  currently covers the separate bounded plan and local adapter preparation only. AWS credentials,
  account/bucket/IAM/KMS/lifecycle changes, live requests and costs remain closed until the exact
  reviewed snapshot, account boundary and cleanup manifest receive action-time approval. Production
  provider/residency selection and real customer data remain outside the spike.
- 2026-09-19 · § Result / Decision: G2/G3 adapter preparation and independent code review completed
  on Python `3.14.7`, boto3 `1.43.89` and botocore `1.43.89`. Pushed commit `5f3ab7f` passed GitHub
  CI run `35448475149` on attempt 2, including PostgreSQL and MinIO gates. This evidence does not
  alter the decision: AWS is still only the isolated-spike target, every live preflight value is
  `UNSET`, and production provider/residency selection remains open.
