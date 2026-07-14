# ADR 0029: Excel Staging Apply Command and Lineage

## Status

Accepted (owner-approved design authority, 2026-07-14)

## Context

S12-PR-003 merged the Excel Staging Validation Engine to `main` (PR #8, merge commit `c2f154dda3ba9c9dd4bdbdb8ce23676315bba1b7`). Staging remains isolated from official `ProjectAssetLine` rows. The Excel import lifecycle still includes a future **Apply** step that promotes validated staging rows into official project asset lines.

Post-merge design discovery found no approved Apply task contract: no endpoint body, eligibility policy, field mapping, lineage schema, idempotency, concurrency fingerprint, or audit schema. ADR 0028 already governs restricted Workbench fields (`description`, `appraised_unit_price`, `review_status`, `validation_status`) and DRAFT-only official draft-commit.

This ADR freezes owner-approved Apply design for:

1. **S12-R-008** — documentation/authority reconciliation (this change set).
2. **S12-PR-004** — backend implementation only after S12-R-008 merges to `main`.

## Decision

### Implementation identity

- Task: `S12-PR-004 — Excel Staging Apply Command & Provenance`
- Branch (implementation only): `s12-pr-004-excel-staging-apply-command-provenance`
- Backend-only: command, API adapter, lineage migration, tests, audits
- Frontend Apply UX is deferred; no task ID assigned here

### Invocation

```text
POST /api/v1/projects/{project_id}/asset-imports/{batch_id}/apply
```

Required JSON body:

```json
{
  "confirm": true
}
```

- Explicit, synchronous, human-confirmed only
- No auto-apply after upload/validate
- No dry-run, worker, background job, scheduler, queue, or AI action in v1
- Missing or non-true `confirm` → reject with zero mutation and zero success audit

### RBAC, tenancy, project state

- Permission: `workbench:edit`
- Actor, organization, project: server-derived
- Cross-tenant / wrong-project / missing batch / inaccessible project → established safe `404`
- Apply only while `Project.status == DRAFT`
- Active Workbench session is **not** required for this backend command

### Eligibility

- Batch status must be exactly `ready_for_review`
- Non-empty batch
- Every staging row must have `validation_status == valid`
- Batch counters must agree with actual row states under lock
- Any pending, invalid, or warning row rejects the **whole** command (all-or-nothing)
- All other batch states, including `applied`, reject with `409` and zero mutation

### Contract version (frozen)

```text
contract_version = s12-pr-004-v1
```

Every Apply success and failure audit payload **must** set `contract_version` to exactly `s12-pr-004-v1` (lowercase). No aliases or inferred version strings.

### Mapping registry (explicit only)

| Staging input | Official target | Transformation |
| --- | --- | --- |
| `proposed_asset_name` | `asset_name` | Required; trim outer Unicode whitespace; non-empty; max 255 |
| `proposed_description` | `description` | Optional; trim outer Unicode whitespace; blank → `null`; max 5000; owner-authorized **only** through Apply |
| `proposed_quantity` | `quantity` | Blank/null → `1.0000`; else finite Decimal `>= 0`, max 4 fractional and 11 integer digits; **no silent rounding**; Decimal-only parse (scientific notation only if expanded value fits limits); never convert through float |
| `proposed_unit` | `unit_id` | Blank/null → `null`; else ACTIVE Unit lookup (see deterministic mechanics) |
| `proposed_raw_price` | `raw_price` | Blank/null → `null`; else finite Decimal `>= 0`, max 2 fractional and 13 integer digits; **no silent rounding**; Decimal-only parse; never convert through float |
| `proposed_currency` | `raw_price_currency_id` | Blank/null → `null`; else ACTIVE Currency lookup (see deterministic mechanics) |
| constant | `review_status` | `pending` |
| constant | `validation_status` | `unvalidated` |

**Must never apply:** `proposed_appraised_unit_price`, `proposed_review_status`, `proposed_validation_status`, raw/unregistered spreadsheet keys. `raw_values` remains staging evidence only.

### Deterministic mapping mechanics (frozen)

- **Stage order:** `source_row_number ASC, id ASC`.
- Official inserts and response `created_lines[]` use **that exact order**.
- Trim outer **Unicode** whitespace.
- Matching is **exact Unicode case-insensitive only**; no fuzzy, substring, accent folding, or auto-create of master data.
- **Unit priority:** code → display name → unique symbol. A unique match at a higher tier **stops** lower tiers. The selected tier must resolve exactly one ACTIVE row; otherwise mapping invalid.
- **Currency priority:** code → display name; **symbols forbidden**. Selected tier must resolve exactly one ACTIVE row; otherwise mapping invalid.
- **Decimal-only parsing.** Scientific notation allowed only when the expanded value fits approved Numeric integer/scale limits. Never convert through float and never round.

### Creation semantics

- One new `ProjectAssetLine` per eligible staging row (in stage order above)
- No update, upsert, name-dedup, replace, or delete of existing official lines

### Atomicity and idempotency

- One transaction: all lines + lineage + batch `applied` + success audit
- Any mapping/lookup/constraint/flush/savepoint/audit/outer-commit failure rolls back everything
- Success → batch `applied`; re-apply → `409`, zero new lines/success audit
- Corrections require a **new** import batch (upload → validate → review → Apply)

### Concurrency

Lock order for Apply:

```text
scoped Project FOR UPDATE → scoped batch FOR UPDATE → ordered staging rows → inserts
```

Pre-attempt generation fingerprint includes:

- project status
- batch status, source filename/sheet, counters
- ordered staging row IDs and source row numbers
- all registered proposed inputs used by Apply
- row validation status/errors/warnings
- latest upload, validation-success, and Apply-success audit IDs

Failure recovery: rollback, re-lock, write failure audit only if fingerprint still matches. Stale failures must not overwrite newer upload/validate/Apply generations.

### Failure-state preservation (frozen)

Every rejected or failed Apply preserves **exactly**:

- batch status
- source filename and sheet
- all counters
- staging rows, raw/mapped values, validation statuses/errors/warnings
- all pre-existing official lines and lineage

For an eligible (confirmed, scoped) attempt that fails mapping or engine recovery, the batch remains `ready_for_review`. **Do not** introduce batch status `apply_failed`. Only the append-only failure audit permitted by the audit cardinality matrix may be new.

### Audit cardinality matrix (frozen)

| Outcome | Success audit | Failure audit |
| --- | ---: | ---: |
| confirmation missing/false | 0 | 0 |
| safe 404 / inaccessible target | 0 | 0 |
| project not DRAFT | 0 | 0 |
| batch state not allowed / rows not ready / re-apply | 0 | 0 |
| successful Apply | exactly 1 | 0 |
| mapping invalid after confirmed, scoped attempt | 0 | exactly 1 if fingerprint matches |
| engine/savepoint/flush/outer-commit failure | 0 | exactly 1 if fingerprint matches and failure audit persists |
| stale fingerprint mismatch | 0 | 0 |
| failure-audit persistence failure | 0 | 0; preserve generation and return safe 500 |

Repeated confirmed mapping failures may each create one failure audit. Never include raw/proposed values in failure audits.

### Lifecycle after success

- Batch status → `applied`
- Staging rows, raw/mapped values, validation results, and counters retained as immutable historical evidence
- Upload, validate, and Apply reject `applied` batches

### Lineage schema (S12-PR-004 migration)

On `project_asset_lines`:

- `source_import_batch_id` nullable, indexed, FK → `project_asset_import_batches.id` ON DELETE RESTRICT
- `source_staging_row_id` nullable, indexed, **unique**, FK → `project_asset_import_staging_rows.id` ON DELETE RESTRICT

Imported lines set both; manual lines leave both null. Uniqueness of `source_staging_row_id` is the database-level exact-once invariant. Command-level checks enforce org/project/batch/staging scope.

### Audit

| Kind | Name |
| --- | --- |
| Command | `ApplyProjectAssetImportBatch` |
| Success event | `ProjectAssetImportBatchApplied` |
| Failure event | `ProjectAssetImportBatchApplyFailed` |

Success payload keys only:

```text
contract_version, organization_id, project_id, batch_id,
source_status, target_status, total_rows, created_count
```

Failure payload keys only:

```text
contract_version, organization_id, project_id, batch_id,
source_status, error_code
```

In both payloads, `contract_version` **must** be exactly `s12-pr-004-v1`.

No raw cells, proposed business values, SQL, paths, stacks, secrets, or bulk line IDs in payloads.

### ADR 0028 interaction

- Apply is a **distinct** official-mutation command (human confirmation, DRAFT-only, explicit handlers, atomic audit, rollback)
- Not a direct PATCH bypass; direct PATCH of restricted fields remains blocked
- Owner authorizes **description creation** only through Apply, with the same string/max-length safeguards as ADR 0028
- Spreadsheet appraised/review/validation values remain forbidden
- New lines use the model’s initial `row_version` (expected `1`); no client version token on create
- Subsequent restricted-field edits remain under ADR 0028 draft-commit

### Correction

- No reverse Apply or delete of imported lines in v1
- While project is DRAFT, corrections use existing Workbench official mutation commands
- After DRAFT, future change-request/reversal authority is required

### API response and safe errors

Response: `ProjectAssetImportBatchApplyResponse` with:

```text
project_id, import_batch_id, status, created_count,
created_lines[{line_id, staging_row_id, source_row_number}]
```

| Condition | HTTP | `error_code` | Vietnamese detail |
| --- | ---: | --- | --- |
| confirmation absent/false | 400 | `apply_confirmation_required` | `Bạn phải xác nhận trước khi áp dụng dữ liệu.` |
| project not DRAFT | 400 | `apply_project_not_draft` | `Chỉ có thể áp dụng dữ liệu khi dự án ở trạng thái nháp.` |
| batch state not eligible | 409 | `apply_state_not_allowed` | `Lô nhập liệu chưa sẵn sàng để áp dụng.` |
| zero or non-valid rows | 409 | `apply_rows_not_ready` | `Tất cả dòng phải hợp lệ trước khi áp dụng.` |
| invalid numeric/reference mapping | 400 | `apply_mapping_invalid` | `Dữ liệu chưa thể ánh xạ vào danh sách tài sản chính thức.` |
| unexpected engine/transaction failure | 500 | `apply_engine_failed` | `Không thể áp dụng dữ liệu Excel. Vui lòng thử lại.` |

Unknown/cross-tenant → safe `404`. No technical exception text to clients.

### Acceptance gates (S12-PR-004)

In addition to repository-wide gates:

1. Endpoint body, permission, safe 404, tenant/project scope, DRAFT-only
2. Allowed/rejected batch states and zero-row behavior
3. All-valid / all-or-nothing eligibility
4. Every registered field mapping and numeric boundary
5. ACTIVE Unit/Currency exact lookup; unknown, inactive, ambiguous
6. Exclusion of appraised/review/validation spreadsheet fields
7. One-line-per-staging-row + lineage uniqueness
8. Re-apply `409` and zero duplicates
9. Success audit atomicity and fault-injection rollbacks
10. Stale-failure fingerprint protection
11. Existing official-line field-for-field immutability
12. Migration upgrade/downgrade and single Alembic head
13. PostgreSQL multi-session matrix: Apply vs Apply; Upload vs Apply both orders; Validate vs Apply both orders; project workflow transition vs Apply
14. Exact generation assertions, audit order/cardinality, thread timeouts, lock-wait evidence
15. Full backend, worker, frontend, security, dependency, and build gates

Local PostgreSQL skips are `SKIPPED`, never `PASS`. CI must execute all PostgreSQL Apply matrix nodes with **zero skips**.

## Full D1–D17 authority index

| ID | Decision |
| --- | --- |
| D1 | S12-R-008 docs; S12-PR-004 backend Apply + lineage; no frontend |
| D2 | Sync POST apply + `{ "confirm": true }` only |
| D3 | `workbench:edit`; DRAFT-only; safe 404; no session required |
| D4 | `ready_for_review`; all rows `valid`; non-empty; all-or-nothing |
| D5 | Explicit registry above; description via Apply only; defaults pending/unvalidated |
| D6 | Append only; no upsert/dedup/delete |
| D7 | Single transaction; full rollback |
| D8 | Success → `applied`; re-apply 409; new batch for corrections |
| D9 | Project → batch → staging lock order; full fingerprint; stale guard |
| D10 | Retain staging; reject upload/validate/apply on applied |
| D11 | Nullable lineage FKs with unique staging-row id |
| D12 | Command/events and payload keys above |
| D13 | Distinct ADR 0028-compliant command; description exception only |
| D14 | No reverse/delete; DRAFT corrections via Workbench |
| D15 | Response shape and VI error table |
| D16 | Backend-only; future UI separate |
| D17 | Acceptance matrix including PG concurrency zero-skip CI |

## Non-goals

- Frontend Apply UX
- AI auto-apply
- Worker/background Apply
- Partial apply of valid rows while invalid remain
- Reverse Apply / bulk delete
- Invented business-key upsert
- Writing free-text unit/currency into non-FK fields
- Applying spreadsheet appraised price or workflow statuses

## Consequences

- S12-PR-004 implementers have unambiguous contracts and must not invent domain behavior.
- ADR 0028 remains authoritative for restricted-field **edits** after creation; Apply is the sole approved path to **create** `description` from staging in v1.
- Excel upload and validate continue never to mutate official lines.
- Operator docs must not treat S12-PR-003 as blocked after merge; next implementation after S12-R-008 merge is S12-PR-004.

## Related documents

- `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md` §15
- `docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md` (addendum)
- Owner decision package embedded in S12-R-008 execution authority (2026-07-14)
