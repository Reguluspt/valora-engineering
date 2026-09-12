# VALORA UI/UX v2.3 — PR-06 M365 Return/Revalidation Implementation Contract

**Task:** `VALORA-PR06-IMPL-001` **Status:** ACCEPTED — PRODUCT OWNER AUTHORIZED IMPLEMENTATION **Date:** 2026-09-12 **Authority:** PR-06 task brief, accepted ADR 0041, accepted ADR 0040, and the UI/UX v2.3 M365 Return/Revalidation semantic and visual addenda

## Scope

Add the OneDrive Personal read-only runtime needed to create or seal trustworthy canonical lineage, explicitly revalidate the current bound DOCX, append the result, and expose computed document freshness/readiness. The authorized producer adopts an existing provider file and writes VALORA lineage only. This contract does not authorize Graph writes, sync writes, conflict resolution, publishing, OneDrive for Business, or SharePoint.

## Domain vocabulary

- **Binding:** the immutable PR-05 association between one VALORA Document Revision and one stable OneDrive drive/item identity plus bind-time Graph metadata.
- **Sealed content baseline:** immutable exact-DOCX and versioned Managed Region fingerprints whose equality to the bound Document Revision was proven.
- **Eligible binding:** the current revision's binding with a matching sealed baseline and active usable OneDrive Personal connection.
- **Observation:** one append-only provider-backed revalidation attempt tied to exact current revision, binding, baseline, trigger, actor, and idempotency lineage.
- **Fresh:** the latest applicable completed observation satisfies the accepted freshness policy and does not contain a blocking integrity result.
- **Applicable:** the observation's organization/project/document/current-revision/binding/baseline lineage still exactly matches current authoritative state.

Eligibility, `BACKGROUND_REFRESH`, and stale-by-policy are technical/readiness states. They are not additional semantic classifications.

## Persistence contract

### `M365ManagedContentBaseline`

One immutable row per `M365RevisionBinding`:

- tenant lineage: `organization_id`, `project_id`, `document_id`, `document_revision_id`;
- integration lineage: `binding_id`, `connection_id`, `drive_id`, `drive_item_id`;
- source proof: `source_content_sha256`, `source_size_bytes`, bind metadata digest, provenance kind;
- contracts: `parser_contract_version`, `fingerprint_contract_version`, `managed_region_manifest_digest_sha256`;
- document comparison: `outside_managed_digest_sha256`, `whole_canonical_digest_sha256`;
- idempotency: organization-scoped key and server-derived request digest;
- actor/time: creator and immutable creation timestamp.

Tenant-safe composite foreign keys must prevent cross-organization/project/document/revision/binding references. The binding is unique. All SHA-256 values are lowercase 64-character hex with database checks. Baselines are never updated or deleted by product commands.

### `M365ManagedRegionBaseline`

Ordered immutable children of the content baseline:

- tenant and parent baseline lineage;
- stable `region_key`, ordered position, and exact server-owned locator needed to resolve the region again;
- locator-contract digest and semantic type;
- normalized-value digest and structural digest;
- normalization contract version.

`baseline + region_key` is unique. Raw Word text and raw business values are not persisted.

### `M365RevalidationObservation`

One immutable terminal attempt:

- tenant/document/revision/binding/baseline/connection lineage;
- trigger enum: `EXPLICIT_REFRESH | FRESHNESS_REQUIRED_ACTION | RECONNECT` for PR-06-callable service semantics;
- canonical classification enum: `NO_CHANGE | EXTERNAL_CHANGE_OUTSIDE_MANAGED | EXTERNAL_CHANGE_IN_MANAGED | FILE_REPLACED_OR_MOVED | ACCESS_UNAVAILABLE`;
- start/completion timestamps and provider-observed modified time;
- observed drive/item/version ID, `eTag`, `cTag`, size, display name/path/URL where safe;
- observed whole/outside digest and parser/fingerprint contract versions when content was verified;
- ordered affected stable region keys and their before/after digests in protected structured persistence, without raw values;
- sanitized reason category and retryability flag;
- organization-scoped idempotency key, server request digest, actor, and correlation ID.

The schema must not imply that every observation has content digests: identity/access failures may terminate before content exists. Database checks enforce required/forbidden field groups by classification where practical; service tests cover the remaining cross-field invariants.

