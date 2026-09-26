# ADR 0041 — OneDrive Personal return/revalidation observations and sealed content baselines

**Status:** ACCEPTED FOUNDATION — CURRENT DOCUMENT-CHANGE SEMANTICS EXTENDED BY ADR 0045 **Date:** 2026-09-12 **Task:** `VALORA-PR06-IMPL-001`

## 2026-09-21 authority note

PR-06 return/revalidation remains valid read/integrity foundation. ADR 0045 extends it with automatic Working-change observation, non-authoritative `DocumentChangeCandidate`, and explicit human-confirmed Revision promotion. Revalidation/RenderJob completion alone must not be interpreted as a generic automatic Revision-creation rule outside an explicitly authorized command boundary.

## Context

PR-05 established delegated OneDrive Personal access, a stable `connection_id + drive_id + drive_item_id` identity, an immutable `M365RevisionBinding`, and a separate canonical VALORA Document Revision. The accepted UI/UX v2.3 Return/Revalidation authority now requires VALORA to re-read the bound file after an external Word handoff, classify the result, and prevent freshness-dependent actions from proceeding on unverifiable state.

The five canonical semantic results are:

`NO_CHANGE | EXTERNAL_CHANGE_OUTSIDE_MANAGED | EXTERNAL_CHANGE_IN_MANAGED | FILE_REPLACED_OR_MOVED | ACCESS_UNAVAILABLE`.

The existing binding stores Graph metadata (`graph_version_id` when available, `eTag`, `cTag`, modified time, size, name, path, and `webUrl`) but does not store the bound DOCX bytes, a Managed Region manifest, or region fingerprints. Metadata alone can establish that a file probably changed, but it cannot truthfully distinguish an edit inside a Managed Region from an edit outside all Managed Regions. A timeout or authorization failure also cannot be treated as evidence of no change.

The current canonical `DocumentRevision.content_checksum_sha256` is useful only when the producer can prove that it is the SHA-256 of the exact DOCX byte stream bound to OneDrive. It is not, by itself, a Managed Region baseline. Existing PR-05 bindings therefore cannot be backfilled by downloading today's file and pretending that the result was the historical bind-time content.

## Proposed decision

### D1. Revalidation requires an immutable sealed content baseline

An `M365ManagedContentBaseline` is attached one-to-one to an immutable `M365RevisionBinding`. It records:

- organization, project, document, Document Revision, binding, connection, drive, and drive-item lineage;
- exact source DOCX checksum and byte size;
- parser/fingerprint contract version;
- immutable Managed Region manifest digest;
- one ordered region snapshot per managed region, including stable region key, exact server-owned locator, locator-contract digest, semantic type, normalization contract, normalized-value digest, and structural digest;
- a canonical outside-managed-content digest that excludes managed payloads while retaining relevant document structure and narrative;
- creation actor/time and provenance showing how equality with the bound Document Revision was proven.

The baseline and its region snapshots are append-only. Revalidation observations never mutate them. Raw access tokens, short-lived download URLs, unrestricted document text, and raw Managed Region values are not stored in the baseline or audit payload.

A document is eligible for canonical revalidation only when this baseline exists and its lineage matches the current Document Revision and immutable binding. Missing eligibility is a precondition failure (`REVALIDATION_BASELINE_REQUIRED`), not a sixth semantic result and not `ACCESS_UNAVAILABLE`.

### D2. Baseline sealing is fail-closed

For a new supported binding, VALORA downloads the exact DOCX bytes during the bind operation, verifies the file type and bounded package safety, computes the exact checksum, resolves an already-authoritative Managed Region definition set, and creates the binding plus sealed baseline atomically after all external reads finish.

For an existing PR-05 binding, a one-time baseline-seal command is allowed only when all of these facts are proven in one attempt:

1. the stable drive/item identity still equals the immutable binding;
2. the current `eTag` equals the bind-time `eTag`; when both bind-time and current `cTag` exist, they must also agree;
3. the downloaded byte stream SHA-256 equals `DocumentRevision.content_checksum_sha256`;
4. an authoritative, versioned Managed Region definition set exists and all required regions resolve uniquely;
5. the DOCX package passes size, compression-ratio, relationship, XML, and parser safety limits.

