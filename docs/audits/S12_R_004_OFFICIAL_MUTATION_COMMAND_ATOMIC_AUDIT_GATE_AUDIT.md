# S12-R-004 — Official Mutation Command & Atomic Audit Gate Audit

## Status
`LOCAL IMPLEMENTATION COMPLETE — AWAITING DRAFT PR AND CI`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `c46ea1ccc43a0010b455c3448dc56f21f874bc1d` |
| Branch | `s12-r-004-official-mutation-command-atomic-audit-gate` |
| Previous code-bearing SHA | `7086eca114331e59a5d595a0064478aa42fab27c` |
| Corrective code-bearing SHA | `ff7b33c5bc43868056d9dca85a1e1e422c274a54` (Commit A: corrective gaps) |
| Draft PR | PENDING |
| CI Run ID / URL | PENDING |

## Root Cause
Prior to S12-R-004, users could bypass the Workbench human-commit flow by issuing direct `PATCH` requests to `/api/v1/projects/{project_id}/asset-lines/{line_id}`. There was no exact optimistic version lock, no DRAFT-only project status gate, no typed field validation for `Decimal`, and the audit payload key `field_keys` was auto-redacted by the sanitizer (which redacts any key containing `"key"`).

## ADR / Design Authority
- `docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md` — Status: **Accepted**
- DRAFT-only policy: **APPROVED** by user (2026-07-12)
- Exact three-way version equality: **APPROVED**

## Command Architecture
```text
authenticated actor
→ RBAC (workbench:edit via derive_effective_permissions)
→ organization/project scope (safe 404 for cross-tenant)
→ ACTIVE owned workbench session (require_owned_workbench_session)
→ DRAFT-only ProjectWorkflowStatus (all non-DRAFT → 400)
→ PostgreSQL row lock (SELECT FOR UPDATE via .with_for_update())
→ exact version equality (request == draft.base == official.row_version)
→ typed validation via FIELD_HANDLERS (description str, appraised_unit_price Decimal)
→ explicit mutation via MUTATION_REGISTRY (no raw setattr)
→ delete applied drafts, keep unrelated drafts
→ append AuditEvent (event_name: project.asset_line.draft_committed)
→ one atomic transaction (audit fail → full rollback)
```

## Implementation Details

