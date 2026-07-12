# S12-R-005 — Dynamic Project Context & Live Workbench Data Integrity Audit

## Status
`PRE-PR EVIDENCE COMPLETE — AWAITING DRAFT PR AND CI`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `e68375756f3ad591889e919bca9de7ac277f1dea` |
| Branch | `s12-r-005-dynamic-project-context-live-data-integrity` |
| Original implementation SHA | `f533eee02fc11545ec1d906c4dfca588b8cb3386` |
| Previous audit SHA | `77f5e9a4c546ea45662bb5c29509bbaeb253d14a` |
| Corrective implementation SHA | `94b8030dda5bd8d7af39a4796439549905256bef` |
| Corrective audit SHA | `16c6a61f0457bd3ef51478f56c4fc8753aef79cb` |
| Micro-corrective code SHA | `c6a1e403c8b40131f792dcc55992306a085c70bd` (Commit E) |
| Micro-corrective audit SHA | `dc5854ca6812d9f6782fb5d6f0a7ee6562504a34` (Commit F) |
| Coverage pass code SHA | `4a140fcb8d25662687a3f44c8603d0948035f9f5` (Commit G) |
| Coverage pass audit SHA | `ee176d86bfc9ca1a0896ef3a03a551e47550ba2f` (Commit H) |
| Behavioral proof code SHA | `1ae4816f08cf375f047bd54b58e36ddf59ba0954` (Commit I) |
| Behavioral proof audit SHA | `a31e4c0652e5519eb54e3dc9207ad0e4bb9d24b9` (Commit J) |
| Session/pagination proof code SHA | `da24172478afa44cc36bcbd0e93db61b99fd61ae` (Commit K) |
| Session/pagination proof audit SHA | `16d8b6930d4e426bd94f5ece52276a1f925bea6b` (Commit L) |
| Correction code SHA | `e0ae061d0def93f55244b6f4d60da3c4b093401f` (Commit M) |
| Correction audit SHA | `62bd2762d214a275c0d0da4e0a97c5b7abc13bb5` (Commit N) |
| Draft PR | NOT CREATED |
| CI | PENDING |
| Branch ahead/behind | 14 commits ahead, 0 behind main |
| Net changed paths | 36 files (+1735 / -954) |

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
| `00000000-0000-0000-0000-000000000000` | `useWorkbenchSession.ts` (runtime API call) | 1 | 0 |
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
| Context drawer panels | Fabricated specs, quotes, lineage, validation | All `null` (unknown state) |

## Security Baseline Changes
- **S12R-SESSION-001** (all-zero UUID): RESOLVED — removed from `TEMPORARY_BASELINE`; fail-closed blocker added to `CRITICAL_BLOCKERS`
- **S12R-ROUTING-001** (hd-98-gia-lai): RESOLVED — removed from `TEMPORARY_BASELINE`; fail-closed blocker added to `CRITICAL_BLOCKERS`
- Static scan confirms 0 runtime occurrences of both patterns

## Quality Gate Results

| Gate | Result |
|---|---|
| Backend ruff | PASS |
| Backend pytest | 322 passed, 4 skipped, 0 failed |
| Security scanner | PASS (fail-closed critical blockers enforced) |
| Alembic heads | PASS (single: `db5977424e7b`) |
| Worker ruff | PASS |
| Worker pytest | 1 passed |
| Frontend lint | PASS |
| Frontend build | PASS |
| Frontend vitest | **80 passed (15 test files)** |
| npm audit | 0 vulnerabilities |

### Skipped Tests
4 PostgreSQL-gated (local dev): `test_auth_endpoints.py:737`, `test_s12_r_004_official_mutation.py:1049`, `test_workbench_api.py:696`, `test_workbench_api.py:980`
SKIPPED — REQUIRES CI WITH POSTGRESQL

## Final Test Inventory (80 tests)

| File | Tests | Type |
|---|---|---|
| `useResolvedProject.test.tsx` | 8 | Resolver lifecycle/race |
| `useWorkbenchSession.lifecycle.test.tsx` | 10 | Session lifecycle/race/heartbeat |
| `useProjectAssetLines.lifecycle.test.ts` | 12 | Pagination lifecycle/race/dedup/concurrency |
| `AppShell.route.test.tsx` | 2 | Routing |
| `AssetGrid.statusLabels.test.tsx` | 4 | Vietnamese display labels |
| `validators.test.tsx` | 5 | UUID validation unit |
| `useProjectAssetLines.test.ts` | 10 | Pure mapping + version parsing |
| `useAssetLineContext.test.ts` | 2 | Context null panels |
| `useWorkbenchDraftSync.test.ts` | 3 | Draft sync hooks |
| `useWorkbenchDraftState.test.ts` | 2 | Draft state |
| `projects.test.ts` | 2 | API serialization |
| `client.test.ts` | 7 | API client |
| `i18n.test.ts` | 4 | Translation keys |
| `AssetGrid.commit.test.tsx` | 4 | Commit confirmation |
| `errorRegistry.test.ts` | 5 | Error mapping |
| **Total** | **80** | |