If any proof is missing, VALORA does not create a baseline and does not infer historical content from the current file. Recovery requires the separately authorized canonical producer flow in D9; the legacy enrollment and revalidation commands never create that revision automatically.

PR-06 does not invent a content-control tag convention or infer ownership from arbitrary Word controls. Region locators and normalization rules must come from an accepted Template Version/Managed Region authority. Documents without that authority remain ineligible.

For this implementation, that accepted authority is an organization-scoped active `DocumentTemplate` and active `TemplateVersion`. The version's server-owned `placeholder_manifest` must declare the exact `valora-managed-regions-v1` contract and a non-empty, strictly shaped list of region key, locator, semantic type, and normalization contract. A project-scoped DOCX `GeneratedDocument` proves template lineage only when its `data_snapshot_hash` equals `DocumentRevision.data_snapshot_digest_sha256`; its legacy `checksum_sha256` is not used as a DOCX-byte proof because the current producer stores the data-snapshot hash there. Exact DOCX-byte equality remains independently required against `DocumentRevision.content_checksum_sha256` under item download proof 3 above. Clients may identify the generated document but cannot submit or override region definitions.

### D3. Metadata is a gate; content comparison is the classifier

The revalidation pipeline has two layers:

1. Graph identity and metadata gate: retrieve the exact bound item by drive/item ID, verify the connection and drive, and capture current version/tag/time/size/name/path/URL metadata. Path and filename remain display metadata rather than identity.
2. Bounded DOCX comparison: when metadata does not conclusively establish `NO_CHANGE`, download the exact current item bytes, parse them under the baseline's contract version, resolve the same Managed Region manifest, and compare canonical fingerprints.

For the exact same drive/item identity, an unchanged current `eTag` is independently sufficient to short-circuit content download to `NO_CHANGE` because Graph defines it over the entire item. When a `cTag` is present, it is retained as the content-specific corroborating signal; its absence does not disable the `eTag` short circuit. A changed or absent `eTag` never proves where content changed. It requires content comparison unless the identity/access gate already produces another terminal result.

The current PR-05 item adapter has no inline Graph version ID. PR-06 may issue the separate version-list query and record the newest version ID when available, but baseline enrollment and classification must remain correct when it is absent. Version retention is not assumed, and version IDs are never required or the sole source of truth. Short-lived download URLs are consumed immediately and never persisted.

### D4. Exactly five terminal semantic classifications

Once the preconditions in D1 and D2 are satisfied, every completed revalidation attempt produces exactly one terminal semantic classification:

- `NO_CHANGE`: the bound identity is trustworthy and the current canonical whole-document comparison equals the sealed baseline, or a trustworthy unchanged `eTag` permits the D3 short circuit.
- `EXTERNAL_CHANGE_OUTSIDE_MANAGED`: all managed-region normalized and structural digests equal the baseline, while the canonical outside-managed digest differs.
- `EXTERNAL_CHANGE_IN_MANAGED`: one or more managed-region normalized or structural digests differ. The observation records only affected stable region keys and digests, not unrestricted content.
- `FILE_REPLACED_OR_MOVED`: the exact bound identity or baseline lineage is no longer trustworthy, including a provider response that resolves a different drive/item identity or an unsupported relocation that breaks the binding. Rename or path change with the same stable drive/item identity is recorded as metadata drift and is not automatically this result.
- `ACCESS_UNAVAILABLE`: the eligible binding cannot be read or verified because authorization, session, network, throttling, provider, or transient download failure prevents a trustworthy observation.

Parser rejection, missing required Managed Regions, duplicate region keys, unsupported DOCX structure, or unsafe package content is an integrity failure after access succeeds. It is persisted as `ACCESS_UNAVAILABLE` with a sanitized technical reason category because VALORA cannot verify the semantic state. It must never become `NO_CHANGE`.

No technical processing state is added to the business enum. In-flight work is represented separately as `BACKGROUND_REFRESH`; an attempt that has not completed has no terminal semantic classification yet.

### D5. Revalidation facts are append-only observations; readiness is computed

