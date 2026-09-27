# F2-PR-001 — Runtime Authority Ratchet & Legacy Route Removal

**Status:** MERGED ON INTEGRATION — PR #34 / `ae5239922b69f2208ee5fc64f70134dba2284605`
**Parent contract:** `VALORA-FLUENT2-REMEDIATION-001`
**Roadmap:** OS-G0
**Depends on:** documentation baseline only
**Blocks:** F2-PR-002+

## Objective
Make production routing/navigation reflect current v2.3 authority before visual migration starts.

## File manifest
| Action | File |
|---|---|
| MODIFY | `frontend/src/contracts/valoraV23.ts` |
| MODIFY | `frontend/src/contracts/__tests__/valoraV23.test.ts` |
| MODIFY | `frontend/src/App.tsx` |
| MODIFY | `frontend/src/components/layout/AppShell.tsx` |
| MODIFY | `frontend/src/components/layout/__tests__/AppShell.route.test.tsx` |
| MODIFY | `frontend/src/components/projects/ProjectListPage.tsx` |
| MODIFY | `frontend/src/components/projects/__tests__/ProjectListPage.test.tsx` |
| MODIFY | `frontend/scripts/assert-production-bundle.mjs` |
| KEEP DEMO-ONLY | `frontend/src/demo/**` |
| KEEP UNREACHABLE TEMPORARILY | `frontend/src/components/workbench/review/**` |

## Implementation
1. Replace `UIUX_V23_AUTHORITY` branch/tip fields with stable current-document identifiers, e.g. `master: "docs/design/VALORA_UIUX_HANDOFF_v2.3.md"` and `authorityIndex: "...AUTHORITY_INDEX.md"`. Do not pin authority to a superseded branch SHA.
2. Remove `legacyReviewQueue` and `legacyValidationDashboard` from `APP_ROUTES`. Remove `LEGACY_ROUTE_ALIASES` and `LEGACY_ROUTE_RATCHET`. Add the removed paths to the forbidden-route ratchet so they cannot be reintroduced.
3. Delete `ReviewQueueDashboard` production import/render branch from `App.tsx`; delete standalone validation-dashboard render branch. Old hashes fall through to the existing Vietnamese Not Found state; do not silently redirect them to another business capability.
4. Remove both legacy nav items from `AppShell.tsx`. Remove now-unused active-link helper/imports.
5. Rename project document parent labels to **`Không gian tài liệu`** in AppShell and Project List. Route remains `/documents`; this PR does not rename API/routes.
6. Strengthen `assert-production-bundle.mjs` with production-forbidden markers for legacy global Review Queue/Validation Dashboard demo identifiers without forbidding valid domain-local “review” terminology.
7. Keep `frontend/src/demo/**` as demo-only; production bundle must remain free of demo fixture markers.

## Tests
- Update route contract test: registered production routes contain neither `/workbench/queue` nor `/workbench/validation`.
- Static route literal scan remains green.
- AppShell test asserts no legacy nav labels and verifies `Không gian tài liệu` preserves project ref.
- ProjectList test expects `Không gian tài liệu`.
- Build assertion proves demo markers absent from production bundle.
- Existing overview/workbench/NCC/document routes unchanged.

## Must not change
Domain/API semantics, hash-router mechanism, M365 endpoints, Case State, NCC selection, Workbench behavior, review demo fixture history.

## DoD
No production navigation or route renders the two legacy global surfaces; current v2.3 authority metadata is stable; provider-neutral document parent label is used; focused tests + full frontend build/test pass.
