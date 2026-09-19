# VALORA S3 G4 live-preflight packet

**Task:** `VALORA-STORAGE-S3-SPIKE-001`
**Gate:** G4 — LIVE PREFLIGHT / BOUNDARY FREEZE
**Status:** STATIC REVIEW PENDING — LIVE AWS NOT RUN
**Prepared:** 2026-09-19, Asia/Saigon
**Production provider:** NOT SELECTED
**Production residency:** NOT SELECTED

## 1. Decision boundary

This packet freezes one synthetic-data-only AWS S3 conformance invocation. It does not authorize
AWS setup or a live call. G5 remains closed until the Product Owner approves the exact executable
commit, review manifest, private account/principal/KMS values, boundary, limits and cleanup plan.

Evidence vocabulary is strict:

- `FROZEN`: exact intended value and local/static evidence are complete;
- `REQUIRES ACTION-TIME VERIFICATION`: the concept and expected value are frozen, but AWS must be
  read at G5; the actual-value cell stays blank in G4;
- `BLOCKED`: a safe boundary cannot be defined;
- `STATIC REVIEW READY`: both independent reviewers accepted one exact snapshot;
- `LIVE AWS NOT RUN`: no AWS API, CLI, STS, S3, IAM or KMS request occurred in G4.

## 2. Exact execution snapshot

| Item | Frozen value |
|---|---|
| G2 reviewed implementation commit | `5f3ab7f6e159aec9cc84aaa24ed04445cbb1215f` |
| G2/G3 docs HEAD before G4 | `aa32ee57a82f9510eb04451adf24e44243787921` |
| Project AI policy commit | `50db35c` |
| G4 executable commit | PENDING BOUNDED G4 IMPLEMENTATION COMMIT |
| G4 review HEAD | PENDING G4 REVIEW FREEZE |
| Python | `3.14.7` |
| boto3 | `1.43.89` |
| botocore | `1.43.89` |
| Signature/retry | `s3v4`; `total_max_attempts=1`; no caller final-write retry |
| Workspace | `F:\Project Valora\valora-operational-frontend` |

G4 changes executable code: the adapter now requires an exact customer-managed KMS key and sends
`ServerSideEncryption="aws:kms"` plus `SSEKMSKeyId` on `PutObject` and
`CreateMultipartUpload`; the one-shot harness is new. Therefore the original G3 review remains valid
historical evidence for `5f3ab7f`, but it is not acceptance evidence for the G4 executable commit.
Both independent reviewers must review the new exact snapshot.

## 3. G4 preflight table — 17/17 rows

| # | Input | G4 state | Exact intended value |
|---:|---|---|---|
| 1 | Reviewed commit | FROZEN | One G4 executable commit and one SHA-256 manifest; no `latest branch` authority |
| 2 | AWS boundary | REQUIRES ACTION-TIME VERIFICATION | Dedicated account reference `VALORA-NONPROD-AWS-STORAGE-SPIKE-01`; private 12-digit ID |
| 3 | Region | FROZEN | `ap-southeast-1`; technical spike only, not production residency |
| 4 | Bucket | REQUIRES ACTION-TIME VERIFICATION | `valora-storage-spike-2c2a9f17-20260919-001`; dedicated general-purpose bucket |
| 5 | Public access | REQUIRES ACTION-TIME VERIFICATION | All four Block Public Access controls `true` at account-effective and bucket levels |
| 6 | Ownership | REQUIRES ACTION-TIME VERIFICATION | `BucketOwnerEnforced`; ACLs disabled |
| 7 | Versioning | REQUIRES ACTION-TIME VERIFICATION | Never enabled; no `Status`, no `MFADelete`, no Object Lock |
| 8 | Encryption | REQUIRES ACTION-TIME VERIFICATION | SSE-KMS with one exact non-production customer-managed key; S3 Bucket Key enabled |
| 9 | Lifecycle | REQUIRES ACTION-TIME VERIFICATION | Exact-prefix abort-incomplete-multipart rule after one day |
| 10 | Identity | REQUIRES ACTION-TIME VERIFICATION | One temporary session for one exact harness role; no profile or long-lived key |
| 11 | IAM/bucket policy | REQUIRES ACTION-TIME VERIFICATION | Rendered reviewed templates and hashes; prefix/KMS/principal scoped |
| 12 | SDK | FROZEN | Python `3.14.7`; boto3/botocore `1.43.89`; SigV4; one total attempt |
| 13 | Key namespace | FROZEN | `valora-spike/s3-g5-20260919-001/`; nine allowlisted synthetic key names |
| 14 | Fixtures | FROZEN | Three `sha256-counter-v1` synthetic fixtures and exact hashes |
| 15 | Limits | FROZEN | One invocation; bounded requests, bytes, objects, parts, lists, deletes, time and cost |
| 16 | Fault method | FROZEN | Botocore transport wrapper suppresses response after one final request returns; second dispatch blocked |
| 17 | Cleanup owner | REQUIRES ACTION-TIME VERIFICATION | Product Owner-appointed G5 operator; exact reference in private manifest |