Observation rows are append-only. Currentness is derived by exact lineage plus completion order; no mutable “latest observation” pointer is required in PR-06.

## Baseline sealing contract

The service accepts an authoritative immutable Managed Region definition set. It does not derive ownership from arbitrary DOCX controls.

The concrete server-authority envelope is an organization-scoped active `DocumentTemplate`, an active `TemplateVersion`, and a project-scoped DOCX `GeneratedDocument` of the same document type. The Template Version's server-owned `placeholder_manifest` must declare `managed_regions_contract: valora-managed-regions-v1` and a non-empty strict list whose entries contain exactly `region_key`, `locator`, `semantic_type`, and `normalization_contract`. Generated-document lineage is accepted only when `GeneratedDocument.data_snapshot_hash` equals `DocumentRevision.data_snapshot_digest_sha256`. `GeneratedDocument.checksum_sha256` is not a DOCX-byte proof because the current producer writes the snapshot hash there; exact downloaded DOCX bytes must separately equal `DocumentRevision.content_checksum_sha256`. The request may carry only the generated-document ID, never client-authored region facts.

### New binding path

1. Resolve actor, tenant, project, current Document Revision, connection, and requested stable file identity.
2. Freeze expected current-head and input digests.
3. Acquire the delegated token and read exact Graph metadata and DOCX content without a database lock.
4. Enforce DOCX package safety and compute exact/canonical/region fingerprints.
5. Require exact DOCX SHA-256 equality with `DocumentRevision.content_checksum_sha256`.
6. In one short transaction, recheck all frozen authority, insert immutable binding and baseline/regions, append sanitized audit, and commit.

### Existing PR-05 binding enrollment

The same flow is owned by the proof-based enrollment command in `revalidation_service.py`. It additionally requires current `eTag` equality with the immutable bind-time observation; when both bind-time and current `cTag` exist, they must also agree. `graph_version_id` is not required because the PR-05 item adapter does not obtain an inline version ID. A mismatch returns `REVALIDATION_BASELINE_REQUIRED`; it does not seal current bytes as historical `Old`, mutate the binding, or create a Document Revision.

Enrollment uses mutation authorization and explicit idempotency. Same-key/same-digest replay returns the original baseline; conflicting reuse returns `409`.

### Canonical first-lineage producer

`POST /api/v1/m365/onedrive/projects/{project_id}/documents/provision` requires `project:update` and accepts exactly `template_version_id`, `connection_id`, `drive_item_id`, `title`, `data_snapshot`, and `idempotency_key`. Unknown fields are rejected. The snapshot is a bounded JSON object: at most 1 MiB canonical UTF-8, depth 32, and 10,000 nodes; non-finite or non-JSON values are rejected. Compact sorted-key JSON is the `v1` canonicalization used for its SHA-256.

Before OAuth/Graph work, the service resolves tenant permission, project, active DOCX Template Version and active organization-owned template, strict server manifest, actor-owned active personal connection, and idempotency replay. The request digest includes actor, tenant/project, template version, connection, stable item ID, normalized title, snapshot digest, and manifest digest.

Metadata size is rejected before content download when empty or above the 25 MiB DOCX boundary. The downloaded size must equal metadata size. A second metadata read must preserve drive/item identity, `eTag`, `cTag`, byte size, and modified time. Filename/path are never identity.

The short transaction locks organization/project authority and rechecks all frozen facts. It rejects an item already bound in the organization, then creates the D9 lineage and three sanitized audit facts atomically. One idempotency key and producer request digest are reused on revision, binding, and baseline. Exact replay performs no OAuth or Graph call. The external artifact record uses the actual DOCX byte checksum; raw snapshot/content/region values never enter API response or audit.

## Revalidation command contract

### Inputs

- authenticated actor and organization;
- project ID and document ID;
- expected current Document Revision ID or revision number;
- trigger;
- explicit idempotency key;
- correlation ID when supplied by the request boundary.

The client cannot submit provider metadata, classification, affected region keys, checksums, current values, or readiness facts.

### Pre-provider gate

Before token or Graph I/O, the service must:

