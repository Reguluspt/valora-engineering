# VALORA S3 G5 action-time checklist

**Task:** `VALORA-STORAGE-S3-SPIKE-001`
**State:** BLANK G4 TEMPLATE — NO AWS VALUE OBSERVED
**Run ID:** `s3-g5-20260919-001`
**Rule:** every row must match before the first mutation; any mismatch stops the invocation.

This checklist is completed only after separate Product Owner approval for G5. Values marked
`PRIVATE OPERATIONAL` stay outside the repository. Evidence references contain sanitized identifiers
or SHA-256 only. A blank cell is not approval and is not evidence.

| Check | Expected frozen value | Actual observed value | Match? | Operator | UTC timestamp | Sanitized evidence reference |
|---|---|---|---|---|---|---|
| Product Owner approval | Exact executable commit, review manifest, boundary, cleanup plan, limits and one invocation |  |  |  |  |  |
| Executable commit | G4-reviewed 40-character SHA in the private runtime manifest |  |  |  |  |  |
| Review manifest | Exact approved SHA-256 in the private runtime manifest |  |  |  |  |  |
| AWS account | `VALORA-NONPROD-AWS-STORAGE-SPIKE-01`; exact 12-digit ID is `PRIVATE OPERATIONAL` |  |  |  |  |  |
| AWS principal | Exact temporary STS assumed-role session ARN in the same frozen account; policy role ARN separately verified |  |  |  |  |  |
| Temporary session | All three explicit session variables present; session token required; no `AWS_PROFILE` |  |  |  |  |  |
| Session expiry | Long enough for one 20-minute invocation plus cleanup; no renewal during the run |  |  |  |  |  |
| Region | `ap-southeast-1` |  |  |  |  |  |
| Bucket | `valora-storage-spike-2c2a9f17-20260919-001`, dedicated general-purpose non-production bucket |  |  |  |  |  |
| Prefix empty before run | `valora-spike/s3-g5-20260919-001/`; zero objects and zero active multipart uploads |  |  |  |  |  |
| Block Public Access | `BlockPublicAcls=true`, `IgnorePublicAcls=true`, `BlockPublicPolicy=true`, `RestrictPublicBuckets=true` |  |  |  |  |  |
| Object Ownership | `BucketOwnerEnforced`; ACLs disabled |  |  |  |  |  |
| Versioning | Never enabled; `GetBucketVersioning` returns no `Status` and no `MFADelete` |  |  |  |  |  |
| Object Lock | Not configured; a bucket with Object Lock or prior versioning history is rejected |  |  |  |  |  |
| Default encryption | `aws:kms`, exact approved non-production customer-managed key ARN, S3 Bucket Key enabled |  |  |  |  |  |
| KMS key | Same account and `ap-southeast-1`; enabled; not production/shared/customer; exact key policy attested |  |  |  |  |  |
| KMS permissions | Harness role has only `kms:GenerateDataKey` and `kms:Decrypt` through S3 for the exact prefix |  |  |  |  |  |
| IAM policy | Rendered policy equals approved SHA-256; no wildcard S3/KMS resource |  |  |  |  |  |
| Bucket policy | Rendered policy equals approved SHA-256; TLS, exact writer and conditional final-create denies present |  |  |  |  |  |
| Lifecycle | Exact-prefix `AbortIncompleteMultipartUpload` after one day; rendered configuration hash matches |  |  |  |  |  |
| SDK runtime | Python `3.14.7`, boto3 `1.43.89`, botocore `1.43.89` |  |  |  |  |  |
| Retry configuration | SigV4; `total_max_attempts=1`; no caller write retry |  |  |  |  |  |
| Fixtures | `FIXTURE_A`, `FIXTURE_B`, `FIXTURE_M` hashes match the private manifest and committed generator |  |  |  |  |  |
| Multipart layout | threshold `8388608`, part size `8388608`, multipart bytes `8392704`, expected parts `2` |  |  |  |  |  |
| Limits | 96 S3 requests; 48 MiB upload; 24 MiB GET; 6 committed objects; 5 MPUs; 9 parts; 12 delete/abort; 16 LIST; 1200 seconds |  |  |  |  |  |
| Cost | normal variable cost `< USD 0.01`; modeled one-run hard ceiling `USD 0.10`; existing dedicated CMK only |  |  |  |  |  |
| T1–T14 before run | Storage service and PostgreSQL suites pass with zero skips |  |  |  |  |  |
| Evidence directory | Private path outside repository; no prior `s3-g5-20260919-001.events.jsonl` |  |  |  |  |  |
| Cleanup permission | Exact-prefix list/get/delete/list-multipart/list-parts/abort only; no bucket-wide delete |  |  |  |  |  |
| Cleanup owner | Product Owner-appointed G5 operator, recorded by safe reference |  |  |  |  |  |
| Configuration restoration owner | Separate setup/control-plane operator; exact approved rollback record available |  |  |  |  |  |

## Go/no-go rule

The operator may pass control to the live harness only when every row is complete and every `Match?`
value is `YES`. The harness independently rechecks commit, runtime, account, principal, region,
bucket, prefix emptiness, public-access block, ownership, versioning, encryption, lifecycle and
bucket-policy hashes before its first write. IAM/key-policy and temporary configuration setup remain
separate operator attestations because the data-plane identity is intentionally denied IAM/KMS
administration reads and mutations.

Any blank, mismatch, expired session, unavailable evidence, out-of-prefix result or unexpected AWS
response is `STOP BEFORE WRITE` or, after the first mutation, `STOP AND CLEAN UP`. It never permits a
second invocation.
