# VALORA-STORAGE-S3-SPIKE-001 — Isolated AWS S3 create-only/checksum spike

**Status:** CLOSED/DEFERRED BY PRODUCT OWNER BEFORE LIVE G5 INVOCATION
**Opened:** 2026-09-19, Asia/Saigon
**Authority:** ADR 0043/D11 and Product Owner instruction on 2026-09-19

## Product Owner closure — 2026-09-20

G1, G2 and G3 are complete. G4 static review is complete and all implementation/evidence is
retained. G5 live AWS was **NOT RUN** and G6 production/provider selection was **NOT RUN** because
the Product Owner selected a different deployment path for the current phase.

No AWS account/resource was created, no AWS credential was used and no STS/S3/IAM/KMS call was
made. No live AWS provider claim was established. AWS remains an available future adapter/reference;
it was not rejected or found incompatible, and it is not selected as the current production
provider. The current pilot path is recorded in
[the successor decision](../research/valora-storage-provider-selection-2.md).

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
- independent review of the exact local implementation snapshot;
- G4-only boundary freeze, policy templates, no-network harness preparation and action-time
  checklist. This preparation does not open G5 or authorize an AWS request.

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
| Reviewed commit | Exact Git SHA and clean relevant diff | FROZEN — exact executable/review commits and 21-file hashes recorded by the review manifest; corrected same-snapshot review passed |
| AWS boundary | Dedicated non-production account alias plus privately verified account ID | REQUIRES ACTION-TIME VERIFICATION — alias `VALORA-NONPROD-AWS-STORAGE-SPIKE-01`; account ID stays private |
| Region | One explicit permitted AWS region | FROZEN — `ap-southeast-1` |
| Bucket | Dedicated general-purpose spike bucket; no production/shared data | REQUIRES ACTION-TIME VERIFICATION — exact name `valora-storage-spike-2c2a9f17-20260919-001` and empty dedicated state |
| Public access | All S3 Block Public Access controls enabled | REQUIRES ACTION-TIME VERIFICATION — all four controls frozen `true` |
| Ownership | Bucket-owner-enforced object ownership; ACLs disabled | REQUIRES ACTION-TIME VERIFICATION — `BucketOwnerEnforced` |
| Versioning | Explicitly enabled or disabled, with matching cleanup procedure | REQUIRES ACTION-TIME VERIFICATION — never enabled; Object Lock absent |
| Encryption | Exact non-production server-side encryption mode and key boundary | REQUIRES ACTION-TIME VERIFICATION — SSE-KMS, one customer-managed key, bucket key enabled |
| Lifecycle | Prefix-scoped incomplete-multipart abort rule and observed configuration | REQUIRES ACTION-TIME VERIFICATION — incomplete multipart abort after one day |
| Identity | Temporary workload/session identity; no long-lived key in repo or shell history | REQUIRES ACTION-TIME VERIFICATION — one exact private STS assumed-role session ARN and explicit temporary session token |
| IAM/bucket policy | Exact least-privilege policy and conditional-write enforcement reviewed | REQUIRES ACTION-TIME VERIFICATION — render only approved placeholders and match canonical hashes |
| SDK | G2-evidenced Python, boto3 and botocore versions plus retry configuration | FROZEN — Python `3.14.7`, boto3/botocore `1.43.89`, SigV4, `total_max_attempts=1` |
| Key namespace | Dedicated opaque `valora-spike/<run-id>/...` prefix | FROZEN — `valora-spike/s3-g5-20260919-001/` |
| Fixtures | Deterministic synthetic bytes, SHA-256 and sizes | FROZEN — fixtures A/B 4,096 bytes; M 8,392,704 bytes; hashes in packet/manifest |
| Limits | One run, maximum object/part count, byte volume, duration and cost ceiling | FROZEN — limits in packet; 20 minutes and USD 0.10 variable-cost ceiling |
| Fault method | Exact transport cut used to lose one response without dispatching a second write | FROZEN — one delegated HTTP send, response suppressed, second dispatch blocked |
| Cleanup owner | Named operator and verified delete/abort permissions for only the spike scope | REQUIRES ACTION-TIME VERIFICATION — private operator ID and exact-prefix permissions |

