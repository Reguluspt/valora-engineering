# VALORA UI/UX v2.3 — PR-01 Case State Provider Implementation Contract

**Status:** PROVIDER SLICE TECHNICALLY ACCEPTED — subsequently wired by VALORA-PR01-IMPL-004
**Task:** PR-01 — Case State Projection Foundation (Slice 3: Providers & Aggregator)
**Date:** 2026-09-04
**Architecture:** ADR 0036 (computed-on-read, no projection migration) + ADR 0037 (durable official-intake fact) + ADR 0038 (bounded preliminary-prefix predicates)

---

## 1. Scope & Boundaries

This contract defines the provider-only, offline implementation of the Global Case State projection foundation for the contiguous prefix:
`PRELIMINARY_REQUEST → PRELIMINARY_ANALYSIS → PRELIMINARY_READY → OFFICIAL_INTAKE`.

### Mandatory Boundaries
- **Provider-only / offline execution:** No HTTP endpoint, no public router, no Pydantic schema exposure, no frontend or resume-context integration.
- **No projection persistence:** Global Case State remains strictly computed on read; no case-state table, column, cache or migration.
- **Read-only single session:** Execution uses exactly one supplied SQLAlchemy Session/transaction without `FOR UPDATE`, without writes, flushes, commits or rollbacks, and without `AuditEvent` creation.
- **Fail-closed authorization:** Internal entry point re-resolves active actor and organization, requiring `project:read` permission (typed 403) and tenant-safe project resolution (safe 404 indistinguishable). No 401 boundary is implemented in this slice.
- **Parent projection contract integrity:** `VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md` and `test_uiux_v23_contract.py` remain byte-for-byte unchanged.

---

## 2. Owner-Approved Decisions (VALORA-PR01-IMPL-003)

The following decisions were owner-approved for IMPL-003:

1. **C1 — Token encoding D3–D6:** Four-slot envelope `facts[]` representation with versioned composite authoritative tokens (`av1-<sha256>`), ambiguity tokens (`amb1-<sha256>`), absence tokens (`absent-v1:absent`), blocker tokens, and warning tokens.
2. **C2 — Multiplicity => NOT_AVAILABLE + amb1:** Multiple batches, snapshots or artifacts produce raw `NOT_AVAILABLE` and an `amb1-<sha256>` token over a deterministic ambiguity payload. Selection by recency is forbidden. Multiple commit rows produce a typed `ProjectionIntegrityError`.
3. **C3 — Warning authority (Variant A):** Independently collect accepted `OPEN + WARNING` issues; deterministic id order; never convert severity; never block or change stage/current_stage/next_action. Surface them in the warning collection and include them in `case_version`.
4. **C4 — Total current_stage + InternalNextAction:** `current_stage` is total and derived from the leading COMPLETE count of the 4 prefix stages. `InternalNextAction` is a typed immutable descriptor respecting strict precedence.
5. **C5a — Deterministic ordered accepted OFFICIAL_INTAKE blocker helper:** Public helper `get_official_intake_open_blockers` in `official_intake_service.py` returning `OPEN + BLOCKING` rows ordered by `ValidationIssue.id.asc()`.
6. **C5b — Existing _has_open_blocker delegation:** NO delegation; `_has_open_blocker` and command behavior in `official_intake_service.py` remain unchanged.
7. **C6 — Public snapshot canonical digest and stored-v2 validator wrappers:** Added `snapshot_canonical_digest` and `validate_stored_v2_manifest` to `preliminary_result_service.py`.

---

## 3. Authoritative Raw Providers (D1)

The four implemented providers emit raw results in `{COMPLETE, INCOMPLETE, NOT_AVAILABLE}`. Raw `STALE` and `IN_PROGRESS` are never emitted in this slice. Unexpected provider failures raise a typed `ProjectionError`. The 12 downstream canonical stages are explicitly `NOT_AVAILABLE`.