### 1. DRAFT-Only Policy (User Approved)
- `Project.status == DRAFT`: commit allowed
- `SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `ARCHIVED`, `CANCELLED`: reject 400
- Official line, row_version, and drafts remain unchanged
- No draft-commit AuditEvent persisted
- Parameterized test over all `ProjectWorkflowStatus` values

### 2. Exact Version Lock
- `version_token` must be strictly positive integer (> 0)
- Missing/malformed/non-positive → 400
- `request_version == draft.base_row_version == locked official.line.row_version`
- Stale/future/mismatch → 409

### 3. Direct PATCH Bypass Protection
- Forbidden fields: `description`, `appraised_unit_price`, `review_status`, `validation_status`
- Uses `payload.model_fields_set` (not `is not None`)
- Blocks explicit `null` bypass
- Allowed fields (e.g. `asset_name`) still accepted

### 4. Decimal-Safe Handlers
- `Decimal` end-to-end, no float conversion
- `Numeric(15,2)`: max 13 integer digits, max 2 fractional digits
- No silent rounding/truncation
- Rejects: bool, list, dict, NaN, Inf, negative, scale/precision overflow

### 5. Audit Payload
- Key: `committed_fields` (NOT `field_keys` — avoids sanitizer redaction)
- Audit includes: actor, organization, project, session, entity, before/after, versions, correlation_id, command_name, event_name, confirm
- Stable names: `command_name = CommitProjectAssetLineDraft`, `event_name = project.asset_line.draft_committed`

### 6. Atomic Rollback
- `log_audit_event` failure → full transaction rollback
- Official values unchanged, row_version unchanged, drafts preserved, zero AuditEvents
- Monkeypatched test with exact assertions

### 7. Side-Effect Prohibition
- AST-based static scan: no `requests`, `httpx`, `urllib`, `aiohttp` imports in command module
- Non-vacuous: test fails when forbidden import/call is introduced

## Test Inventory

### Backend Dedicated Test File
`backend/tests/test_s12_r_004_official_mutation.py` (1226 lines)

| # | Test | Scope | Method |
|---|---|---|---|
| 1 | `test_draft_only_policy` | DRAFT-only matrix (5 states) | Parameterized, zero-mutation asserts |
| 2 | `test_patch_model_fields_set_null_bypass_blocked` | PATCH null bypass | Explicit `null` in body → 400 |
| 3 | `test_patch_model_fields_set_allowed_field_accepted` | PATCH allowed field | Normal update accepted |
| 4 | `test_version_token_matrix` | Version token validation | 7 cases: 0, -1, abc, 1.5, "", stale, valid |
| 5 | `test_validate_description_unit` | Description validator | 10 cases: strings, non-strings, too-long, None |
| 6 | `test_validate_appraised_unit_price_unit` | Price validator | 14 cases: valid, type errors, NaN, inf, scale/precision overflow |
| 7 | `test_permissions_and_scoping_matrix` | Security matrix | 401, 403, 404 + zero-mutation |
| 8 | `test_audit_trail_payload_committed_fields` | Audit payload | committed_fields key, before/after, versions, correlation_id |
| 9 | `test_atomic_rollback_on_audit_failure` | Atomic rollback | Monkeypatch + zero mutation |
| 10 | `test_remaining_draft_state_after_partial_commit` | Draft lifecycle | 2-step partial then full commit |
| 11 | `test_no_forbidden_side_effects_on_commit` | Side effects | No AI/taxonomy calls |
| 12 | `test_commit_command_ast_no_http_calls` | AST static scan | Forbidden import detection |
| 13 | `test_confirm_false_rejected_no_mutation` | Human confirmation | confirm=False → 400, zero mutation |
| 14 | `test_empty_field_keys_rejected` | Input validation | Empty array → 400 |
| 15 | `test_duplicate_field_keys_rejected` | Input validation | Duplicate keys → 400 |
| 16 | `test_unsupported_field_key_rejected` | Allowlist enforcement | Unregistered field → 400 |
| 17 | `test_cross_org_scoping_rejected` | Tenant isolation | Wrong org actor → 404 |
| 18 | `test_postgres_concurrent_official_commit` | PostgreSQL concurrency | 2-thread barrier, SELECT FOR UPDATE, 1 success + 1 409 |

### Frontend Tests (added in micro-corrective pass)
| # | File | Tests | Scope |
|---|---|---|---|
| 19 | `useWorkbenchDraftSync.test.ts` | 3 | commitAssetLineDraft with version_token |
| 20 | `projects.test.ts` (NEW) | 2 | API serialization: version_token in POST body |
| 21 | `AssetGrid.commit.test.tsx` (NEW) | 4 | Human confirm reject/accept, String(row_version), field list |

### Legacy Test Files
| File | Net Diff vs Main | Reason |
|---|---|---|
| `test_projects_api.py` | +2/-2 (4 lines) | Minimal mandatory: added `"version_token": "1"` to 2 legacy payloads (schema now requires it) |
| `test_workbench_api.py` | 0 diff | Matches main exactly |

## Changed Files
```text
backend/app/api/projects.py                                           (semantic changes only)
backend/app/modules/project_master_data/commands/__init__.py           (NEW)
backend/app/modules/project_master_data/commands/commit_asset_line_draft.py (NEW)
backend/app/modules/project_master_data/workbench_schemas.py           (schemas)
backend/tests/test_projects_api.py                                     (+2/-2 mandatory)
backend/tests/test_s12_r_004_official_mutation.py                      (NEW)
docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md       (NEW)
docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md          (Section 13+14)
docs/audits/S12_R_004_OFFICIAL_MUTATION_COMMAND_ATOMIC_AUDIT_GATE_AUDIT.md (this file)
frontend/src/api/projects.ts                                           (+1 line: commitAssetLineDraft)
frontend/src/components/layout/WorkbenchLayout.tsx                     (minimal)
frontend/src/components/workbench/AssetGrid.tsx                        (helper + onClick)
frontend/src/components/workbench/session/__tests__/useWorkbenchDraftSync.test.ts  (version_token)
frontend/src/api/__tests__/projects.test.ts                            (NEW)
frontend/src/components/workbench/__tests__/AssetGrid.commit.test.tsx  (NEW)
```

## Local Quality Gate Results (Commit A — `ff7b33c`)

| Gate | Command | Result |
|---|---|---|
| Backend ruff | `python -m ruff check backend` | **PASS** — All checks passed |
| Backend pytest | `python -m pytest backend/tests -rs` | **319 passed, 4 skipped, 0 failed** (30.44s) |
| Security scanner | `python tests/check_security.py` | **PASS** — Controlled baseline validated |
| Alembic heads | `alembic heads` | **PASS** — Single head: `db5977424e7b` |
| Worker ruff | `python -m ruff check worker` | **PASS** — All checks passed |
| Worker pytest | `python -m pytest worker/tests -rs` | **1 passed** |
| Frontend lint | `npm run lint --prefix frontend` | **PASS** — `tsc --noEmit` |
| Frontend build | `npm run build --prefix frontend` | **PASS** |
| Frontend vitest | `npm test --prefix frontend -- --run` | **34 passed (9 test files)** |
| Frontend npm audit | `npm audit --prefix frontend` | **PASS** — 0 vulnerabilities |

### Skipped Tests (all PostgreSQL-gated)
| # | File | Reason |
|---|---|---|
| 1 | `test_auth_endpoints.py:737` | PostgreSQL not available. Skipping integration test. |
| 2 | `test_s12_r_004_official_mutation.py:1049` | No PostgreSQL URL configured; skipping concurrency test (local dev). |
| 3 | `test_workbench_api.py:696` | PostgreSQL not configured — awaiting CI with PostgreSQL service. |
| 4 | `test_workbench_api.py:980` | PostgreSQL not configured — awaiting CI with PostgreSQL service. |

## PostgreSQL Concurrency
`test_postgres_concurrent_official_commit` — locally SKIPPED (no PostgreSQL configured).
Requires CI with PostgreSQL service container to execute.
In CI, must `pytest.fail` if `CI=true` and PostgreSQL unavailable.

## Micro-Corrective Finding Disposition

| Finding | Source | Resolution | Commit |
|---|---|---|---|
| F-1: Frontend test missing version_token | Onboarding report | Added `version_token: "1"` to test call and assertion | `ff7b33c` |
| F-2: No API serialization test | Corrective §17 | Created `projects.test.ts` with fetch mock, exact body assert | `ff7b33c` |
| F-3: No human confirmation test | Corrective §17 | Extracted `executeDraftCommit` helper, 4 unit tests | `ff7b33c` |
| F-4: Contract §13 stale | Corrective §16 | Updated request shape, added version_token documentation | `ff7b33c` |
| F-5: Audit premature PASS | Corrective §18 | Status changed to AWAITING DRAFT PR AND CI, local gates recorded | Current commit |
| F-6: test_projects_api.py diff | Onboarding report | Verified +2/-2, documented as minimal mandatory | N/A (verified) |
| F-7: projects.py semantic diff | Onboarding report | Verified semantic-only changes, no formatting churn | N/A (verified) |

## Out of Scope
- S12-R-005: Dynamic project routing (hard-coded `hd-98-gia-lai`)
- S12-R-006: Excel parser hardening
- S12-PR-003: Validation Engine
- Workbench fabricated/mock data
- AI governance, report generation, background tasks

## Final Verdict
```text
PENDING INDEPENDENT RE-AUDIT AND CI
```
