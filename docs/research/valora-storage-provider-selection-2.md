# VALORA pilot storage and OneDrive role selection

**Start time:** 2026-09-20, Asia/Saigon
**Task:** `VALORA-STORAGE-LOCAL-001`; later `VALORA-ONEDRIVE-EXCHANGE-001` and
`VALORA-BACKUP-ONEDRIVE-001`

## Initial purpose

Record the Product Owner's current deployment-path decision after the provider-neutral fake and AWS
S3 G1-G4 static preparation completed. The decision must preserve ADR 0043's authority and integrity
invariants while selecting the smallest operational shape for development, test, pilot and a small
single-user deployment.

Constraints at the decision point:

- do not run AWS G5 or create/use any AWS resource or credential;
- keep the AWS adapter and all G1-G4 evidence as a future provider reference;
- keep PostgreSQL and `DocumentRevisionCurrentHead` authoritative;
- make local authoritative blob availability independent of OneDrive OAuth/network health;
- keep OneDrive Personal non-authoritative in both Exchange and encrypted Backup roles;
- keep `VALORA/Exchange/{Inbox,Working,Exports}` separate from
  `VALORA/Backup/<deployment-id>`;
- do not claim HA, WORM, PITR, `RPO <= 15 minutes` or `RTO <= 4 hours` without measured evidence.

## Strategy

1. Separate the authoritative runtime path from both OneDrive roles.
2. Reuse the accepted four-operation `DocumentBlobStore` port and durable DB execution model.
3. Prove Linux local-filesystem create-only publication before accepting any Exchange import as
   authoritative.
4. Keep Backup transport outside document mutation, CurrentHead, normal read and write paths.
5. Require explicit Inbox initial import and explicit human-confirmed Working revision promotion. Word/Excel Save, provider notification, revalidation and Export never create a revision or update CurrentHead; Working observation/revalidation may run automatically under ADR 0045.
6. Retain cloud-provider adapters and evidence without treating unrun live gates as conformance.

## Checklist

- [x] Preserve ADR 0043 D1-D10 and the T1-T14 contract.
- [x] Close/defer AWS before G5 without a live-provider conclusion.
- [x] Select app-owned local immutable blobs for the current pilot deployment path.
- [x] Select OneDrive Personal Exchange as a mutable, non-authoritative interoperability surface.
- [x] Select a separate OneDrive Personal namespace as encrypted off-site backup transport.
- [x] Require separate acceptance gates for Local storage, Exchange and Backup.
- [x] Implement and prove G5 for `VALORA-STORAGE-LOCAL-001`.
- [x] Independently accept Local-1 at G6.
- [x] Implement and close `VALORA-ONEDRIVE-EXCHANGE-001` G8 offline after Local-1.
- [ ] Implement and restore-test `VALORA-BACKUP-ONEDRIVE-001` offline.
- [ ] Perform separately authorized interactive OneDrive Exchange/Backup live evidence.

## Result

The approved current-phase topology is:

```text
Vietnix CHEAP 2 VPS
  -> VALORA backend/API
  -> PostgreSQL authority
  -> app-owned local immutable DocumentRevision blobs

OneDrive Personal (non-authoritative Exchange)
  -> VALORA/Exchange/Inbox      # explicit import source
  -> VALORA/Exchange/Working    # mutable Word/Excel copy; auto observation allowed, human-confirmed promotion required
  -> VALORA/Exchange/Exports    # mutable user-facing copies; no revision mutation

Separate backup process
  -> bounded local backup staging
  -> restic encryption
  -> rclone transport
  -> VALORA/Backup/<deployment-id>
```

OneDrive Personal is not an authoritative document store, a CurrentHead authority or a required
runtime dependency. Exchange files can be renamed, moved, edited or deleted without changing
authority. Word/Excel Save changes only the mutable OneDrive file. VALORA may automatically observe/revalidate it, but a new revision requires ADR-0045 review plus an explicit human-confirmed revision command that captures exact accepted bytes locally and wins CurrentHead CAS. Backup
authentication, quota, throttling, network or upload failure may fail a backup run, but must not fail
a VALORA business transaction or prevent verified local blob reads.

The local provider is accepted as a deployment target only after it proves atomic no-replace
publication, full SHA-256 and length verification, symlink/path containment, bounded cleanup,
restart reconciliation and the unchanged T1-T14/CurrentHead CAS behavior. Application/filesystem
immutability is not hardware WORM or compliance retention; a VPS root administrator can mutate the
disk.

The single VPS remains one failure domain for backend, PostgreSQL and authoritative local blobs.
Encrypted OneDrive Backup improves off-site recoverability but provides neither HA nor synchronous
replication. Exchange folders do not count as backup. The accepted long-term recovery objectives
remain targets, not achieved measurements.

### Verification

This record is a Product Owner architecture decision, not runtime evidence. At the decision point,
the repository contains the accepted fake, durable execution/CAS model, AWS adapter and G1-G4 static
evidence. The local adapter passed Linux G5 and independent G6 acceptance on the exact reviewed snapshot.
OneDrive read/adopt/bind/revalidation plus G8 offline Exchange now exist on the active Draft PR #32. G8 proves the offline Inbox/Working/Exports Exchange lifecycle and app-owned revision storage machinery. Working Change Observation / Change Candidate runtime remains unimplemented and separately gated by ADR 0045; Backup/restore remains unopened.

### Corroborating links

- [ADR 0043](../adr/0043-app-owned-immutable-document-storage.md)
- [Document Blob Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Deferred AWS spike](../plan/valora-storage-s3-spike-001.md)
- [Local provider plan](../plan/valora-storage-local-001.md)
- [Superseded provider-spike selection](valora-storage-provider-selection.md)

## Decision

**Action:** use app-owned local immutable blob storage for the current VPS pilot path, gated by
`VALORA-STORAGE-LOCAL-001`. After Local-1, separately gate OneDrive Exchange under
`VALORA-ONEDRIVE-EXCHANGE-001` and encrypted PostgreSQL/blob Backup under
`VALORA-BACKUP-ONEDRIVE-001`. Neither task is part of Local-1 and neither authorizes live OAuth.

AWS remains an available future adapter/reference. G5 was not run, no live AWS conformance claim was
established, and AWS is not selected as the current production provider. This decision does not
reject AWS or declare it incompatible.

**Cross-references:** ADR 0043, the storage contract, the PR-07 acceptance matrix and documentation
index are synchronized to this current decision.