### D3 — `preliminary_request_v1`
- **Fact input:** Tenant/project-scoped `ProjectAssetImportBatch` and its `current_source_artifact_id` pointing to `ImportSourceArtifact`.
- **Zero batches OR 1 batch with null artifact ID:**
  - Raw result: `INCOMPLETE`
  - Fact token: `preliminary_request_v1:null:absent-v1:absent`
- **Exactly 1 batch with present current artifact:**
  - Dangling or cross-lineage pointer raises `ProjectionIntegrityError`.
  - Canonical `av1` payload (`"preliminary-request-authoritative-version-v1"`):
    `artifact_id`, `import_batch_id`, `artifact_generation`, `artifact_checksum_sha256`, `artifact_state` (normalized lowercase string, e.g. `"available"`), `authoritative_timestamp` (available_at if present else created_at; normalized to UTC with six fractional digits + Z).
  - Raw result: `COMPLETE` only if artifact state is `"available"` (`ImportSourceArtifactState.AVAILABLE.value`); else `INCOMPLETE`.
  - Fact token: `preliminary_request_v1:<artifact_id>:av1-<sha256>:<complete|incomplete>`
- **>= 2 batches:**
  - Raw result: `NOT_AVAILABLE`
  - Ambiguity payload (`"preliminary-request-ambiguity-v1"`): `batch_count`, sorted `batch_ids`.
  - Fact token: `preliminary_request_v1:null:amb1-<sha256>:not_available`

### D4 — `preliminary_analysis_v1`
- **Fact input:** Tenant/project-scoped `PreliminaryAnalysisSnapshot`.
- **Zero stored snapshots:**
  - Raw result: `INCOMPLETE`
  - Fact token: `preliminary_analysis_v1:null:absent-v1:absent`
- **Exactly 1 stored snapshot:**
  - Canonical `av1` payload (`"preliminary-analysis-provider-authoritative-version-v1"`):
    `snapshot_id`, `snapshot_version`, `canonical_snapshot_digest` (from `snapshot_canonical_digest`), `finalized_at`.
  - Raw result: `COMPLETE` only if current (matches unique current batch, source artifact generation and available state, structure snapshot, mapping decision and profile usage digests, recomputed line_manifest canonical digest equality, and stored manifest passes strict v2 validation via `validate_stored_v2_manifest`). Otherwise `INCOMPLETE`. Never `STALE`.
  - Fact token: `preliminary_analysis_v1:<snapshot_id>:av1-<sha256>:<complete|incomplete>`
- **>= 2 stored snapshots:**
  - Raw result: `NOT_AVAILABLE`
  - Ambiguity payload (`"preliminary-analysis-ambiguity-v1"`): `count`, sorted `<id>@<version>` identities.
  - Fact token: `preliminary_analysis_v1:null:amb1-<sha256>:not_available`

### D5 — `preliminary_ready_v1`
- **Fact input:** Tenant/project-scoped `PreliminaryResultArtifact`.
- **Zero stored artifacts:**
  - Raw result: `INCOMPLETE`
  - Fact token: `preliminary_ready_v1:null:absent-v1:absent`
- **Exactly 1 stored artifact:**
  - Canonical `av1` payload (`"preliminary-ready-provider-authoritative-version-v1"`):
    `artifact_id`, `version`, `content_checksum_sha256`, `source_snapshot_sha256` (canonical `PreliminaryAnalysisSnapshot` digest), `canonical_lineage_manifest_digest`, `analysis_snapshot_id` (or null), `created_at`.
  - Raw result: `COMPLETE` only when `artifact.source_snapshot_sha256` matches the expected analysis snapshot digest and the stored lineage manifest matches the production `_build_lineage_manifest` rebuilt from current authoritative source, structure, mapping, analysis and output-layout facts.
  - Full-manifest equality uses canonical JSON bytes so JSON types are significant (`true`, `1`, `1.0` and `"1"` are distinct) while object-key order is irrelevant. Any missing, additional, value-mutated or type-mutated lineage field produces `INCOMPLETE`.
  - Fact token: `preliminary_ready_v1:<artifact_id>:av1-<sha256>:<complete|incomplete>`
