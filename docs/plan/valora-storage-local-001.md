# VALORA-STORAGE-LOCAL-001 — Linux local immutable DocumentBlobStore

**Status:** G6 REVIEW CANDIDATE — FINAL VERDICTS REQUIRED
**Opened:** 2026-09-20, Asia/Saigon
**Authority:** ADR 0043, the Document Blob Storage contract and the 2026-09-20 Product Owner
deployment-path decision

## Goal

Implement a production-shaped, Linux-only `LocalFilesystemDocumentBlobStore` for the current VPS
pilot path without changing `DocumentRevision`, `DocumentRevisionCurrentHead`, the durable execution
state machine or the four-operation provider-neutral port.

Local filesystem bytes become authoritative only for revisions successfully finalized through the
existing DB CAS flow. This task does not claim HA, hardware WORM, compliance retention, encrypted
local-disk custody, the long-term RPO/RTO targets or general production-provider conformance.

## Existing capability and new scope

| Surface | State before this task | This task |
|---|---|---|
| `DocumentRevision` / `CurrentHead` DB authority | Implemented | Preserve unchanged |
| Durable storage intent/event/state/binding | Implemented | Preserve semantics; admit provider kind `local` |
| Four-operation `DocumentBlobStore` port | Implemented | Preserve unchanged |
| Deterministic fake and T1-T14 | Accepted | Keep passing unchanged |
| AWS S3 adapter/evidence | G1-G4 static retained | Do not delete, invoke or wire |
| Linux local immutable adapter | Implemented at G4 | T1-T14/L1-L17 proved at G5; G6 pending |
| Deployment provider/root configuration | Implemented at G4 | Validated settings, fail-closed factory and persistent volume shape |
| OneDrive Exchange / encrypted Backup | Partial / not implemented | Both out of scope for Local-1 and remain independent later gates |

## Frozen local layout and identity

`DOCUMENT_BLOB_ROOT` is an absolute, pre-provisioned persistent directory outside the Git
repository. The adapter owns two children on the same filesystem:

```text
<root>/
  objects/    # committed immutable candidate bytes, deterministic object-key hierarchy
  staging/    # exact temporary candidates only; never authoritative or included as committed data
```

Object keys remain server-owned opaque relative POSIX keys. Reject empty components, `.`, `..`,
absolute paths, backslashes, NUL/control characters, drive/UNC shapes and symlink traversal. All
directory traversal and final opens use Linux directory file descriptors plus `O_NOFOLLOW`; string
`resolve()` checks alone are not sufficient against a concurrent symlink swap.

The root must already exist, be a real directory rather than a symlink, be readable/writable by the
VALORA service account, not be group- or world-writable and not be inside a Git worktree. Startup
probes the required same-filesystem hard-link primitive and fails closed on `EXDEV`, unsupported
link semantics or unsafe permissions. There is no fallback to overwrite-capable rename behavior.

## Atomic create-only publication

1. Validate the key and open/create its committed parent hierarchy beneath the `objects` dirfd with
   no symlink following.
2. Create one `0600` staging file beneath `staging` using exclusive creation.
3. Stream chunks once while computing SHA-256 and byte length; reject non-bytes, overflow or final
   mismatch.
4. Flush and `fsync` the staging file; change committed file mode to application-immutable `0400`.
5. Publish with one same-filesystem `linkat`/`os.link` operation from the staging dirfd to the final
   parent dirfd. Hard-link creation is atomic and fails with `EEXIST`; it never replaces a target.
6. On success, `fsync` the containing committed directory, unlink the staging name and `fsync` the
   staging directory.
7. On `EEXIST`, stream the existing no-follow regular file. Exact SHA-256 plus exact length returns
   compatible `ALREADY_EXISTS`; any mismatch or unsafe identity returns `REJECTED` without overwrite.

A process crash may leave an exact staging orphan or a committed object whose DB state has not yet
advanced. Recovery observes/verifies the same final key through the existing state machine. The
adapter exposes a read-only inventory of exact regular staging tokens and cleanup accepts only one
such validated token. It does not recursively delete, follow symlinks or target committed objects.
No request path automatically sweeps staging: an operator or scheduled pilot task must inventory and
clean exact tokens only while writers are quiescent or after an age/ownership policy is established.

## Read and cleanup contract

`observe` and `verify_checksum` open the exact committed path through dirfds, require a no-follow
regular file, stream the complete content and return fail-closed statuses on unsafe/unreadable state.
Checksum verification never trusts path, inode metadata, mtime or filename.

`delete_uncommitted_or_expire` remains guarded first by the application service's binding/state/legal
hold checks. The adapter then re-verifies the exact checksum, confirms the opened inode still matches
the directory entry and unlinks only that entry beneath `objects`. Ordinary cleanup has no path to a
bound/finalized revision and never performs recursive deletion.

## Persistence and configuration

- Add one forward Alembic migration changing only the two existing `provider_kind` check constraints
  from `('fake')` to `('fake', 'local')`; downgrade restores the previous constraint and must fail if
  local rows still exist rather than silently discarding data.
- `record_storage_candidate` receives an explicit closed provider kind; it does not infer the domain
  provider from filenames or user input.
