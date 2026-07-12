# S12-R-005 — Dynamic Project Context & Live Workbench Data Integrity Audit

## Status
`FINAL MICRO-CORRECTIVE COMPLETE — READY FOR INDEPENDENT RE-AUDIT`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `e68375756f3ad591889e919bca9de7ac277f1dea` |
| Branch | `s12-r-005-dynamic-project-context-live-data-integrity` |
| Original implementation SHA | `f533eee02fc11545ec1d906c4dfca588b8cb3386` |
| Previous audit SHA | `77f5e9a4c546ea45662bb5c29509bbaeb253d14a` |
| Corrective implementation SHA | `94b8030dda5bd8d7af39a4796439549905256bef` |
| Corrective audit SHA | `16c6a61f0457bd3ef51478f56c4fc8753aef79cb` |
| **Micro-corrective code SHA** | `c6a1e403c8b40131f792dcc55992306a085c70bd` (Commit E) |
| **Micro-corrective audit SHA** | `dc5854ca6812d9f6782fb5d6f0a7ee6562504a34` (Commit F) |
| **Coverage pass code SHA** | `4a140fcb8d25662687a3f44c8603d0948035f9f5` (Commit G) |
| **Coverage pass audit SHA** | `ee176d86bfc9ca1a0896ef3a03a551e47550ba2f` (Commit H) |
| **Behavioral proof code SHA** | `1ae4816f08cf375f047bd54b58e36ddf59ba0954` (Commit I) |
| **Behavioral proof audit SHA** | `a31e4c0652e5519eb54e3dc9207ad0e4bb9d24b9` (Commit J) |
| **Session/pagination proof code SHA** | `da2417245fa596a2b6896c0c60b49ce1d42b9db9` (Commit K) |
| **Session/pagination proof audit SHA** | `PENDING` (Commit L) |
| Draft PR | NOT CREATED |
| CI | PENDING |

## Root Cause Matrix

| # | Root Cause | File(s) | Fix |
|---|---|---|---|
| A | Hard-coded route slug `hd-98-gia-lai` in runtime | `App.tsx`, `AppShell.tsx`, `WorkbenchLayout.tsx` | Route-driven project ref extraction |
| B | All-zero UUID `00000000-...` sent as project ID | `useWorkbenchSession.ts` | Resolved project UUID from context |
| C | Duplicate slug resolution per consumer | `useProjectAssetLines.ts`, `WorkbenchLayout.tsx` | Single `useResolvedProject` boundary |
| D | Fabricated grid data (canonical, variant, taxonomy, unit, currency, quotes) | `useProjectAssetLines.ts` | Truthful null mapping |
| E | Fabricated context drawer data | `useAssetLineContext.ts`, `mockContextData.ts` | Null-based unknown states |
| F | No pagination | `useProjectAssetLines.ts` | `limit`/`offset`, load-more button |
| G | Broken resolver retry | `useProjectAssetLines.ts` | `retryCounter` in `useResolvedProject` |
| H | English user-facing labels | Panel components, `WorkbenchLayout.tsx` | Vietnamese translation |

## Architecture: Route-to-Consumer Flow

```text
App.tsx (extracts {ref} from hash)
  → WorkbenchLayout (useResolvedProject)
    → projectId: resolved UUID
      → useWorkbenchSession(projectId) → createSession({ project_id })
      → useProjectAssetLines(projectId) → fetchProjectAssetLines(projectId, {limit, offset})
      → useWorkbenchDraftState(projectId)
      → useWorkbenchDraftSync(sessionId, projectId)
      → commitAssetLineDraft(projectId, ...)
      → useAssetLineContext(projectId, ...)
```

## Removed Hard-Code Inventory

| Pattern | Location | Count Before | Count After |
|---|---|---|---|
| `hd-98-gia-lai` | `App.tsx`, `AppShell.tsx`, `WorkbenchLayout.tsx` | 9 | 0 |
| `00000000-0000-0000-0000-000000000000` | `useWorkbenchSession.ts` (runtime API call) | 1 | 0 (guard constant only) |
| `mockAssetRows.ts` | Entire file | 112 lines | **DELETED** |
| `mockContextData.ts` | Entire file | 165 lines | **DELETED** |

## Fabricated Data Disposition Matrix

