# PR-07 storage fallback options if OneDrive write integration remains unavailable

**Start time:** 2026-09-19, Asia/Saigon  
**Status:** initial research complete — follow-up validation requires a separate architecture decision  
**Scope:** read-only provider and architecture research; no credential, live API, runtime, migration or ADR change

## Initial purpose

Give the research team a self-contained account of the OneDrive blocker and identify deployable
fallbacks that preserve PR-07's actual safety goal: a stale execution must not overwrite a newer
document, and an ambiguous provider response must be recoverable without a blind write retry.

This report does not declare OneDrive impossible. It treats the current OneDrive Personal write
mechanism as production-ineligible unless Microsoft documents the missing commit guarantee or a
separately reviewed supported mechanism satisfies the gate.

## Strategy

1. Freeze the verified C2 result and accepted G3 decision before comparing alternatives.
2. Separate product invariants from OneDrive-specific implementation choices.
3. Prefer primary provider documentation for concurrency and resumable-upload claims.
4. Compare consumer-owned drive UX with app-owned object storage and a no-provider-write fallback.
5. Recommend the smallest reversible validation, not an implementation or migration.

## Checklist

- [x] Reconcile ADR 0042/D6, the PR-07 contract, G3 Option A and the public-source clarification.
- [x] Record the authorized public Microsoft Q&A escalation.
- [x] Compare AWS S3, Azure Blob Storage, Google Cloud Storage and Dropbox primitives.
- [x] Evaluate an immutable-object architecture that avoids in-place provider overwrite.
- [x] Identify a safe interim product fallback.
- [x] Define falsifiers and a provider-neutral acceptance matrix.
- [ ] Select a fallback architecture and provider; this requires Product Owner architecture authority.
- [ ] Run any live provider spike; each provider requires a new bounded plan and action-time authority.

## Result

### Situation handed to research

- The only authorized `C2_AUTO_V2` invocation completed without retry. Fresh commit succeeded; after
  a verified concurrent write, the stale final fragment returned `404 itemNotFound`, not the accepted
  `412` proof shape. Exact-item post-read proved the concurrent bytes, eTag and identity were preserved
  in that run.
- Microsoft public documentation does not bind creation-time `If-Match` to automatic upload-session
  completion and does not define that `404` as a stable stale-write rejection.
- The Product Owner approved G3 Option A: retain D6, close C2 research and keep
  `runtime_gate=BLOCKED`. No additional OneDrive mutation is authorized.
- Temporary delegated `Files.ReadWrite` and the temporary client secret were removed; the PR-05
  read-only baseline remains.