No row is conceptually undefined. Rows that require AWS reads remain explicitly unverified, not
`PASS`. If the dedicated account, exact role or dedicated CMK does not already satisfy this packet,
G5 stops; G4 authority does not permit creating or changing them.

## 4. Row evidence, ownership, cleanup and classification

### Row 1 — reviewed commit

- Intended value: exact G4 executable commit plus `VALORA_STORAGE_S3_G4_REVIEW_MANIFEST.json`.
- Rationale: only reviewed bytes may reach G5.
- Evidence source: Git commit/tree and SHA-256 file manifest.
- Verification: harness requires clean tracked state and exact `git rev-parse HEAD` match.
- Owner: Codex freezes; Product Owner approves.
- Cleanup implication: none; a changed commit consumes approval and requires a new review.
- Classification: commit/hash `PUBLIC SAFE`; local paths `REPO SAFE`.

### Row 2 — AWS boundary

- Intended value: dedicated non-production account `VALORA-NONPROD-AWS-STORAGE-SPIKE-01`.
- Rationale: isolate the spike from production, customer and personal workloads.
- Evidence source: private approval packet plus action-time `sts:GetCallerIdentity`.
- Verification: exact account ID and role ARN must match before any S3 mutation.
- Owner: Product Owner-appointed account owner and G5 operator.
- Cleanup implication: expire/revoke the temporary session; retain sanitized account reference only.
- Classification: account label `REPO SAFE`; account ID and role ARN `PRIVATE OPERATIONAL`;
  session credentials `SECRET`.

### Row 3 — region

- Intended value: `ap-southeast-1`.
- Rationale: one general-purpose S3/KMS region close to the operator, with no residency claim.
- Evidence source: frozen manifest and AWS public service contracts.
- Verification: explicit SDK region plus bucket-location response must match.
- Owner: Codex freezes; G5 operator verifies.
- Cleanup implication: every resource and key used for the run stays in this region.
- Classification: `PUBLIC SAFE`.

`SPIKE REGION != PRODUCTION DATA RESIDENCY APPROVAL`.

### Row 4 — bucket

- Intended value: `valora-storage-spike-2c2a9f17-20260919-001`, general-purpose, dedicated,
  non-production, synthetic-only and empty under the exact prefix.
- Rationale: no shared workload and a deterministic cleanup target.
- Evidence source: private setup record and action-time S3 reads.
- Verification: region/config reads plus zero objects and zero active uploads under the prefix.
- Owner: setup/control-plane operator; harness rechecks read-only state.
- Cleanup implication: delete no bucket; clean only manifest keys and prefix upload IDs.
- Classification: exact name `REPO SAFE`; account ownership metadata `PRIVATE OPERATIONAL`.

### Row 5 — Block Public Access

- Intended value: `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy` and
  `RestrictPublicBuckets` all `true`.
- Rationale: the spike has no public access requirement.
- Evidence source: `GetPublicAccessBlock` plus effective account-level operator attestation.
- Verification: harness checks bucket controls; operator checks the account-effective control.
- Owner: setup operator; harness fails closed on bucket mismatch.
- Cleanup implication: do not weaken controls for cleanup.
- Classification: configuration `REPO SAFE`; raw account evidence `PRIVATE OPERATIONAL`.

### Row 6 — Object Ownership

- Intended value: `BucketOwnerEnforced`; ACLs disabled; requests send no ACL.
- Rationale: policy-only ownership and no ACL workaround.
- Evidence source: `GetBucketOwnershipControls`.
- Verification: exact action-time equality.
- Owner: setup operator; harness verifies.
- Cleanup implication: no ACL restoration step exists.
- Classification: `REPO SAFE`.