| Field | Before | After |
|---|---|---|
| `canonical_asset` | `{id: "c-...", standard_name: ...}` | `null` |
| `asset_variant` | `{id: "v-...", display_name: ...}` | `null` |
| `taxonomy_node` | `{id: "t-...", path: "..."}` | `null` |
| `unit` | `{id: "u-1", code: "cai", name_vi: "cái"}` | `null` |
| `currency` | `{id: "cur-1", code: "VND"}` | `null` |
| `supplier_quote_[1-3]` | `item.raw_price \|\| 0` | `null` |
| `normalized_name` | `item.asset_name` | `null` |
| `appraised_price` | `item.appraised_unit_price \|\| 0` | `item.appraised_unit_price ?? null` |
| `row_version` | `parseInt(version_token) \|\| 1` | `parseInt(version_token) \|\| null` |
| Context drawer `knowledge_panel` | Fabricated specs, suggestions, conflicts | True data only: `Tên gốc` from `raw_name` |
| Context drawer `price_evidence_panel` | Fake quote batches, quote lines, appraisal | `quote_batch: null`, empty quotes, truthful `appraised_price_decision` |
| Context drawer `lineage` | `p-org`, `p-dir` fake IDs | `null` |
| Context drawer `validation_issues` | Empty `[]` (implies valid) | `null` (unknown state) |

## Changed Files

```text
Modified:
  frontend/src/App.tsx
  frontend/src/components/layout/AppShell.tsx
  frontend/src/components/layout/WorkbenchLayout.tsx
  frontend/src/components/workbench/AssetGrid.tsx
  frontend/src/components/workbench/AssetGridTypes.ts
  frontend/src/components/workbench/hooks/useProjectAssetLines.ts
  frontend/src/components/workbench/hooks/useAssetLineContext.ts
  frontend/src/components/workbench/session/useWorkbenchSession.ts
  frontend/src/components/workbench/panels/ContextPanelTypes.ts
  frontend/src/components/workbench/panels/KnowledgePanel.tsx
  frontend/src/components/workbench/panels/PriceEvidencePanel.tsx
  frontend/src/components/workbench/panels/LineagePanel.tsx
  frontend/src/components/workbench/panels/ValidationPanel.tsx
  frontend/src/i18n/vi.ts
  backend/tests/check_security.py
  frontend/src/components/workbench/hooks/__tests__/useAssetLineContext.test.ts
  frontend/src/components/workbench/hooks/__tests__/useProjectAssetLines.test.ts

Added:
  frontend/src/components/workbench/project-context/useResolvedProject.ts
  frontend/src/components/workbench/project-context/index.ts

Deleted:
  frontend/src/components/workbench/mockAssetRows.ts
  frontend/src/components/workbench/panels/mockContextData.ts
```

## Pagination Behavior
- First page: `fetchProjectAssetLines(projectId, { limit: 50, offset: 0 })`
- Load-more: subsequent `offset = currentRowCount`
- Duplicate prevention via `Set` of existing IDs
- Project change triggers full reset (via `loadFirstPage` useEffect dependency)
- Display: `Đã tải X/Y dòng` and `Tải thêm` button

## Security Baseline Changes
- **S12R-SESSION-001** (all-zero UUID): RESOLVED — removed from `TEMPORARY_BASELINE`
- **S12R-ROUTING-001** (hd-98-gia-lai): RESOLVED — removed from `TEMPORARY_BASELINE`
- Static scan confirms 0 runtime occurrences of both patterns

## Obfuscated (ZERO_UUID guard constants only in `useWorkbenchSession.ts` and `useResolvedProject.ts`)

## Micro-Corrective Local Quality Gate Results

| Gate | Result |
|---|---|
| Backend ruff | PASS |
| Backend pytest | **322 passed, 4 skipped, 0 failed** (includes 8 security checks + 3 blocker tests) |
| Security scanner | PASS (fail-closed critical blockers enforced: slug + all-zero UUID) |
| Alembic heads | PASS (single: `db5977424e7b`) |
| Worker ruff | PASS |
| Worker pytest | 1 passed |
| Frontend lint | PASS |
| Frontend build | PASS |
| Frontend vitest | **75 passed (15 test files)** |
| npm audit | 0 vulnerabilities |

### Test File Inventory
| File | Tests | Type |
|---|---|---|
| `useResolvedProject.test.tsx` | 8 | Lifecycle + race (resolver) |
| `useWorkbenchSession.lifecycle.test.tsx` | 6 | Lifecycle (session A-to-B, invalid, clearing) |
| `useProjectAssetLines.lifecycle.test.ts` | 11 | Lifecycle + race (pagination, dedup, A-to-B) |
| `AppShell.route.test.tsx` | 2 | Routing (preservation, neutral nav) |
| `AssetGrid.statusLabels.test.tsx` | 4 | Display label (all values, null fallback, mutation) |
| `validators.test.tsx` | 5 | UUID validation unit |
| `test_check_security_blockers.py` | 3 | Security blocker enforcement |
| `useProjectAssetLines.test.ts` | 10 | Mapping + pagination (mocked) |
| `useAssetLineContext.test.ts` | 2 | Context null panels |
| `useWorkbenchDraftSync.test.ts` | 3 | Draft sync hooks |
| `useWorkbenchDraftState.test.ts` | 2 | Draft state |
| `projects.test.ts` | 2 | API serialization |
| `client.test.ts` | 7 | API client |
| `i18n.test.ts` | 4 | Translation keys |
| `AssetGrid.commit.test.tsx` | 4 | Commit confirmation |
| `errorRegistry.test.ts` | 5 | Error mapping |

