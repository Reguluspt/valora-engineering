# S12-R-005 — Dynamic Project Context & Live Workbench Data Integrity Audit

## Status
`LOCAL IMPLEMENTATION COMPLETE — AWAITING DRAFT PR AND CI`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `e68375756f3ad591889e919bca9de7ac277f1dea` |
| Branch | `s12-r-005-dynamic-project-context-live-data-integrity` |
| Implementation SHA | `PENDING` (Commit A) |

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

## Local Quality Gate Results

| Gate | Result |
|---|---|
| Backend ruff | PASS |
| Backend pytest | 319 passed, 4 skipped, 0 failed |
| Security scanner | PASS (S12R-SESSION-001 + S12R-ROUTING-001 resolved) |
| Alembic heads | PASS (single: `db5977424e7b`) |
| Worker ruff | PASS |
| Worker pytest | 1 passed |
| Frontend lint | PASS |
| Frontend build | PASS |
| Frontend vitest | 36 passed (9 test files) |
| npm audit | 0 vulnerabilities |

Skipped: 4 PostgreSQL-gated (local dev, expected)

## Out of Scope
- S12-R-006: Excel parser hardening
- S12-PR-003: Validation Engine
- Backend API or database model changes
- Adding React Router or other routing dependencies
- `package.json` / `package-lock.json` changes

## Final Verdict
```text
LOCAL IMPLEMENTATION COMPLETE — AWAITING DRAFT PR AND CI
```
