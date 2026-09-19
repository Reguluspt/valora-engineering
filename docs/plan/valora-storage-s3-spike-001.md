# VALORA-STORAGE-S3-SPIKE-001 — Isolated AWS S3 create-only/checksum spike

**Status:** OPEN — PLAN AND LOCAL PREPARATION AUTHORIZED; LIVE AWS ACTIVITY CLOSED
**Opened:** 2026-09-19, Asia/Saigon
**Authority:** ADR 0043/D11 and Product Owner instruction on 2026-09-19

## Goal

Test one AWS S3 adapter against the accepted `DocumentBlobStore` contract without selecting a
production provider. The spike must prove create-only publication for both `PutObject` and
`CompleteMultipartUpload`, and exact full-content SHA-256 recovery after an ambiguous response.

## Authority boundary

The Product Owner has authorized opening this isolated spike and its local preparation. This
authority covers:

- this bounded plan and documentation synchronization;
- a server-side AWS S3 adapter behind the existing four-operation port;
- deterministic local/unit tests and request-shape capture with no AWS endpoint;
- independent review of the exact local implementation snapshot.

It does **not** authorize:

- creating or changing an AWS account, IAM principal/policy, KMS key, bucket or lifecycle rule;
- obtaining, storing or using AWS credentials;
- sending any request to AWS, incurring cloud cost or uploading any bytes to AWS;
- using a production/shared bucket, real customer document or valuation record;
- choosing AWS S3 as the production provider or choosing a production residency region;
- migration, deployment, release, PR-08 or reopening the OneDrive direct-write path.

A live run requires a second, action-time Product Owner approval over the reviewed commit hash and
the completed preflight table below. No automatic retry is permitted in that run.

## Provider semantics frozen by this plan

- Use an AWS S3 **general purpose bucket**, not a directory bucket or an S3-compatible substitute.
- Every final object create carries `If-None-Match: *`. The bucket policy must reject
  `PutObject`/`CompleteMultipartUpload` requests that omit that condition; multipart staging calls
  receive only the documented `s3:ObjectCreationOperation` exception.
- Treat `412 Precondition Failed` as an existing-key result requiring observation and exact
  verification. Treat `409 ConditionalRequestConflict`, timeouts, connection loss and an unreadable
  response as an unknown outcome. None causes an automatic write retry.
- An in-progress multipart upload is staging only. It is not observable as the committed object and
  never becomes authoritative until conditional `CompleteMultipartUpload` succeeds and exact bytes
  are verified.
- ETag is opaque. `PutObject` with SHA-256 supplies a full-object checksum, but SHA-256 for S3
  multipart upload is composite rather than a full-object digest. Therefore the common proof for
  both paths is a streamed `GetObject` of the same key, recomputing SHA-256 and byte length locally.
- A present object with another SHA-256/length is `RECONCILIATION_REQUIRED`. The adapter never
  overwrites, deletes or retries it.
- The adapter creates its client with botocore `total_max_attempts = 1`; this includes the initial
  request and therefore disables SDK-level retry. A caller retry wrapper is also forbidden.
- The exact Python, boto3 and botocore versions resolved during G2 are recorded in local evidence
  and copied into the live preflight row. The broad `boto3>=1.34.0` declaration is not version proof.

## Preflight values required before live approval

Every value must be concrete and reviewed. Secrets, account numbers, access keys, session tokens,
signed URLs and raw policy credentials must not be committed.