- Add `DOCUMENT_BLOB_PROVIDER=local` and
  `DOCUMENT_BLOB_ROOT=/var/lib/valora/document-blobs` to the VPS/Docker shape with a persistent
  volume. No runtime default may point inside the repository.
- Before any provider I/O or cleanup, the application compares the selected adapter's immutable
  `provider_kind` with the persisted candidate and fails closed on mismatch.
- `fake` remains available for development/tests only. Production/pilot startup with `local` validates
  the root and required filesystem capability before serving requests.

## Test matrix

| ID | Required proof |
|---|---|
| L1 | Normal staged write, fsync and atomic create-only publication |
| L2 | Duplicate key with same SHA-256/length reconciles idempotently |
| L3 | Duplicate key with different SHA-256 or length fails closed |
| L4 | Concurrent OS-thread same-object create yields one final inode/content |
| L5 | Crash/interruption during staging write leaves no committed partial object |
| L6 | Crash after staging fsync before publish leaves recoverable exact staging orphan only |
| L7 | Collision at atomic publish observes/verifies instead of overwriting |
| L8 | Committed file SHA-256 corruption is detected by a full read |
| L9 | Committed file byte-length mismatch is detected by a full read |
| L10 | Exact staging orphan cleanup stays inside `staging` |
| L11 | Path traversal, absolute/backslash/control input is rejected |
| L12 | Symlink escape and concurrent symlink substitution are rejected |
| L13 | Injected denial plus non-root kernel DAC/read-only proof fails closed |
| L14 | Concurrent OS-thread different-content writers never overwrite the winner |
| L15 | Restart/recovery returns compatible existing bytes without a second object |
| L16 | Cleanup cannot escape root or follow a symlink |
| L17 | Injected disk-full/write/fsync failure creates no committed partial object where practical |

T1-T14 must keep their existing semantics and pass without edits made merely to accommodate the
local provider. PostgreSQL T8/T9/T14 plus migration upgrade/downgrade/upgrade remain mandatory.
Linux filesystem proofs run on a real Linux filesystem; a Windows skip is not a PASS.

## G5 evidence — 2026-09-20

The Linux Docker proof used the repository's Python 3.12 backend with a throwaway PostgreSQL 16
container. No AWS/OneDrive credential, endpoint or provider operation was used.

- focused local/S3/service/PostgreSQL suite: `68 passed`, `1 skipped` under root; the sole skip is
  the explicitly non-root kernel-DAC half of L13;
- exact L13 kernel-DAC/read-only proof: `1 passed` in a separate container running as UID 65532;
- all L1-L17 tests passed on the container's Linux filesystem, including a subprocess hard crash
  after staging fsync and before publish;
- T1-T14 remained unchanged and passed, including PostgreSQL T8/T9/T14;
- Alembic upgrade/downgrade/upgrade passed and the restored provider constraint admits `local`;
- full backend run with Node and PostgreSQL available: `1597 passed`, `10 skipped`;
- full backend Ruff passed and `docker compose config --quiet` passed.

The full run covers all `1597` executed backend tests, including the downgrade-refusal proof; the
separate non-root run covers the root-only L13 skip. Existing Pydantic/SQLAlchemy
deprecation warnings remain unrelated debt. This record does not claim a deploy, HA, WORM, live
provider validation or hardware-enforced immutability.

## Gates

1. **G1 — plan/contract: COMPLETE.** Authority, AWS deferral and two OneDrive roles synchronized.
2. **G2/G4 — adapter/config/migration: COMPLETE.** No Exchange or Backup tooling was added.
3. **G5 — verification: PASS.** T1-T14, L1-L17, PostgreSQL CAS/migration and static gates passed.
4. **G6 — acceptance: REVIEW CANDIDATE.** Freeze an exact manifest and obtain two independent
   read-only reviews before accepting Local-1; this file records the frozen candidate state, while
   reviewer verdicts are external gate evidence.

`VALORA-BACKUP-ONEDRIVE-001` remains unopened for implementation until G4/Local-1 passes. A failure
to prove atomic no-replace publication is a stop condition, not a reason to weaken the contract.

## Stop conditions

- Any need to change `DocumentRevision` authority or weaken CurrentHead CAS.
- Hard-link publication is unsupported, cross-filesystem or not demonstrably no-replace.
- A path/symlink race can escape the configured root.
- T1-T14 regresses or PostgreSQL migration/CAS cannot be proved.
- The migration needs data rewriting or broader schema changes than the provider-kind constraints.
- Implementation requires AWS, OneDrive credentials, a live provider, real customer data or a
  production deploy.

## Planned implementation ownership

Codex retains authority interpretation, filesystem-concurrency design, migration semantics, diff
inspection and final gates. The configured mechanical worker may implement only the exact adapter,
tests and locked configuration/migration edits named in its task packet. It may not commit, push,
change PR state, use credentials, reinterpret ADR 0043 or begin backup work.

## References

- [ADR 0043](../adr/0043-app-owned-immutable-document-storage.md)
- [Document Blob Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Current deployment decision](../research/valora-storage-provider-selection-2.md)
- [Deferred AWS spike](valora-storage-s3-spike-001.md)
