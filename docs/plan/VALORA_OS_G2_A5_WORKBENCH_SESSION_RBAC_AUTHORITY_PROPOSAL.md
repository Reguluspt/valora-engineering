# OS-G2 A5R — Workbench Session Open RBAC Authority Proposal

**Status: PROPOSED / PRODUCT OWNER DECISION REQUIRED**
**Task:** Issue #82 — VALORA-TASK-OS-G2-A5R-WORKBENCH-SESSION-OPEN-RBAC-AUTHORITY
**Date:** 2026-10-02
**Risk:** HIGH — authorization policy / standard-role capability
**Verified baseline:** `origin/main` = `416157e6330f861127455a66fd5df9c0972bc02a`; exact-main [CI #545 SUCCESS](https://github.com/Reguluspt/valora-engineering/actions/runs/37004731799).
**Scope:** authority proposal only. No permission grant or runtime implementation is authorized by this document.

## 1. Exact blocker and existing authority

A4 / Issue #79 / PR #80 is merged at the baseline above. Accepted [ADR 0049](../adr/0049-asset-line-human-review-and-validation-authority.md), D1/D6, and the [Line Decision Contract](../implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md), §2, require effective existing `workbench:edit` and an active owned Workbench session for validation, human review and receipt recovery. They authorize no new permission or grant.

The existing browser path is `WorkbenchLayout` → `useWorkbenchSession` → `createSession` → **POST `/api/v1/workbench/sessions`**. That endpoint requires **`workbench:open`**, before creating or returning an existing active owned session. Accepted RBAC-001 granted only `workbench:edit` to standard `owner` and `appraiser`; it explicitly preserved all other endpoint checks and role grants. Edit does not imply open.

The stopped A5 synthetic owner browser returned **403** from this POST, including retry, before Asset Review validation/review could proceed. Existing A5 transport evidence records:

```json
{"method":"POST","path":"/api/v1/workbench/sessions","status":403,"response_dropped":false,"command_id":null,"contract_version":null}
```

This is the first missing permission on the observed minimum product path, not a missing validation/review permission. A5 remains STOPPED; this task did not rerun browser acceptance. Existing stop evidence is local to `F:/Project Valora/g2-a5-evidence/transport.jsonl` and `TASK_STATE.json`; it is historical observation, not certification of this candidate. A5's uncommitted worktree is `F:/Project Valora/valora-os-g2-a3-authority`, branch `codex/os-g2-a5-asset-review-product-closure`; preserve it unchanged.

## 2. Verified permission graph

All repository paths below are inspected at the verified baseline, except the explicitly identified stopped A5 files in §3.

| Minimum path / operation | Existing server authority | Verification |
| --- | --- | --- |
| Create or obtain owned active session: POST `/api/v1/workbench/sessions` | `workbench:open`; same-tenant Project; active session belongs to authenticated user | [workbench.py](../../backend/app/api/workbench.py), `create_session` |
| Maintain session: POST `.../{session_id}/heartbeat` | `workbench:edit`; active owned session; exact session row version | Same file, `session_heartbeat`; [session resolver](../../backend/app/modules/workflow_workbench/resolve_owned_session.py) |
| Selection state sync: POST `.../{session_id}/selection` | `workbench:edit`; active owned session; scoped targets | Same file, `save_selection` |
| Layout/grid-view/panel-state writes; inline-edit/checkpoint writes | `workbench:edit`; existing ownership/target checks | Same file, corresponding POST handlers; no read grant inferred |
| Read Project / asset grid / draft state | Existing `project:read` | [projects.py](../../backend/app/api/projects.py), Project GET, `list_project_asset_lines`, `get_project_asset_lines_draft_state` |
| Read Case State v3 | Authenticated actor and existing scoped projection authorization | Same file, `get_project_case_state`; no Workbench read dependency |
| ValidateProjectAssetLine / DecideProjectAssetLineReview | Existing effective `workbench:edit` + active owned session; all accepted command eligibility, tenant, lineage, confirmation and CAS checks | [A4 API](../../backend/app/api/asset_review_lines.py); [commands](../../backend/app/modules/project_master_data/application/asset_review_line_commands.py), `_execute` / `require_line_access`; [authority](../../backend/app/modules/project_master_data/application/asset_review_authority.py), `require_mutation_actor` |
| GET exact scoped Asset Review command receipt | Fresh effective `workbench:edit` + active owned session; actor/tenant/Project/line/UUID scope and receipt integrity | Same commands file, `read_asset_review_receipt`; no `workbench:read` requirement |

The role seed [7519c3d1f364](../../backend/alembic/versions/7519c3d1f364_create_identity_baseline.py) contains no Workbench permissions. [RBAC-001 migration e2f3a4b5c6d7](../../backend/alembic/versions/e2f3a4b5c6d7_grant_standard_operator_workbench_edit.py) adds exactly `workbench:edit` for `owner`/`appraiser`. A bounded search of the migration chain found no `workbench:open`, `workbench:read` or `workbench:undo_redo` grant. [RBAC-001 PostgreSQL test](../../backend/tests/test_g1_rbac_001_postgresql.py) proves the exact edit addition, unchanged other roles, endpoint denial/tenant isolation and provenance-preserving downgrade; it does not prove a session-open grant.

A read-only query of the already migrated synthetic A5 PostgreSQL database `issue81_acceptance` (Alembic head `a4b5c6d7e8f9`) corroborated:

| Standard role | `workbench:edit` | `workbench:open` | `workbench:read` | `workbench:undo_redo` | Proposed change |
| --- | --- | --- | --- | --- | --- |
| owner | Present | Absent | Absent | Absent | Add open only, if accepted and separately implemented |
| appraiser | Present | Absent | Absent | Absent | Add open only, if accepted and separately implemented |
| admin | Absent | Absent | Absent | Absent | None |
| viewer | Absent | Absent | Absent | Absent | None |
| reviewer | Absent | Absent | Absent | Absent | None |
| knowledge_curator | Absent | Absent | Absent | Absent | None |

These are standard migrated role records, not a claim that every deployed account has identical effective permissions. [rbac.py](../../backend/app/core/rbac.py) derives the union of active, non-revoked roles for an active user/organization and requires exact permission membership. There is no admin-name or wildcard shortcut. Existing admin grants and behavior remain unchanged; an account with another separately accepted grant is evaluated normally. Non-operator standard roles alone remain denied session creation and A4 mutation.

## 3. Read and undo/redo are not minimum-path prerequisites

[useWorkbenchSession](../../frontend/src/components/workbench/session/useWorkbenchSession.ts) imports only `createSession` and `sendHeartbeat`. POST creation returns the session object; heartbeat returns its updated version. It never calls the exported GET `getSession`, whose server requires `workbench:read`.

[useWorkbenchStateSync](../../frontend/src/components/workbench/session/useWorkbenchStateSync.ts) calls only POST `saveLayout`, `saveGridView`, `saveSelection` and `savePanelState` from [workbenchState.ts](../../frontend/src/api/workbenchState.ts). Existing [WorkbenchLayout](../../frontend/src/components/layout/WorkbenchLayout.tsx) uses selection POST on row selection. It does not call GET grid-view/selection/panel-state/notifications. Asset grid and draft-state reads use Project APIs; [useAssetLineContext](../../frontend/src/components/workbench/hooks/useAssetLineContext.ts) constructs context locally, without a Workbench read API.

Read-only inspection of the preserved, uncommitted A5 `frontend/src/api/assetReview.ts` and `frontend/src/components/workbench/asset-review/useAssetReview.ts` confirms its added calls are Case State GET, dedicated validation/review POST and exact command-receipt GET. They add no Workbench read or undo/redo call. These stopped files are not merged baseline authority or part of this candidate.

Undo/redo calls exist through explicit `handleUndo`/`handleRedo` → [useWorkbenchDraftSync](../../frontend/src/components/workbench/session/useWorkbenchDraftSync.ts) → undo/redo POST, which require `workbench:undo_redo`. They are not automatically invoked by session creation, heartbeat, row selection, validation, review or receipt recovery, and are not required for A5 Asset Review closure. Their availability is not promised by D1. Existing GET Workbench state APIs likewise remain denied without their distinct read permission. If a later required A5 path actually needs either permission, stop and report the exact call path rather than broadening D1.

## 4. One preferred Product Owner decision

**D1 — Grant the existing permission `workbench:open` to standard `owner` and `appraiser` ONLY via a future data-only migration. Keep the endpoint and all other grants unchanged.**

This enables operators to establish the owned session prerequisite for their already accepted edit-gated commands. It also enables the existing open-gated endpoint generally for those roles; it is not a new A5-only permission. It grants no new validation/review authority and does not bypass any command eligibility check.

Explicitly unaffected: `workbench:edit`, `workbench:read`, `workbench:undo_redo`, all other permissions, admin behavior, viewer/reviewer/knowledge_curator grants, tenant and Project checks, active session ownership, confirmation, version safety, receipt/replay and audit rules. Session endpoint permission remains `workbench:open`. No new permission name, role shortcut or later-stage authority is proposed. ASSET_WORKBENCH+ remains unauthorized.

Rejected alternatives:

- Frontend/session bypass, pre-created session or direct DB permission patch for E2E: substitutes an unauthorized fixture or client workaround for the product's enforced session authority and cannot certify the real operator path.
- Changing the endpoint from `workbench:open` to `workbench:edit`: changes existing permission semantics and weakens the separate session-open boundary instead of making the bounded role grant explicit.
- Granting open to all standard roles: adds unsupported capability to admin, viewer, reviewer and knowledge_curator.
- Granting read or undo/redo: no minimum-path dependency was found; these distinct capabilities require their own evidence and accepted authority.
- Treating RBAC-001 edit acceptance as an implicit open grant: contradicts its expressly bounded data-only grant.

## 5. Decision, implementation and rollback gates

If D1 is denied or pending, standard operator session creation remains 403 and A5 browser closure remains blocked. No administrator manual patch or fixture bypass is authorized to complete acceptance.

Product Owner acceptance would freeze the bounded policy only. A separately authorized runtime task must implement and certify the future data-only migration, preserving unrelated grants and pre-existing accepted grants, with durable grant provenance and safe downgrade. This proposal creates no migration and changes no RBAC record, backend authentication, API, frontend, runtime or test behavior. No A5 worktree changes or browser E2E were performed; acceptance alone does not certify A5 or authorize ASSET_WORKBENCH+.

A future rollback should remove only the open grants introduced by that migration, retaining independently pre-existing accepted grants and all other permissions. Losing effective open denies subsequent session-create calls, including retrieval through that POST. It does **not** itself close existing active sessions or revoke edit: current heartbeat, A4 commands and receipt recovery still evaluate their own effective edit and active owned-session checks. Session revocation or altered authorization semantics require separate accepted authority; do not claim rollback automatically revokes active sessions.

This HIGH-risk docs-only candidate requires a frozen HEAD, DeepSeek and Gemini read-only reviews of that same HEAD, zero unresolved material P0–P3 and exact-head CI SUCCESS. Gate Owner retains Draft integration control; no Ready transition or merge is authorized.

PRODUCT OWNER DECISION REQUIRED: YES