| Input | Required live value | Current state |
|---|---|---|
| Reviewed commit | Exact Git SHA and clean relevant diff | UNSET |
| AWS boundary | Dedicated non-production account alias plus privately verified account ID | UNSET |
| Region | One explicit permitted AWS region | UNSET |
| Bucket | Dedicated general-purpose spike bucket; no production/shared data | UNSET |
| Public access | All S3 Block Public Access controls enabled | UNSET |
| Ownership | Bucket-owner-enforced object ownership; ACLs disabled | UNSET |
| Versioning | Explicitly enabled or disabled, with matching cleanup procedure | UNSET |
| Encryption | Exact non-production server-side encryption mode and key boundary | UNSET |
| Lifecycle | Prefix-scoped incomplete-multipart abort rule and observed configuration | UNSET |
| Identity | Temporary workload/session identity; no long-lived key in repo or shell history | UNSET |
| IAM/bucket policy | Exact least-privilege policy and conditional-write enforcement reviewed | UNSET |
| SDK | G2-evidenced Python, boto3 and botocore versions plus retry configuration | UNSET |
| Key namespace | Dedicated opaque `valora-spike/<run-id>/...` prefix | UNSET |
| Fixtures | Deterministic synthetic bytes, SHA-256 and sizes | UNSET |
| Limits | One run, maximum object/part count, byte volume, duration and cost ceiling | UNSET |
| Fault method | Exact transport cut used to lose one response without dispatching a second write | UNSET |
| Cleanup owner | Named operator and verified delete/abort permissions for only the spike scope | UNSET |

The live gate stays closed while any row is `UNSET` or while the exact account/bucket state differs
from the reviewed table.

## Local implementation slices

### S1. Adapter boundary

Implement only the existing `DocumentBlobStore` operations:

- `create_immutable` chooses bounded single-part or multipart creation and maps S3 outcomes into the
  existing closed domain result types;
- `observe` uses exact bucket/key identity and records size, opaque ETag, provider version when
  present and sanitized request identifiers;
- `verify_checksum` streams the object and computes full SHA-256 and byte length;
- `delete_uncommitted_or_expire` accepts only a previously recorded committed, unbound candidate
  key/checksum and cannot target finalized bindings.

The existing port has no multipart upload-ID parameter and is not expanded for this spike. During
cleanup, the one-run harness calls `ListMultipartUploads` with the exact dedicated run prefix,
records the returned key/upload-ID pairs in sanitized evidence, rejects any out-of-prefix result and
aborts only that bounded inventory. The prefix-scoped lifecycle rule is a delayed backstop for an
interrupted harness, not an adapter-domain operation.

No signed URL, browser upload, generic multi-cloud layer, background retry or new domain operation
is introduced.

### S2. Request-shape and failure tests

Local tests must prove the adapter sends the exact conditional header on both final create paths,
uses consecutive multipart part numbers, does not expose a staged upload as committed, and maps
`412`, `409`, timeout, connection loss and a temporary read failure without a second write. Request
capture must assert exactly one dispatched HTTP write for each create/final-commit operation and
must assert `total_max_attempts = 1`. Test doubles may validate request shape but are not evidence of
AWS behavior.

### S3. Live acceptance matrix

The later approved run uses only synthetic fixtures under the one frozen prefix.

| ID | Observation | Required result |
|---|---|---|
| S3-1 | First conditional `PutObject` | One committed object; exact size and streamed SHA-256. |
| S3-2 | Same key/same bytes | `412`, then observe/verify exact existing object; no second success. |
| S3-3 | Same key/different bytes | `412`, then `RECONCILIATION_REQUIRED`; original bytes unchanged. |
| S3-4 | Multipart parts before completion | No committed object at the final key. |
| S3-5 | Conditional multipart completion | One committed object; streamed full SHA-256 matches fixture. |
| S3-6 | Competing committed object | Competitor wins; final multipart create fails safely and never overwrites it. |
| S3-7 | Lost `PutObject` response | Same-key observe and streamed SHA-256 classify outcome without blind retry. |
| S3-8 | Lost completion response | Same-key observe and streamed SHA-256 classify outcome without new upload. |
| S3-9 | Incomplete multipart cleanup | Exact-prefix inventory is recorded; only discovered in-prefix upload IDs are aborted. |
| S3-10 | Unbound committed cleanup | Only recorded unbound candidates are deleted; finalized bindings are ineligible. |
| S3-11 | Secret/log inspection | No credential, token, bytes or presigned URL in output/evidence. |
| S3-12 | Conditional-write policy | Unconditional `PutObject` and final multipart commit are denied. |
| S3-13 | Domain regression | T1–T14 pass before and after the live observations. |