- A sanitized question was posted to Microsoft Q&A on 2026-09-19 and is awaiting an attributable
  answer: [OneDrive Personal upload session: does If-Match remain a commit precondition?](https://learn.microsoft.com/en-us/answers/questions/6008198/onedrive-personal-upload-session-does-if-match-rem).

### Non-negotiable acceptance matrix

| Criterion | Required evidence |
|---|---|
| No stale overwrite | Normative final-commit CAS/precondition, or an architecture that never overwrites a mutable provider object |
| Stable identity | Immutable provider version/object ID or server-owned key; no silent path/name rebinding |
| Ambiguous response | Exact read-after-error can classify old, expected output or third state; no blind retry |
| Resumable transfer | Candidate bytes can be staged/chunked without becoming the current document before commit |
| Integrity | Provider metadata or a post-read proves the exact expected full-object checksum |
| Least privilege | Server-verifiable, scoped credentials; no secret or preauthenticated URL in browser logs, audit or persistence |
| Recovery | Failed staging is abortable/collectable; committed prior versions remain recoverable under a declared retention policy |
| Valora lineage | Provider result can bind once to the durable intent and immutable Document Revision |
| Operational fit | Cost, retention, regional placement, backup, incident handling and key rotation are owned explicitly |

### Ranked architecture options

| Rank | Option | Safety fit | Main trade-off | Research disposition |
|---|---|---|---|---|
| 1 | App-owned immutable object per revision plus database CAS pointer; optional OneDrive export is non-authoritative | Strongest: create-only objects remove in-place overwrite; exact checksum post-read settles ambiguous responses; DB transaction controls the current revision | Changes storage ownership, privacy/retention duties and the consumer-drive UX | **Recommended validation path** |
| 2 | App-owned mutable object with provider-native conditional final commit | Strong when final commit carries documented `If-Match`/generation CAS; smaller conceptual change than immutable objects | Still couples correctness to provider commit semantics and requires app-operated storage | Validate only if immutable-per-revision cost is unacceptable |
| 3 | Dropbox consumer storage with upload-session finish using `WriteMode.update(rev)` and `strict_conflict` | Promising revision conflict primitive and consumer OAuth | Commit is documented in terms of a path; exact ID targeting and ambiguous-final recovery still need proof | Consumer-UX candidate, not yet D6-equivalent |
| 4 | Read-only OneDrive import/revalidation plus explicit download/manual replace | Safe interim because Valora performs no provider write | Loses automatic sync and makes the user responsible for replacing the document | **Deployable degraded mode** after UX/product approval |
| 5 | Generic BYO/pluggable provider | Avoids single-provider lock-in eventually | Multiplies auth, recovery and conformance surface before one safe adapter exists | Defer until one fallback passes |

### Provider evidence for app-owned storage

| Provider | Documented primitive | Assessment |
|---|---|---|
| AWS S3 | `CompleteMultipartUpload` accepts `If-Match`; mismatch returns `412`, while a conflicting operation can return `409`. Bucket policy can require conditional writes. | Clearest documented multipart final-commit CAS in this pass. Strong candidate for option 2; option 1 needs only create-only keys plus checksum verification. |
| Azure Blob Storage | Staged uncommitted blocks are published by `Put Block List`; that operation supports conditional request headers. Blob versioning and soft delete preserve prior states. | Strong Microsoft-ecosystem candidate. Validate `Put Block List` with frozen `If-Match`, version ID and full-content checksum in a local emulator or isolated account before selection. |
| Google Cloud Storage | `ifGenerationMatch` makes mutations conditional and returns `412`; conditional insert/compose operations are documented as safe read-modify-write/retry primitives. Resumable upload is supported. | Strong generation-CAS model. A spike must prove the chosen resumable/compose sequence and exact ambiguous-response reconciliation. |
| Dropbox | Upload sessions defer saving until `finish`; `WriteMode.update(rev)` overwrites only when the current revision matches, and `strict_conflict` strengthens conflicts. | Best consumer-drive lead found, but current official SDK text describes saving to a file path. Exact immutable-ID targeting and recovery semantics remain gating questions. |
| Google Drive consumer API | Resumable update by file ID is documented, but this pass found no current primary statement giving a frozen-revision precondition at final resumable commit. | Do not substitute one undocumented consumer-drive behavior for another. Exclude unless normative evidence is found. |

### Recommended target shape

The smallest safety-preserving redesign is not another mutable-file adapter. It is:

```text
deterministic DOCX bytes
  -> create immutable object at tenant/document/intent/content-digest
  -> exact HEAD/GET checksum verification
  -> short database CAS transaction publishes Document Revision N+1 as current
  -> optional user export or provider copy remains a derived artifact
```

This keeps Word as input/output rather than source of truth, matches Valora's existing durable-intent
and immutable-revision model, and reduces the provider commit requirement from “conditionally replace
the user's live file” to “create this content-addressed object once.” If the create response is lost,
the same key plus expected checksum can be observed safely; a different checksum is a third state and
must fail closed. A unique intent/digest mapping prevents a second revision from the same provider
commit.

### Falsifiers and unresolved questions

- Reject any provider if its final publish step cannot carry the conditional precondition documented
  for that same operation.
- Reject immutable-object storage if tenant isolation, retention/deletion, encryption, regional
  placement or recoverable checksum verification cannot meet Valora guardrails at acceptable cost.
- Reject Dropbox direct sync unless official documentation or a bounded reviewed test proves exact
  identity behavior, revision conflict at session finish and read-after-ambiguous-response recovery.
- Do not infer full-object integrity from an opaque/multipart eTag; require an explicit checksum or
  read-back digest.
- Do not call an exported OneDrive/Dropbox copy authoritative unless a new ADR defines conflict,
  lineage and user-edit semantics for that copy.
- File-size distribution, expected revision count, retention period, data residency and monthly
  egress are not yet quantified; provider cost ranking is therefore intentionally provisional.

### Adversarial review and pre-mortem

The strongest case against option 1 is product fit, not concurrency: users may reasonably expect the
editable file to remain in their own drive, while app-owned storage makes Valora responsible for
custody, retention, deletion and export. Dropbox deserves a fair comparison because its documented
revision update mode could retain consumer ownership with less UX change if its identity and recovery
gaps are resolved.

Assume the preferred redesign failed after launch:

| Failure mode | Earliest warning | Kill/mitigation condition |
|---|---|---|
| Privacy or residency policy rejects app-owned DOCX custody | No approved retention/residency owner during ADR review | Do not open implementation; retain read-only/manual mode |
| Immutable revisions create uncontrolled storage cost | Revision-count and file-size model has no bounded retention result | Require lifecycle policy, legal retention exception and cost ceiling before provider selection |
| Exported drive copy silently becomes the user's real source | Users edit exported files and expect automatic merge | Label export as derived, preserve read-only re-import/revalidation, or reject the export-only product model |
| Lost-response recovery cannot prove the created bytes | Provider lacks a stable object version plus full checksum/read-back | Reject the provider; do not infer success from eTag or status alone |
| Provider-neutral fake masks a cloud-specific race | Live spike cannot reproduce CAS failure and ambiguous response independently | No ADR acceptance until the isolated provider evidence passes independent review |

### Smallest reversible validation sequence

1. **Architecture-only gate:** decide whether app-owned storage is acceptable and whether the user
   copy becomes export-only. No code or provider account is needed.
2. **Provider-neutral fake:** model create-only object, lost success response, checksum reconciliation,
   duplicate intent and database CAS loss. Reuse the PR-07 durable-intent state machine.
3. **One isolated provider spike:** stage chunks, create/commit against a frozen version, perform a
   concurrent write, test `412/409`, lose the final response deliberately, reconcile by immutable
   identity/checksum and clean up. No retry of the write under test.
4. **Independent review:** verify request capture, provider contract, cleanup, no secret leakage and
   exact acceptance-matrix coverage before any ADR proposal.
5. **ADR successor:** only after the spike passes, propose the storage-ownership, export and migration
   decision. PR-07 runtime remains blocked until that authority is accepted.

## Verification

- [AWS S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
  and [`CompleteMultipartUpload`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html),
  accessed 2026-09-19.
- [Azure `Put Block List`](https://learn.microsoft.com/en-us/rest/api/storageservices/put-block-list),
  [conditional headers](https://learn.microsoft.com/en-us/rest/api/storageservices/specifying-conditional-headers-for-blob-service-operations)
  and [blob soft delete/versioning](https://learn.microsoft.com/en-us/azure/storage/blobs/soft-delete-blob-overview),
  accessed 2026-09-19.
- [Google Cloud Storage request preconditions](https://cloud.google.com/storage/docs/request-preconditions),
  [resumable uploads](https://cloud.google.com/storage/docs/resumable-uploads) and
  [retry/idempotency guidance](https://cloud.google.com/storage/docs/retry-strategy), accessed
  2026-09-19.
- [Dropbox upload-session and write-mode types](https://dropbox.github.io/dropbox-sdk-js/global.html),
  accessed 2026-09-19.
- Repo authority was checked at local HEAD `46e0792b3ae697158f0fe38db8100fbd4afdc6fc` after fetching
  `origin/main` `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`. Existing user changes were preserved.
- Three requested research-agent lanes could not run because the workspace reported exhausted agent
  credits. The lead completed this first pass directly; independent research review is still pending.

## Decision

**Follow-up research, no architecture change.** Keep D6 and `runtime_gate=BLOCKED`. Use option 1 as
the preferred validation target and option 4 as the product-safe degraded mode. Do not select a cloud
provider or implement/migrate from this report.

The next owner decision is limited to whether the research team may draft an ADR comparison for
app-owned immutable storage versus consumer-owned Dropbox, including cost/data-residency inputs. Any
live spike needs separate provider-specific authority.

Cross-references:

- [G3 architecture decision](../plan/done/pr07-g3-architecture-decision.md)
- [OneDrive stale-session evaluation](pr07-stale-session-404-decision.md)
- [Public Microsoft clarification result](pr07-provider-clarification-public-sources.md)
- [Sanitized Microsoft question packet](../ref/pr07-provider-clarification-question-packet.md)
- [ADR 0042](../adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md)
- [PR-07 sync/conflict contract](../implementation/VALORA_UIUX_V2_3_PR07_SYNC_CONFLICT_CONTRACT.md)