Each attempt appends one `M365RevalidationObservation` with tenant/document/binding lineage, trigger, start/completion times, baseline fingerprint contract, observed Graph metadata, observed package/region digests when available, affected region keys, terminal classification, sanitized reason category, idempotency key, request digest, actor, and correlation ID.

The latest applicable observation is selected by current Document Revision and binding lineage, never merely by timestamp across revisions. Document sync/readiness is computed on read from the current head, eligible baseline, latest applicable completed observation, and freshness policy. PR-06 does not introduce a mutable readiness source of truth.

`ACCESS_UNAVAILABLE`, a missing eligible baseline, a stale observation, `FILE_REPLACED_OR_MOVED`, or `EXTERNAL_CHANGE_IN_MANAGED` cannot support a fresh/safe-to-overwrite claim. `EXTERNAL_CHANGE_OUTSIDE_MANAGED` is not a conflict by default. Three-way conflict remains a PR-07 concern and is derived only when the VALORA-side value for an affected region also changed from `Old` and differs semantically from current Word value `W`.

### D6. Authorization, idempotency, and transaction boundary

Reading the current observation and readiness requires `project:read`. Explicitly requesting a provider-backed revalidation also uses `project:read` because it is a read-only integrity check; connection creation, baseline creation, binding replacement, sync, and any document mutation remain protected by their mutation permissions.

Before any provider call, the service resolves the active actor, organization, project, document, current revision, connection, binding, and sealed baseline without disclosing foreign identifiers. It freezes the expected lineage and request digest, then performs token acquisition, Graph metadata/content reads, and DOCX parsing outside a database lock.

The commit phase opens a short transaction and rechecks actor permission, tenant lineage, current document head, binding, baseline, and idempotency. If lineage changed, the attempt fails with a version conflict and cannot become the latest applicable fact. The observation and sanitized `M365_REVALIDATION_COMPLETED` AuditEvent commit atomically. Same-key/same-digest replay returns the original observation; conflicting key reuse fails closed. Concurrent equivalent attempts may store only one idempotent fact for the same command key.

### D7. PR-06 trigger and API boundary

PR-06 implements an explicit `Kiểm tra thay đổi` command and a read aggregate that exposes current revalidation/readiness facts. It also provides the same application service for later freshness-required actions. Browser focus-return orchestration, reconnect automation, webhook/change notifications, polling, and freshness TTL scheduling are deferred until their owning UI or integration slice.

The API does not return raw document bytes, raw region values, tokens, provider exception text, or short-lived download URLs. It returns stable IDs, timestamps, canonical classification, affected region keys, freshness/readiness facts, sanitized recovery code, and display-safe current file metadata.

### D8. OneDrive Personal remains the only provider scope

PR-06 continues using the PR-05 consumer delegated connection and `Files.Read`. It adds no write scope. OneDrive for Business, SharePoint sites/document libraries, application permissions, tenant-wide scopes, delta queries, and webhooks remain deferred.

### D9. Authorized canonical OneDrive adoption producer

On 2026-09-12, the Product Owner authorized the minimum producer needed to create a real eligible lineage and complete live classification. The producer adopts an existing OneDrive Personal DOCX; it does not upload, render, or mutate the provider file.

The strict request carries only an active Template Version ID, active connection ID, stable drive-item ID, title, bounded JSON Data Snapshot, and organization-scoped idempotency key. The server derives document type, drive identity, manifest, checksums, metadata, Managed Region facts, and classification. It rejects client-authored proof fields.

Before provider I/O, VALORA resolves the active actor, `project:update`, tenant project, active Template/Template Version and strict manifest, active actor-owned personal-drive connection, and same-key replay. It bounds and canonically hashes the Data Snapshot. Graph metadata is read before content, and metadata size must be within the DOCX parser limit before download. Exact bytes are fingerprinted, then metadata is read again to reject an identity/tag/size/modified-time race.

After all provider I/O, one short transaction locks organization/project authority, rechecks permission, template status and manifest digest, connection/drive ownership, item uniqueness, and idempotency, then atomically creates:

`RenderJob → GeneratedDocument → DocumentRecord → DocumentRevision #1 → current head → M365RevisionBinding → M365ManagedContentBaseline → Managed Region rows`, plus sanitized audit facts.