### Row 7 — versioning

- Intended value: versioning `DISABLED_NEVER_ENABLED`; no Object Lock.
- Rationale: smallest safe isolated-spike configuration; create-only enforcement supplies the
  tested invariant, while disabling versioning removes versions/delete markers from bounded cleanup.
- Evidence source: `GetBucketVersioning`, setup attestation and dedicated-empty-bucket evidence.
- Verification: no `Status`, no `MFADelete`; any `Enabled` or `Suspended` result stops G5.
- Owner: setup operator; harness verifies versioning response.
- Cleanup implication: simple exact-key delete; if prior versioning is discovered, stop rather than
  introduce `DeleteObjectVersion` or version-wide cleanup.
- Classification: `REPO SAFE`.

### Row 8 — encryption/KMS

- Intended value: `ServerSideEncryption=aws:kms`, exact dedicated non-production customer-managed
  KMS key in the same account/region, and `BucketKeyEnabled=true`.
- Rationale: preserve ADR 0043's customer-managed-key boundary; no SSE-S3 downgrade.
- Evidence source: adapter request-shape tests, bucket encryption read and private key-policy hash.
- Verification: harness checks default encryption and sends the exact key on `PutObject` and
  `CreateMultipartUpload`; role and key account IDs must match.
- Owner: setup/KMS operator; harness verifies the S3-facing configuration.
- Cleanup implication: restore/remove only the approved temporary key-policy grant; never delete or
  schedule deletion of the key from the harness.
- Classification: key-policy shape `REPO SAFE`; key ARN `PRIVATE OPERATIONAL`; key material `SECRET`
  and never available to the harness.

The key-policy fragment grants the exact harness role only `kms:GenerateDataKey` and `kms:Decrypt`
through S3, scoped by caller account and S3 encryption context. Its `Resource: "*"` is required
inside a policy attached to that one KMS key; it does not mean every KMS key.

### Row 9 — lifecycle

- Intended value: one enabled rule for prefix `valora-spike/s3-g5-20260919-001/`,
  `AbortIncompleteMultipartUpload.DaysAfterInitiation=1`, and no object-expiration rule.
- Rationale: delayed orphan-part backstop; immediate cleanup remains the harness responsibility.
- Evidence source: reviewed lifecycle JSON and action-time configuration hash.
- Verification: harness hashes the canonical returned configuration before writing.
- Owner: setup operator; harness verifies.
- Cleanup implication: restore/remove the temporary rule exactly as approved after zero-prefix proof.
- Classification: `REPO SAFE`.

### Row 10 — temporary identity

- Intended value: one explicit temporary session for the exact G5 role; all three environment
  credential values present; `AWS_PROFILE` forbidden.
- Rationale: no implicit default chain, personal key or reusable credential.
- Evidence source: private session issuance record and `GetCallerIdentity`.
- Verification: harness compares account and full role ARN before S3 mutation.
- Owner: account operator issues; G5 operator runs; harness never acquires credentials.
- Cleanup implication: session expires or is revoked; environment and process memory are cleared.
- Classification: role/account `PRIVATE OPERATIONAL`; credential values `SECRET`.

### Row 11 — IAM and bucket policy

- Intended value: rendered versions of the reviewed IAM, bucket and KMS fragments with exact private
  role/account/key values; hashes are included in the private approval manifest.
- Rationale: data plane is prefix-bounded, encryption-bounded and unable to administer resources.
- Evidence source: policy templates, action-time rendered hashes and read-back bucket-policy hash.
- Verification: setup operator attests IAM/key-policy hashes; harness verifies bucket policy.
- Owner: setup/security operator renders/applies; Codex reviewed templates; harness only reads.
- Cleanup implication: restore/remove the exact temporary role grants and bucket/key/lifecycle
  statements; no broad policy replacement.
- Classification: templates `PUBLIC SAFE`; rendered ARNs/account IDs `PRIVATE OPERATIONAL`.

`sts:GetCallerIdentity` is the only IAM statement with `Resource: "*"` because that API has no
resource-level ARN. All S3 object, bucket and KMS permissions use exact resources. The policy does
not grant `CreateBucket`, IAM/KMS administration, policy mutation, lifecycle mutation, ACL actions,
Object Lock bypass, wildcard object prefixes or version deletion.