Additional backend security-blocker test:
- `test_check_security_blockers.py`: 3 tests (PASS)

## Test Type Distinctions
- **Pure mapping/version parsing:** `useProjectAssetLines.test.ts` — 10 tests
- **Resolver lifecycle/race:** `useResolvedProject.test.tsx` — 8 tests
- **Session lifecycle/race/heartbeat:** `useWorkbenchSession.lifecycle.test.tsx` — 10 tests
- **Pagination lifecycle/race/dedup/concurrency:** `useProjectAssetLines.lifecycle.test.ts` — 12 tests
- **Routing:** `AppShell.route.test.tsx` — 2 tests
- **Vietnamese display labels:** `AssetGrid.statusLabels.test.tsx` — 4 tests
- **WorkbenchLayoutInner project isolation:** `key={projectId}` — independently reviewed code evidence; no dedicated automated test

## Micro-Corrective Finding Disposition

| Finding | Resolution | Evidence |
|---|---|---|
| F-1: Security scanner weakened | Added 2 fail-closed critical blockers to `CRITICAL_BLOCKERS`; 3 security-blocker tests | Security scan blocks reintroduction |
| F-2: All-zero UUID runtime literal | Created shared `isValidProjectUuid()` validator using regex `^0{32}$`; no hyphenated zero UUID literals remain | Static scan 0 occurrences; 5 validator tests |
| F-3: Hardcoded role/org | Removed role/organization footer from AppShell | AppShell no longer renders fabricated identity |
| F-4: Fabricated workflow status | Made status/statusLabel optional in WorkbenchHeader; removed hard-coded values; made issuesCount nullable in WorkbenchFooter | No fabricated draft/issue claims |
| F-5: Fabricated context drawer entities | Removed ALL fabricated specs, decisions, versions; useAssetLineContext returns null for all panels | All panels show truthful unavailable states |
| F-6: False validation conclusion | Changed validation page to neutral "Chưa có dữ liệu kiểm tra" | No false PASS claims |
| F-7: Route preservation | AppShell Workbench nav preserves active project route; neutral route navigates to /workbench/projects | 2 routing tests PASS |
| F-8: Pagination correctness | project generation guard; stale response rejection; consumed API offset; dedup via set; offset-based line_no; concurrent loadMore protection; immediate project-change reset; retry reset | 10 pure mapping tests + 12 lifecycle/race tests |
| F-9: Session correctness | project generation guard; session/sessionRef clearing; invalid-project fail-closed; stale createSession rejection; heartbeat interval cleanup; stale heartbeat rejection; unmount cleanup | 10 session lifecycle tests |
| F-10: Vietnamese labels | Translated all grid headers, toolbar selects, placeholders, disabled buttons; added `workbench.requiresBackendSession` key | 4 status-label tests; no English in main Workbench UI |
| F-11: Strict version parsing | Replaced `parseInt` with regex `^[1-9]\d*$` + `Number.isSafeInteger`; no trim, no silent conversion | Table-driven test covers invalid cases |
| F-12: Null price | Changed `?? 0` to pass-through null in AssetGrid draft editing; legitimate zero preserved | Mapping test covers null and zero |
| F-13: Unused import | Removed `useResolvedProject` import from App.tsx | Build/lint PASS |
| F-14: Audit document | Final reconciliation: full SHA lineage, final 80-test inventory, corrected pagination/session evidence, PostgreSQL CI limitation, exact cumulative scope | This document |

## Out of Scope
- S12-R-006: Excel parser hardening
- S12-PR-003: Validation Engine
- Backend API or database model changes
- No R004 tracked changes
- No runtime dependency changes (react-test-renderer@18.3.1 added as dev-only behavioral-test dependency; package-lock contains only that package + 3 transitive packages; zero npm audit vulnerabilities)
- Deleted mock files remain deleted

## Final Verdict
```text
PRE-PR EVIDENCE COMPLETE — AWAITING DRAFT PR AND CI
```