- reload the active actor and active organization;
- require `project:read`;
- resolve the tenant-owned project/document and exact current head;
- resolve the exact immutable binding, active connection, and matching sealed baseline;
- reject unsupported account/drive/file type or absent baseline without provider access;
- freeze the lineage and server-derived request digest.

Foreign and missing project/document/binding identifiers use the established hidden-not-found response. Inactive or unauthorized actors fail before provider access.

### Provider and parser phase

Without holding a database row lock:

1. acquire an access token through the encrypted credential vault boundary;
2. retrieve the exact bound drive item by stable drive/item ID;
3. verify returned identity and capture metadata;
4. if the trustworthy current `eTag` equals the baseline `eTag`, classify `NO_CHANGE` without content download; compare `cTag` too when both values exist, but do not require a non-null `cTag`;
5. otherwise download the exact item stream immediately, bounded by size/time limits;
6. verify the stream against the metadata observed for the attempt or detect a metadata/content race;
7. parse the DOCX under the baseline's parser contract and compute the same canonical fingerprints;
8. classify by the matrix below.

A metadata/content race retries only within a bounded policy. Exhaustion becomes retryable `ACCESS_UNAVAILABLE`; it never stores a classification from mismatched metadata and bytes.

### Classification matrix

| Provider/content fact | Terminal classification | Required behavior |
| --- | --- | --- |
| trustworthy unchanged `eTag` gate, or all canonical digests equal | `NO_CHANGE` | preserve current revision/binding; freshness may be satisfied |
| managed digests/structure equal; outside digest differs | `EXTERNAL_CHANGE_OUTSIDE_MANAGED` | record outside edit; do not call it conflict |
| any managed normalized/structural digest differs | `EXTERNAL_CHANGE_IN_MANAGED` | record affected region keys; block unsafe overwrite until later review/sync policy |
| exact bound identity or lineage cannot be trusted | `FILE_REPLACED_OR_MOVED` | require verification/recovery; never bind by name/path |
| auth/network/throttle/provider/download/parser/integrity failure prevents verification | `ACCESS_UNAVAILABLE` | preserve last usable fact as stale context; expose retry/reconnect category; no fake success |

Rename or path drift with unchanged drive/item identity is metadata drift, not replacement. A changed/absent tag alone selects neither external-change class.

### Commit phase

Open a short transaction after all external and parser work. Recheck:

- active actor/organization and `project:read`;
- tenant-owned project/document;
- expected current Document Revision/head;
- exact binding, connection, and sealed baseline lineage;
- idempotency key and request digest.

Append the immutable observation and sanitized `M365_REVALIDATION_COMPLETED` AuditEvent atomically. If current lineage changed, roll back and return a version conflict; the stale attempt cannot become an applicable observation. If persistence fails, neither observation nor success audit may remain.

## Read aggregate contract

The tenant-safe document revalidation aggregate returns:

- document, current revision, binding, and display-safe OneDrive file identity;
- baseline eligibility and a stable recovery code when ineligible;
- current presentation state (`BACKGROUND_REFRESH` only while a request is active at the API/UI orchestration boundary);
- latest applicable completed classification and completion time;
- affected stable region keys without raw values;
- computed `is_fresh`, `is_safe_for_freshness_required_action`, `stale_reason`, `blocking_reason`, `next_action`, and retry/reconnect capability.

The aggregate never promotes an observation from an old revision/binding/baseline. `ACCESS_UNAVAILABLE` preserves last-known usable information only as explicitly stale context. The frontend does not recompute classification, freshness, conflict, or publishing truth.

PR-06 exposes:

- `POST /api/v1/m365/onedrive/projects/{project_id}/documents/provision` with `project:update`, strict producer input, and server-derived provider/baseline facts;
- `POST /api/v1/m365/onedrive/projects/{project_id}/documents/{document_id}/revalidation/baseline` with `project:update`, strict expected-lineage input, and no raw baseline facts from the client;
- `GET /api/v1/m365/onedrive/projects/{project_id}/documents/{document_id}/revalidation` with `project:read`;
- `POST /api/v1/m365/onedrive/projects/{project_id}/documents/{document_id}/revalidation` with `project:read`, strict body, expected revision, trigger, and idempotency key.

Permission, strict-input, tenant-hiding, and server-authority semantics may not change without contract review.

## Freshness/readiness contract