Allowed final writes: exact role, exact prefix, TLS, exact KMS boundary, `If-None-Match: *`.
Denied cases: another writer, non-TLS request, unconditional `PutObject`, unconditional
`CompleteMultipartUpload`, another prefix/key or another KMS key. Multipart staging is permitted by
the documented `s3:ObjectCreationOperation=false` exception; final commit is not exempt.

### Row 12 — SDK/runtime

- Intended value: Python `3.14.7`, boto3 `1.43.89`, botocore `1.43.89`, SigV4,
  `total_max_attempts=1`.
- Rationale: exact versions reviewed for request models and transport hook behavior.
- Evidence source: local runtime, request-model tests and runtime manifest.
- Verification: harness compares version strings before constructing clients.
- Owner: G5 operator reproduces; harness verifies.
- Cleanup implication: none; any version drift stops before network mutation.
- Classification: `PUBLIC SAFE`.

### Row 13 — key namespace

- Intended value: run ID `s3-g5-20260919-001`, prefix
  `valora-spike/s3-g5-20260919-001/`, and only the nine cleanup-manifest keys.
- Rationale: server-owned deterministic identity and bounded inventory.
- Evidence source: code constants, live manifest and cleanup manifest.
- Verification: adapter and harness reject every out-of-prefix key; cleanup rejects every
  out-of-manifest result.
- Owner: Codex freezes; harness enforces.
- Cleanup implication: list and mutate only this prefix and allowlist.
- Classification: `REPO SAFE`.

### Row 14 — synthetic fixtures

- Intended value: deterministic generator and hashes in §8.
- Rationale: no operator file path and no real/customer data.
- Evidence source: committed generator, tests and runtime self-test.
- Verification: generated byte length/hash must equal the frozen manifest before AWS clients exist.
- Owner: Codex freezes; harness generates.
- Cleanup implication: all objects are synthetic and unbound; exact keys remain allowlisted.
- Classification: fixture metadata/content `PUBLIC SAFE`.

### Row 15 — limits

- Intended value: exact ceilings in §10.
- Rationale: a tiny bounded request/byte/cost envelope.
- Evidence source: committed constants, manifest and metered request journal.
- Verification: request proxy stops before any operation that would exceed a ceiling.
- Owner: Codex freezes; harness enforces; Product Owner approves.
- Cleanup implication: cleanup has reserved request/delete/list capacity within the ceiling.
- Classification: `PUBLIC SAFE`.

### Row 16 — lost-response fault

- Intended value: one response suppression each for `PutObject` and
  `CompleteMultipartUpload`, after the real transport returns exactly once.
- Rationale: deterministically create an ambiguous application outcome without a replacement write.
- Evidence source: reviewed transport wrapper, no-network unit test and sanitized live journal.
- Verification: final-operation `before-send` arms the wrapper; wrapper delegates one `send`, records
  safe response metadata, closes the response and raises `ReadTimeoutError`; a second dispatch raises
  `HarnessFailure` before transport.
- Owner: harness; Codex/reviewers verify implementation.
- Cleanup implication: observe/stream-verify the same key, then continue cleanup; never rerun create.
- Classification: method and dispatch counts `REPO SAFE`; safe request ID `REPO SAFE`;
  headers/signatures/tokens/payload `SECRET` or prohibited evidence.

### Row 17 — cleanup owner

- Intended value: Product Owner-appointed G5 operator safe reference in the private manifest.
- Rationale: one person/role owns immediate reconciliation, exact-prefix cleanup and external setup
  rollback without widening scope.
- Evidence source: Product Owner approval and action-time checklist.
- Verification: non-placeholder safe reference required before the harness can run.
- Owner: Product Owner appoints; operator executes; harness proves data-plane residue.
- Cleanup implication: incomplete proof makes G6 fail and forbids a second run.
- Classification: safe operator reference `REPO SAFE`; personal contact/identity details
  `PRIVATE OPERATIONAL`.

## 5. Frozen AWS boundary