S3-12 validates the current AWS-documented `s3:if-none-match` policy condition and
`s3:ObjectCreationOperation` exception used by the reviewed policy. The run record must distinguish
local adapter evidence, AWS response evidence and post-run cleanup evidence. Passing S3-1–S3-13
does not select a production provider.

## Live execution discipline

After action-time approval, execution is one scripted invocation with no retry wrapper. The script
must write a sanitized manifest before its first provider write containing the run ID, exact prefix,
fixture hashes, expected upload count and object-key cleanup targets. Multipart upload IDs are added
only by the later exact-prefix cleanup inventory. A deliberate lost-response case may cut
the client transport only after the one dispatched request; it must not issue a replacement create.

If the invocation exits unexpectedly, stop and reconcile the recorded keys/upload IDs. Do not rerun
the script. Any further provider mutation requires a new reviewed snapshot and new approval.

## Cleanup and baseline restoration

Cleanup is part of the single approved run, not evidence that unsafe writes were acceptable:

1. inventory the exact run prefix, object versions/delete markers when applicable, and active
   multipart uploads returned for that exact prefix;
2. reject out-of-prefix entries, record the bounded key/upload-ID inventory, then abort only those
   incomplete multipart uploads;
3. delete only synthetic unbound committed spike objects identified in the manifest;
4. verify the prefix has no object/version/delete-marker residue and no active multipart upload;
5. remove or restore temporary IAM/bucket/lifecycle/KMS configuration exactly as approved;
6. revoke the temporary session/credential and preserve only sanitized response/evidence metadata.

Lifecycle abortion is a backstop, not the primary cleanup mechanism. Cleanup failure is reported as
a failed spike and blocks another run; no broad recursive deletion is allowed.

## Stop conditions

Stop before or during the live gate if:

- create-only final commit cannot be enforced for either upload path;
- exact full-object SHA-256 requires trusting ETag or multipart composite SHA-256;
- the SDK cannot send `If-None-Match: *` on `CompleteMultipartUpload` in the frozen version;
- a test or implementation introduces automatic provider-write retry after an ambiguous response;
- least privilege cannot support observation, verification and exact cleanup;
- the account, region, bucket, identity, encryption, lifecycle, fixture or cost boundary is unclear;
- any real/customer data, production resource, secret exposure or cross-prefix deletion is possible;
- T1–T14 regress, independent review is not ready, or cleanup cannot be proven safe.

Failure returns to architecture review. It does not silently switch to Azure or weaken ADR 0043.

## Gates and deliverables

1. **G1 — plan open:** this document, ADR/research/index synchronization and documentation checks.
2. **G2 — local adapter:** surgical implementation plus deterministic request/failure tests; T1–T14
   and affected backend checks green. Record exact Python/boto3/botocore versions and exclude the
   unrelated untracked `scratch/` directory from every commit and evidence snapshot.
3. **G3 — independent review:** DeepSeek v4.1 Flash and Gemini 3.1 Pro High review the exact diff and
   hashes; all valid findings resolved.
4. **G4 — live preflight:** every boundary row frozen, cleanup dry-reviewed and exact commit hash
   presented to the Product Owner.
5. **G5 — action-time approval:** explicit authorization for one invocation only, no retry.
6. **G6 — evidence and closure:** sanitized AWS observations, complete cleanup proof, regression
   results and a recommendation. Production-provider selection remains a separate decision.

## References

- [ADR 0043](../adr/0043-app-owned-immutable-document-storage.md)
- [Document Blob Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Provider selection research](../research/valora-storage-provider-selection.md)
- [Completed provider-neutral fake](done/valora-storage-fake-001.md)
- [AWS conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
- [AWS conditional-write enforcement](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html)
- [AWS object-integrity checks](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html)
- [AWS multipart uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
- [AWS incomplete-multipart lifecycle cleanup](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html)