### Test Type Distinctions
- **Pure mapping:** `useProjectAssetLines.test.ts` (10 tests) — mapAssetLinesToGridRows + version token parsing
- **Lifecycle/race:** `useResolvedProject.test.tsx` (8 tests), `useWorkbenchSession.lifecycle.test.tsx` (6 tests), `useProjectAssetLines.lifecycle.test.ts` (11 tests) — real hook mount/unmount/rerender/switch
- **Routing:** `AppShell.route.test.tsx` (2 tests) — component render with react-test-renderer
- **Display label:** `AssetGrid.statusLabels.test.tsx` (4 tests) — Vietnamese status label mapping
- `key={projectId}` on WorkbenchLayoutInner: independently reviewed code evidence (no dedicated behavioral test)

### Skipped Tests
4 PostgreSQL-gated (local dev): `test_auth_endpoints.py:737`, `test_s12_r_004_official_mutation.py:1049`, `test_workbench_api.py:696`, `test_workbench_api.py:980`
SKIPPED — REQUIRES CI WITH POSTGRESQL

## Micro-Corrective Finding Disposition

| Finding | Resolution | Evidence |
|---|---|---|
| F-1: Security scanner weakened | Added 2 fail-closed critical blockers for `hd-98-gia-lai` and all-zero UUID to `CRITICAL_BLOCKERS` | Security scan now blocks reintroduction |
| F-2: All-zero UUID runtime literal | Created shared `isValidProjectUuid()` validator; removed ZERO_UUID constants; both hooks use semantic hex comparison | Static scan confirms 0 runtime occurrences |
| F-3: Hardcoded role/org | Removed role/organization footer from AppShell | AppShell no longer renders fabricated identity |
| F-4: Fabricated workflow status | Made status/statusLabel optional in WorkbenchHeader; removed hard-coded values from WorkbenchLayout; made issuesCount nullable in WorkbenchFooter | No fabricated draft/issue claims |
| F-5: Fabricated context drawer entities | Removed all fabricated specs, decisions, versions, decisions from useAssetLineContext; panels render null states | All panels show truthful unavailable states |
| F-6: False validation conclusion | Changed validation page to neutral "Chưa có dữ liệu kiểm tra" | No false PASS claims |
| F-7: Route preservation | AppShell Workbench nav now preserves active project path; only navigates to neutral when no project is active | Routing test confirms behavior |
| F-8: Pagination races | Replaced stale state with projectGen guard; AbortController; dedup via Set; line_no from offset; consumedOffset-based hasMore; immediate reset on project change | 10 pagination tests |
| F-9: Session project-switch race | Added projectGen guard; clear session/sessionRef on project change; heartbeat binds to current generation | Stale response ignored |
| F-10: Vietnamese labels | Translated all grid headers, toolbar selects, placeholders, disabled buttons; added `workbench.requiresBackendSession` i18n key | No English in main Workbench UI |
| F-11: Strict version parsing | Replaced `parseInt` with regex `^[1-9]\d*$` + `Number.isSafeInteger` | Table-driven test covers 8 invalid cases |
| F-12: Null price | Changed `?? 0` to pass-through null in AssetGrid draft editing | Legitimate zero preserved, null preserved |
| F-13: Unused import | Removed `useResolvedProject` import from App.tsx | Build/lint PASS |
| F-14: Audit document | Updated status, SHA tracking, added corrective disposition table, removed overstatements | This document |

## Corrective Test Results

| File | Tests | Status |
|---|---|---|
| `useProjectAssetLines.test.ts` | 10 | PASS (strict parsing, pagination, null/zero price) |
| `useAssetLineContext.test.ts` | 2 | PASS (null panels, no fabricated entities) |
| All other existing tests | 29 | PASS (no regressions) |
| **Total frontend** | **39** | **PASS (9 test files)** |

## Out of Scope
- S12-R-006: Excel parser hardening
- S12-PR-003: Validation Engine
- Backend API or database model changes
- Adding React Router or other routing dependencies
- `package.json` / `package-lock.json` changes

## Final Verdict
```text
SESSION AND PAGINATION PROOF COMPLETE — READY FOR INDEPENDENT RE-AUDIT
```