```text
Account:  VALORA-NONPROD-AWS-STORAGE-SPIKE-01
Region:   ap-southeast-1
Bucket:   valora-storage-spike-2c2a9f17-20260919-001
Prefix:   valora-spike/s3-g5-20260919-001/
Class:    S3 general-purpose bucket
Data:     deterministic synthetic bytes only
Access:   no public access; BucketOwnerEnforced; no ACL
Version:  disabled and never previously enabled
Encrypt:  SSE-KMS, exact dedicated non-production customer-managed key, bucket key enabled
Runtime:  Python 3.14.7 / boto3 1.43.89 / botocore 1.43.89
Retry:    total_max_attempts=1; no caller final-write retry
```

The actual account ID, role ARN and KMS key ARN are private action-time values. They must be present
in the private approved manifest and must match one another. Sanitization does not permit choosing a
different account, role or key after approval.

## 6. Policy artifacts

- IAM identity policy: `VALORA_STORAGE_S3_G4_IAM_POLICY.json`.
- Conditional-write bucket policy: `VALORA_STORAGE_S3_G4_BUCKET_POLICY.json`.
- KMS key-policy fragment: `VALORA_STORAGE_S3_G4_KMS_KEY_POLICY_FRAGMENT.json`.
- Lifecycle configuration: `VALORA_STORAGE_S3_G4_LIFECYCLE_CONFIGURATION.json`.

The setup operator renders only `${HARNESS_ROLE_ARN}`, `${EXPECTED_ACCOUNT_ID}` and
`${KMS_KEY_ARN}`, canonicalizes JSON and records SHA-256 in the private approval packet. No other
substitution is allowed. The bucket policy grants nothing; it adds explicit denies. The IAM policy
grants only boundary reads, exact-prefix object/multipart operations and exact-key KMS use.

## 7. Runtime and retry boundary

The live command accepts no profile, arbitrary endpoint, alternate region/bucket/prefix, customer
file path, retry flag or scenario subset. It requires:

```text
cd backend
python -m tools.valora_storage_s3_live_harness --manifest <private-approved-manifest.json> --evidence-dir <private-directory-outside-repository> --execute-live
```

This command is documentation only in G4 and was not run. The default/self-test path performs no
network call. Live mode requires explicit temporary environment credentials including a session
token and rejects `AWS_PROFILE` to avoid implicit profile selection.

The one-run evidence file is created with exclusive-create semantics before any network call. If it
already exists, the harness refuses to start. Tracked worktree changes, commit mismatch, runtime
drift, prior prefix contents or any preflight mismatch stop before mutation.

## 8. Synthetic fixtures and multipart layout

Generator `sha256-counter-v1` concatenates SHA-256 blocks of
`VALORA-S3-G5-V1:<fixture-id>:<eight-digit-block-number>` and truncates to the exact byte length.

| Fixture | Purpose | Bytes | SHA-256 | Upload path | Parts |
|---|---|---:|---|---|---:|
| `FIXTURE_A` | small create/same-byte/lost-response/cleanup | 4,096 | `0cf110c493ab86b092c293078e3c7742c4bc2874f253c90253baec3c6719226e` | single `PutObject` | 1 |
| `FIXTURE_B` | same-key different bytes/competitor | 4,096 | `57a2d94c0f5364d022b1a2deae4ba36c7c473335a575dc1da2ab4b63cec3d7fe` | single `PutObject` | 1 |
| `FIXTURE_M` | multipart create/lost completion/policy | 8,392,704 | `bc6c5ce6422b75c18018933169b7847661a094ab9b635143fcdd529e6921aedf` | multipart | 2 |

Multipart threshold and part size are both `8,388,608` bytes. `FIXTURE_M` therefore uses one
8 MiB non-final part and one 4 KiB final part, satisfying S3's minimum non-final-part rule.

## 9. Lost-response and request-count proof

For each ambiguous final write, the harness temporarily wraps botocore
`client._endpoint.http_session` at the frozen botocore version. The event-specific
`before-send.s3.<Operation>` handler arms exactly one transport send. The wrapper:

1. records `FAULT_FINAL_WRITE_DISPATCH` with operation and `dispatch_count=1`;
2. calls the original transport `send` exactly once;
3. receives the response and records only status plus a sanitized request ID;
4. closes the response and raises `ReadTimeoutError` before the adapter receives it;
5. rejects any second `before-send` for that operation before network dispatch;
6. restores the original transport and unregisters the hook after the call returns.

The adapter maps the injected timeout to `OUTCOME_UNKNOWN`. Recovery performs same-key observation
and full streamed SHA-256/length verification. There is no replacement `PutObject`, no new multipart
upload and no second `CompleteMultipartUpload`.