- **>= 2 stored artifacts:**
  - Raw result: `NOT_AVAILABLE`
  - Ambiguity payload (`"preliminary-ready-ambiguity-v1"`): `count`, sorted `<id>@<version>` identities.
  - Fact token: `preliminary_ready_v1:null:amb1-<sha256>:not_available`

### D6 — `official_intake_commit_v1`
- **Fact input:** Tenant/project-scoped `ProjectOfficialIntakeCommit`.
- **Zero commit rows:**
  - Raw result: `INCOMPLETE`
  - Fact token: `official_intake_commit_v1:null:absent-v1:absent`
- **Exactly 1 commit row:**
  - Canonical `av1` payload (`"official-intake-authoritative-version-v1"`):
    `artifact_id`, `artifact_version`, `artifact_checksum`, `source_snapshot_sha256`, `committed_at`.
  - Raw result: `COMPLETE`
  - Fact token: `official_intake_commit_v1:<commit_id>:av1-<sha256>:complete`
- **>= 2 commit rows:**
  - Raises typed `ProjectionIntegrityError` (uniqueness is a database authority invariant).

---

## 4. Blockers and Warnings (D6)

- **Official Blockers:**
  - Target spellings: `("project", "Project")` matching `project_id`, or `("project_asset_line", "ProjectAssetLine")` resolving through an asset line belonging to this tenant/project.
  - Severity: `BLOCKING`; Status: `OPEN`. Ordered deterministically by `ValidationIssue.id.asc()`.
  - Contributed fact token: `validation_issue_blocker_v1:<id>:rv<row_version>:open`.
  - Effect: An open blocker changes `OFFICIAL_INTAKE` stage result from `INCOMPLETE` to `BLOCKED` only when commit fact is absent. If commit fact exists, `OFFICIAL_INTAKE` remains `COMPLETE`.
  - Preliminary stages have no registered blockers and must never become `BLOCKED`.
  - An open official blocker takes global next-action precedence and outranks preliminary pending actions.
- **Warnings (Variant A):**
  - Same accepted official target spellings and tenant scopes.
  - Severity: `WARNING`; Status: `OPEN`. Ordered deterministically by `ValidationIssue.id.asc()`.
  - Contributed fact token: `validation_issue_warning_v1:<id>:rv<row_version>:open`.
  - Effect: Surfaced separately; never converted to blocking; never modifies stage result, `current_stage`, or `next_action`. Contributed to `case_version` so changes alter the token.

---

## 5. Global `case_version` Token (D2)

The `case_version` token is an opaque lowercase SHA-256 hex digest computed over canonical JSON:

```json
{
  "contract": "global-case-state-v1",
  "facts": [
    "<lexicographically sorted fact tokens>"
  ],
  "organization_id": "<lowercase hyphenated UUID>",
  "project_id": "<lowercase hyphenated UUID>"
}
```

Serialization uses `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")`.
Static capabilities, display text, user secrets, and database-specific identifiers are excluded.

---

## 6. Aggregator & Next Action (D8)

### Canonical Stage Order
1. `PRELIMINARY_REQUEST`
2. `PRELIMINARY_ANALYSIS`
3. `PRELIMINARY_READY`
4. `OFFICIAL_INTAKE`
5. `ASSET_REVIEW` ... 16. `PUBLISHED` (explicitly `NOT_AVAILABLE`)

### Total `current_stage`
Derived strictly from the count of leading `COMPLETE` stages among the four prefix stages:
- 0 leading `COMPLETE` => `PRELIMINARY_REQUEST`
- 1 leading `COMPLETE` => `PRELIMINARY_ANALYSIS`
- 2 leading `COMPLETE` => `PRELIMINARY_READY`
- 3 leading `COMPLETE` => `OFFICIAL_INTAKE`
- 4 leading `COMPLETE` => `OFFICIAL_INTAKE`