PR-06 computes readiness on read. It does not create a mutable case-state or publishing record.

- no eligible baseline → not fresh; freshness-required action blocked with baseline recovery;
- no applicable observation → not fresh; explicit check required;
- stale by accepted policy → not fresh; revalidation required;
- `NO_CHANGE` → fresh and revalidation-safe;
- `EXTERNAL_CHANGE_OUTSIDE_MANAGED` → fresh for change detection and not a conflict by default; later sync must preserve outside narrative;
- `EXTERNAL_CHANGE_IN_MANAGED` → verified change exists but unsafe to overwrite until PR-07 review/comparison;
- `FILE_REPLACED_OR_MOVED` → blocking integration recovery;
- `ACCESS_UNAVAILABLE` → unverified; freshness-required action blocked, with stale last-known data retained if available.

This readiness is an integration input. It does not itself increase workflow completion or claim release readiness.

## DOCX safety and canonicalization contract

- accept only bounded ZIP-based DOCX content with validated media type/signature;
- reject absolute paths, parent traversal, encrypted entries, duplicate conflicting entries, dangerous external relationships, oversize entries, excessive entry count, and decompression-ratio abuse;
- use hardened XML parsing with DTD/entity/network expansion disabled;
- parse only the parts required by the accepted region locator and outside-content contract;
- require each baseline region key exactly once unless its authority explicitly permits a versioned repeating-region form;
- make whitespace, number/date, relationship, run-boundary, and field-code normalization explicit per contract version;
- compare semantic values using region-specific normalization; raw string equality is not universal;
- deterministic input under one parser/fingerprint contract must produce deterministic ordered digests;
- parser/fingerprint contract mismatch fails unavailable until an explicit baseline migration/reseal strategy is accepted.

## Audit and privacy contract

Success/failure audit includes stable tenant/document/binding/observation IDs, trigger, canonical classification, affected region keys, contract versions, reason category, retryability, and correlation ID.

Audit, logs, API, and persistence must exclude:

- access/refresh tokens, token cache, client secrets, authorization codes, OAuth state, and PKCE material;
- short-lived/preauthenticated download URLs;
- raw DOCX bytes, unrestricted extracted text, and raw Managed Region values;
- provider response bodies, stack traces, and unsanitized exception text;
- account/profile data beyond already accepted non-secret connection identity.

## Idempotency and concurrency contract

- idempotency is organization-scoped and request digests include actor, project, document, expected revision, binding, baseline, and trigger;
- same key plus same digest returns the original terminal observation without a second provider call when the persisted result is already available;
- same key plus different digest returns `409 idempotency_key_reused`;
- equivalent concurrent requests with one key persist one observation and one completion audit;
- a current-head, binding, baseline, connection, or permission change between provider read and commit rejects stale commit;
- lock order follows project → document current head → binding/baseline → idempotency/observation as applicable and never spans Graph/content I/O.

## Explicitly forbidden behavior

- classifying changed metadata directly as inside- or outside-managed change;
- returning `NO_CHANGE` after access, download, parser, checksum, or contract failure;
- sealing current content as historical baseline without D2 proof from ADR 0041;
- adding a sixth business classification to hide incomplete processing;
- persisting mutable “latest” truth that can drift from current revision lineage;
- creating/mutating a Document Revision or overwriting an immutable binding during enrollment or revalidation; only the D9 producer may create revision `#1` together with its first immutable binding;
- treating outside-managed edits as a conflict by default;
- overwriting user edits, auto-resolving a conflict, or writing any OneDrive content;
- using filename/path as identity or auto-binding a replacement;
- exposing sensitive/raw document or credential material;
- widening account/provider scope beyond OneDrive Personal delegated `Files.Read`.

## Acceptance gate

Implementation passes only when all task-brief verification is green with zero relevant skips, PostgreSQL proves migration/concurrency behavior, an independent review has no unresolved P0/P1 findings, a real eligible OneDrive Personal document completes a read-only live classification where safe, and the final audit records exact commands and residual limitations.

The Product Owner accepted ADR 0041 and this contract on 2026-09-12, then authorized the D9 canonical producer extension for real lineage and live classification. Runtime implementation is authorized within the amended task-brief allowlist. Commit, push, publication, deployment, and release remain separately gated.