Every S3 method passes through a metered proxy that records operation, per-operation sequence,
bounded relative key and byte count. It never records request headers, authorization, signatures,
credentials, payload bytes, presigned URLs or KMS key material.

## 10. Limits and cost ceiling

| Limit | Frozen ceiling |
|---|---:|
| Harness invocations | 1 |
| S3 requests, including preflight and cleanup | 96 |
| Uploaded bytes | 50,331,648 (48 MiB) |
| Streamed GET bytes | 25,165,824 (24 MiB) |
| Committed objects at any point | 6 |
| Multipart uploads initiated | 5 |
| Parts uploaded | 9 |
| Delete + abort requests | 12 |
| LIST requests | 16 |
| Wall time | 1,200 seconds |
| Estimated normal variable cost | `< USD 0.01` |
| Modeled hard one-run variable cost | `USD 0.10` |

The cost model includes bounded S3 storage/requests, data transfer and KMS request usage. It assumes
an already-approved dedicated non-production customer-managed KMS key. A new key is not authorized
by G4; if no suitable dedicated key exists, G5 is blocked rather than silently accepting a new
standing monthly key charge or using a shared/production key.

## 11. S3-1 through S3-13 live matrix

### S3-1 — first conditional PutObject

- Precondition: empty `small-primary.bin`.
- Operation/count: one conditional `PutObject`, one `HeadObject`, one streamed `GetObject`.
- Expected AWS class: create `2xx`.
- Object/VALORA result: one exact `FIXTURE_A` object; `CREATED`, then checksum `MATCH`.
- Cleanup: manifest-key deletion during final cleanup.
- Stop: non-2xx, missing version/request metadata required by adapter, or checksum/length mismatch.

### S3-2 — same key, same bytes

- Precondition: S3-1 exact object remains.
- Operation/count: one conditional `PutObject`, one `HeadObject`, one streamed `GetObject`.
- Expected AWS class: `412 Precondition Failed`.
- Object/VALORA result: original unchanged; `ALREADY_EXISTS`, then exact `MATCH`.
- Cleanup: S3-1 target only; no new object.
- Stop: any success, automatic retry, absent/ambiguous observation or mismatch.

### S3-3 — same key, different bytes

- Precondition: S3-1 exact object remains; attempted bytes are `FIXTURE_B`.
- Operation/count: one conditional `PutObject`, one mismatch GET, one preservation HEAD+GET.
- Expected AWS class: `412 Precondition Failed`.
- Object/VALORA result: original `FIXTURE_A` remains; mismatch maps to
  `RECONCILIATION_REQUIRED`, never overwrite.
- Cleanup: original manifest key only.
- Stop: success, replacement bytes, unverifiable original or another final write.

### S3-4 — staged multipart invisibility

- Precondition: empty `multipart-primary.bin`.
- Operation/count: one initiate, two `UploadPart`, one `HeadObject`.
- Expected AWS class: staging `2xx`, head `404`.
- Object/VALORA result: no committed object before completion.
- Cleanup: upload continues directly to S3-5 or is exact-ID aborted on failure.
- Stop: key becomes visible or part/checksum/number differs.

### S3-5 — conditional multipart completion

- Precondition: S3-4 two-part upload.
- Operation/count: one conditional completion, one HEAD, one streamed GET.
- Expected AWS class: completion `2xx`.
- Object/VALORA result: one exact `FIXTURE_M`; checksum `MATCH`.
- Cleanup: manifest-key deletion.
- Stop: composite checksum/ETag is treated as full SHA-256 or streamed bytes mismatch.

### S3-6 — competing committed object

- Precondition: staged `FIXTURE_M` at `multipart-race.bin`, no committed object.
- Operation/count: one initiate, two parts, one conditional competitor PutObject, one conditional
  completion, one HEAD, one GET, one exact upload abort.
- Expected AWS class: competitor `2xx`; completion `409` or `412`.
- Object/VALORA result: exact `FIXTURE_B` competitor remains; multipart never overwrites it.
- Cleanup: abort only the recorded upload ID; delete the competitor manifest key at final cleanup.
- Stop: completion succeeds, competitor changes or upload ID/prefix differs.

### S3-7 — lost PutObject response