The aggregator never jumps past an earlier `INCOMPLETE`, `NOT_AVAILABLE`, or `BLOCKED` stage.

### `InternalNextAction` Precedence
`InternalNextAction(kind, stage, semantic_route_key, validation_issue_id)`:
1. **Accepted official blocker present:** `kind = "BLOCKER"`, `stage = "OFFICIAL_INTAKE"`, `validation_issue_id = lowest_id`, `semantic_route_key = None`.
2. **All four prefix stages COMPLETE:** `kind = "NO_AUTHORIZED_DOWNSTREAM_ACTION"`, `stage = None`, `semantic_route_key = None`, `validation_issue_id = None`.
3. **First non-complete stage in canonical order:**
   - If `INCOMPLETE`: `kind = "PENDING"`, `stage = that stage`, `semantic_route_key = <route_key>`, `validation_issue_id = None`.
   - If `NOT_AVAILABLE`: `kind = "UNAVAILABLE"`, `stage = that stage`, `semantic_route_key = None`, `validation_issue_id = None`.

### All-Four-Complete Semantics
When all four implemented stages are `COMPLETE` and no blockers exist:
- `current_stage`: `OFFICIAL_INTAKE`
- `next_action`: `InternalNextAction(kind="NO_AUTHORIZED_DOWNSTREAM_ACTION", stage=None, semantic_route_key=None, validation_issue_id=None)`
- Stages 5–16 remain `NOT_AVAILABLE`. Never `PUBLISHED`.

---

## 7. Static Capability Registry (D7)

Version: `pr01-prefix-v1`.
Defines static capability for all 16 canonical stages:
- Implemented: `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS`, `PRELIMINARY_READY`, `OFFICIAL_INTAKE`.
- Unavailable: `ASSET_REVIEW` through `PUBLISHED`.
Capability metadata is excluded from `case_version` while it remains static.

---

## 8. Local Technical Acceptance

The offline provider/aggregator slice completed owner-directed local technical acceptance on
2026-09-05. The accepted local provider candidate remains uncommitted. The subsequent, separately
authorized `VALORA-PR01-IMPL-004` slice wires it to the read endpoint without changing the provider
contract or adding projection persistence.

- focused provider/aggregator tests: `40 passed`, `0 failed`, `0 skipped`;
- focused PostgreSQL projection tests: `3 passed`, `0 failed`, `0 skipped`;
- existing v2.3 design-contract tests: `5 passed`, `0 failed`, `0 skipped`;
- full relevant PR-01 packet with `CI=true`: `226 passed`, `0 failed`, `0 skipped`,
  `0 deselected`, `0 xfail`;
- adversarial full-manifest matrix through the real aggregator: 126 missing/value/type mutations,
  all `INCOMPLETE`; matching and key-reordered manifests remain `COMPLETE`;
- fresh read-only PostgreSQL verification: 8 production-generated artifacts retained
  `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS` and `PRELIMINARY_READY` as `COMPLETE`;
- Ruff, Python compile, trailing-whitespace/final-newline scan, `git diff --check`, Alembic single
  head `c159fab13c3a`, staged-empty/25-file dirty scope and 18 protected hashes passed;
- fresh Qwen independent review returned `PASS` with no blocking finding;
- the formal Sol process could not inspect files because its read-only command host was unavailable
  and therefore is not recorded as an acceptance review. The Product Owner directed the coordinator
  to perform the replacement gate; that gate reproduced and corrected the JSON type-equivalence
  defect, then returned `PASS` on the corrected candidate.

Detailed evidence and explicit deferrals are recorded in
`docs/audits/2026-09-05__PR-01__CASE_STATE_PROVIDER_RUNTIME_FOUNDATION_AUDIT.md`.