The canonical 17-row rationale, evidence source, action-time verification and cleanup implications
are in the [G4 preflight packet](../implementation/VALORA_STORAGE_S3_G4_PREFLIGHT_PACKET.md). G5 stays
closed while a row is `BLOCKED`, an action-time check is incomplete, or actual state differs from
the reviewed boundary.

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

1. inventory the exact run prefix and active multipart uploads returned for that exact prefix; stop
   if versioning history or Object Lock exists because this frozen bucket must never have either;
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

1. **G1 — plan open: COMPLETE.** This document, ADR/research/index synchronization and
   documentation checks passed at commit `2162f71078a1e980c0129fa8e9fbe2d8d36e43d3`.
2. **G2 — local adapter: COMPLETE.** The isolated adapter and deterministic request/failure tests
   pass locally and at pushed commit `5f3ab7f6e159aec9cc84aaa24ed04445cbb1215f`. No runtime wiring,
   migration or provider request was added.
3. **G3 — independent review: COMPLETE FOR THE LOCAL CODE SNAPSHOT.** DeepSeek v4.1 Flash and
   Gemini 3.1 Pro High both returned `READY` with no P0–P2 finding on the exact six-file hash
   manifest below.
4. **G4 — live preflight: COMPLETE (STATIC ONLY).** The 17-row intended boundary, no-network
   harness, policy templates, cleanup manifest/runbook and action-time checklist are frozen. On the
   corrected 21-file snapshot, DeepSeek v4.1 Flash and Gemini 3.1 Pro High both returned `READY`
   with no P0–P3 finding. No live boundary or AWS request is approved.
5. **G5 — action-time approval/live invocation: NOT RUN; CLOSED/DEFERRED BY PRODUCT OWNER.**
6. **G6 — live evidence/provider selection: NOT RUN.** No AWS production/provider conclusion was
   reached; the G1-G4 static implementation and evidence remain available for a future decision.

## G2/G3 local evidence

- Base branch/HEAD: `feat/operational-frontend-m365` at
  `2162f71078a1e980c0129fa8e9fbe2d8d36e43d3` before the G2 commit.
- Resolved local runtime: Python `3.14.7`, boto3 `1.43.89`, botocore `1.43.89`.
- Retry configuration: botocore `Config(retries={"total_max_attempts": 1}, ...)`; request-shape
  tests validate the installed botocore model with `Stubber` and capture one final SDK dispatch.
- Local tests: adapter plus T1–T14 `42 passed`; affected storage/document/M365 selection
  `145 passed, 11 skipped`. The skips are PostgreSQL-only because no local PostgreSQL URL or Docker
  daemon was available; they are not counted as pass and remain for CI.
- Full local backend suite: `1466 passed, 99 skipped, 23 warnings`. The skips are the repository's
  environment-gated PostgreSQL and MinIO proofs; a configured but unavailable local MinIO endpoint
  was diagnosed separately, then omitted from the isolated pytest process so those proofs skipped
  explicitly instead of being misreported as adapter regressions.
- Pushed implementation commit: `5f3ab7f6e159aec9cc84aaa24ed04445cbb1215f`. GitHub CI run
  `35448475149`, attempt 2, passed all four jobs; backend passed `1565` tests with `29` warnings,
  including PostgreSQL and MinIO gates. Attempt 1's only failure was the unrelated pre-existing
  PR-01 concurrent replay race; the base SHA had passed the same test, so the failed job was rerun
  once after diagnosis and no code was changed to mask it.
- Static checks: focused Ruff, Python compilation and `git diff --check` pass.
- Reviewer snapshot hashes:
  - adapter: `9bf7552fbaa322b91a7251132719fd17ed41a96b660a05706cad3487e0b685d9`;
  - adapter tests: `4e3b77bcddfeb96c8c50cedd2501e309f429e7ef8aff9ca1f56963a5f1bce78b`;
  - complete six-file manifest verified independently by both reviewers; DeepSeek and Gemini both
    returned `READY — no P0/P1/P2 findings`.
- No AWS credential, endpoint, account, bucket, IAM, KMS, lifecycle, live request, real customer
  data or cloud cost was used. The unrelated untracked `scratch/` directory remains excluded.

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