- Precondition: empty `lost-put.bin`; one-shot fault armed.
- Operation/count: exactly one PutObject transport dispatch, then one HEAD and one GET; no second PUT.
- Expected AWS class: transport wrapper received `2xx`, adapter receives `ReadTimeoutError` and
  returns `OUTCOME_UNKNOWN`.
- Object/VALORA result: observe and exact `FIXTURE_A` verification classify the committed outcome.
- Cleanup: manifest-key deletion.
- Stop: dispatch count other than one, no response-before-suppression proof, retry or mismatch.

### S3-8 — lost CompleteMultipartUpload response

- Precondition: empty `lost-complete.bin`; one-shot completion fault armed.
- Operation/count: one initiate, two parts, exactly one final completion dispatch, one HEAD, one GET.
- Expected AWS class: wrapper receives `2xx`; adapter sees `OUTCOME_UNKNOWN`.
- Object/VALORA result: same-key exact `FIXTURE_M` verification; no new upload.
- Cleanup: manifest-key deletion; any residual upload must be exact-ID inventoried/aborted.
- Stop: second completion, replacement upload, missing dispatch proof or mismatch.

### S3-9 — incomplete multipart cleanup

- Precondition: empty `incomplete.bin`.
- Operation/count: one initiate, one part, one exact-prefix upload LIST, one part LIST, one abort.
- Expected AWS class: all `2xx`.
- Object/VALORA result: no committed object; exactly one inventoried upload with one part.
- Cleanup: abort only its exact key/upload ID and later prove zero active prefix uploads.
- Stop: pagination, out-of-prefix result, another part/upload or abort failure.

### S3-10 — unbound committed cleanup

- Precondition: empty `unbound.bin`, synthetic and never database-bound.
- Operation/count: one conditional PUT, HEAD+GET verification, cleanup GET, one guarded delete,
  one absence HEAD.
- Expected AWS class: create/read/delete `2xx`, final HEAD `404`.
- Object/VALORA result: exact unbound candidate deleted; finalized binding path is not used.
- Cleanup: complete in scenario; final inventory still confirms absence.
- Stop: checksum/ETag/version guard mismatch, binding ambiguity or delete failure.

### S3-11 — secret/log inspection

- Precondition: journal created outside repository with mode `0600` where supported.
- Operation/count: no additional AWS request.
- Expected result: only allowlisted sanitized event fields; zero secret-shaped fields.
- Cleanup: retain sanitized evidence only; clear environment/process session state.
- Stop: any authorization/signature/key/token/presigned URL/payload/customer data appears.

### S3-12 — conditional-write bucket policy

- Precondition: exact rendered bucket policy hash passed preflight.
- Operation/count: one unconditional PutObject; one initiate, two parts, one unconditional completion,
  one abort.
- Expected AWS class: both unconditional final operations `403 AccessDenied`; staging succeeds only
  under the documented exception.
- Object/VALORA result: neither denied final operation creates an object.
- Cleanup: abort the policy-test upload; final prefix inventory proves no denied key.
- Stop: either unconditional final operation succeeds or a different policy statement causes an
  unclassified failure.

### S3-13 — domain regression

- Precondition: configured PostgreSQL gate; zero skips allowed.
- Operation/count: fixed T1–T14 pytest command before the first AWS write and after cleanup; no AWS
  request from the tests.
- Expected result: all storage-service/PostgreSQL scenarios pass twice with zero skips.
- Object/VALORA result: local DB CAS/idempotency/recovery invariants unchanged.
- Cleanup: test database follows its existing fixture lifecycle.
- Stop: nonzero exit, any skip or missing pass count; no convenient live rerun.

## 12. Cleanup manifest and runbook

Canonical repo-safe manifest: `VALORA_STORAGE_S3_G4_CLEANUP_MANIFEST.json`.

1. Stop all further spike activity; the harness never starts another scenario after an unexpected
   provider result.
2. List active multipart uploads with the exact run prefix and one bounded page.
3. List objects with the exact run prefix and one bounded page.
4. Reject every out-of-prefix or out-of-manifest result; do not broaden inventory.
5. Record only bounded relative keys and SHA-256 references for upload IDs.
6. Abort only exact in-prefix upload IDs returned by that inventory.
7. Delete only the synthetic unbound committed keys in the cleanup manifest.
8. Versioning is frozen disabled/never-enabled; if versions/delete markers are discovered, stop and
   escalate instead of adding version cleanup authority.