`RenderJob.data_snapshot` is the protected authoritative snapshot; its compact canonical SHA-256 equals both `RenderJob.data_snapshot_hash`, `GeneratedDocument.data_snapshot_hash`, and `DocumentRevision.data_snapshot_digest_sha256`. For this new producer, `GeneratedDocument.checksum_sha256` and `DocumentRevision.content_checksum_sha256` both contain the SHA-256 of the exact downloaded DOCX bytes. Same-key/same-request replay returns the complete existing lineage without OAuth or Graph I/O; conflicting reuse returns `409`. A provider, parser, authority, race, uniqueness, or commit failure leaves no partial lineage.

The producer does not weaken D2 for legacy bindings. It creates a new baseline only as part of the same atomic first-revision/binding transaction, so current bytes are never misrepresented as an older historical state.

## Alternatives considered

### Classify a changed `eTag` or `cTag` as managed-region change

Rejected. A tag can signal change but cannot localize that change. This would misclassify outside narrative edits and violate the authority that outside-managed changes are not conflicts by default.

### Add `UNKNOWN` or `CONTENT_COMPARISON_REQUIRED` to the canonical result enum

Rejected. The accepted UI authority fixes five semantic outcomes. Eligibility and in-flight processing are separate technical states; inability to verify after an eligible attempt maps to `ACCESS_UNAVAILABLE`.

### Backfill existing baselines from the latest OneDrive bytes

Rejected unless D2 proves exact equality with the immutable Document Revision and bind-time metadata. Treating today's file as the old baseline would erase evidence of edits that occurred after binding.

### Store full document text or raw region values for easier diffing

Rejected for PR-06. Versioned canonical digests and stable region keys are sufficient for change classification and reduce sensitive-data persistence. A future conflict-resolution experience that must display values requires a separately reviewed protected snapshot contract.

### Make revalidation a `project:update` operation

Rejected for the read-only command. It would unnecessarily deny integrity checks to readers and conflate external observation with business mutation. Baseline enrollment and later sync writes remain mutations.

## Adversarial review

- The most dangerous false positive is `NO_CHANGE` after a provider or parser failure. D3 and D4 prohibit it.
- The most dangerous false baseline is a post-edit file sealed as `Old`. D2 requires exact revision checksum and bind-time metadata equality for an existing binding.
- OOXML canonicalization can hide or invent differences. Parser/fingerprint contracts are versioned, bounded, deterministic, and covered by adversarial fixtures; a contract mismatch fails unavailable rather than silently comparing unlike digests.
- Stable drive/item identity usually survives rename or move within one drive. Name/path drift alone therefore does not prove replacement. Cross-drive or unresolved identity changes do not auto-bind.
- Persisting only digests limits immediate conflict UX. That is intentional in PR-06; PR-07 must define protected value snapshots before displaying or resolving conflicts.

## Consequences

- PR-06 can implement all five canonical results without pretending metadata can identify Managed Region edits.
- Existing PR-05 bindings are not automatically eligible; they require proof-based baseline sealing and may remain blocked.
- New supported bindings become slightly more expensive because exact DOCX content must be read and parsed once when sealing the baseline.
- Return/revalidation remains read-only with respect to VALORA Document Revision and the OneDrive file.
- PR-07 receives append-only, lineage-safe observations and affected region keys without inheriting a mutable or fabricated sync state.

## Owner decision

Accepted on 2026-09-12 and extended the same day with D9. The Product Owner authorized the bounded runtime implementation and canonical OneDrive adoption producer described by `VALORA_UIUX_V2_3_PR06_M365_RETURN_REVALIDATION_TASK_BRIEF.md` and the accepted PR-06 implementation contract. This decision does not authorize a commit, push, pull request publication, deployment, OneDrive write permission, PR-07 sync/conflict behavior, OneDrive for Business, or SharePoint.

## References

- [Download driveItem content](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
- [Get driveItem and conditional tag reads](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0)
- [List driveItem versions](https://learn.microsoft.com/en-us/graph/api/driveitem-list-versions?view=graph-rest-1.0)
- `docs/adr/0040-onedrive-delegated-integration-and-file-binding.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_CONTRACT_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_VISUAL_BASELINE_ADDENDUM.md`