9. List the exact prefix again and require zero residual objects.
10. List active multipart uploads again and require zero residual uploads.
11. The separate setup operator restores/removes only the exact temporary IAM, bucket-policy,
    lifecycle and KMS-policy changes authorized for G5.
12. Revoke or allow expiry of the one temporary session and clear credential environment state.
13. Retain sanitized JSONL, action-time checklist and hashes only; retain no credentials or payload.

No bucket-wide recursive delete, wildcard cleanup, bucket deletion, key deletion or out-of-prefix
mutation is permitted.

If cleanup cannot be proven complete: `G6 = FAIL`, no second spike run, no broad cleanup expansion,
and escalation for new authority.

## 13. Action-time checklist

`VALORA_STORAGE_S3_G4_ACTION_TIME_CHECKLIST.md` is intentionally blank in G4. Rows requiring AWS
reads or private values must remain blank until G5. The private runtime manifest is derived from the
committed template only after Product Owner approval. It contains the exact account ID, role/KMS
ARNs and rendered-policy/checklist hashes; it is never committed.

## 14. Secret classification

| Field | Classification | Repository rule |
|---|---|---|
| Region, run ID, prefix, fixture IDs/hashes/sizes, limits, policy templates | PUBLIC SAFE / REPO SAFE | May commit |
| Bucket name and sanitized account/role/key references | REPO SAFE in this packet | May commit |
| Actual account ID, role ARN, KMS key ARN, rendered private policy hashes, operator identity | PRIVATE OPERATIONAL | Private manifest/checklist only |
| Access key, secret key, session token, credential-process output, Authorization/signature headers | SECRET | Never commit or journal |
| Presigned URL, payload bytes, customer data, real valuation document, KMS key material | SECRET / PROHIBITED | Never accept, commit or journal |
| Safe AWS request ID, relative key, classified result, sequence/timestamp | REPO SAFE after review | Sanitized evidence only |

The harness exposes no arbitrary file option and generates fixtures internally. It does not accept a
customer path, presigned URL, endpoint override, profile, alternate bucket or alternate prefix.

## 15. Static checks and independent review

The final review snapshot must include code, tests, this packet, all policy/config/manifest artifacts,
the action-time checklist, cleanup manifest, the active plan, ADR/contract/status synchronization and
the SHA-256 review manifest.

| Reviewer | Required model | State | P0 | P1 | P2 |
|---|---|---|---:|---:|---:|
| DeepSeek reviewer A | `opencode-go/deepseek-v4.1-flash` | PENDING | — | — | — |
| Gemini reviewer B | `gemini-3.1-pro-high` | PENDING | — | — | — |

Reviewer output is static/plan-readiness evidence, never AWS conformance evidence. Any valid P0/P1/P2
requires correction, new hashes and both reviews rerun. Provider outage yields
`INDEPENDENT REVIEW INCOMPLETE`, not a substituted verdict.

## 16. Known limitations and stop conditions

- No AWS account, role, CMK, bucket or policy was queried or changed in G4.
- Account/principal/key private values and actual configurations remain action-time evidence.
- The lost-response method proves one SDK transport dispatch and deliberate response suppression at
  the frozen botocore boundary; it is not evidence about arbitrary network partitions.
- S3-compatible emulator evidence is not AWS provider-conformance evidence.
- A suitable existing dedicated non-production account, role and CMK are mandatory. Reusing a
  production/shared/personal boundary or creating resources without separate authority is blocked.
- Any runtime/version/hash mismatch, policy drift, versioning history, non-empty prefix, unexpected
  provider response, secret leakage, out-of-prefix inventory, cost/limit pressure, regression or
  cleanup uncertainty stops the run.

## 17. G5 readiness

Current state: `STATIC REVIEW PENDING`; G5 is `CLOSED`; AWS live is `NOT RUN`.

G4 may become `READY FOR PRODUCT OWNER REVIEW` only after the implementation commit and file hashes
are frozen, all local gates pass, both independent reviewers return `READY`, and Codex verifies no
unresolved P0/P1/P2. Product Owner review is not G5 approval. G5 requires a later explicit approval
over the exact private boundary and exactly one invocation.

## 18. Official AWS references

- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjects.html>
