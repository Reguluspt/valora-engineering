# VALORA Operational Frontend + OneDrive Personal — Browser Acceptance Closeout

**Status:** PASS ON LOCAL SIMULATED PROVIDER — UNMERGED CANDIDATE
**Date:** 2026-09-13
**Branch:** `feat/operational-frontend-m365`
**Base:** `6af3c86`

**Historical evidence note:** This closeout is immutable functional/browser evidence for the 2026-09-13 operational-frontend snapshot. Later Draft PR #32 work added Local G6, G8 Exchange and authority reconciliation. It is **not current visual acceptance**: the historical dark/Astryx presentation conflicts with the current Microsoft Fluent 2 light authority. Do not read the residual limitations below as current branch/product status; use the feature/acceptance matrix, UI/UX Handoff v2.3 and Unified Roadmap for present truth.

## Scope

This closeout covers the operational frontend entry added after PR-06: login/session restoration,
account and organization context, real project selection, OneDrive Personal connection status,
provision/adopt selection, callback return, canonical document list and revalidation presentation.

The browser fixture is explicitly simulated and local. It does not replace the live OneDrive Personal
provider evidence already retained by PR-05/PR-06, and it is not evidence of a Microsoft Graph write.
No sync/conflict runtime or Graph write exists in this candidate.

## Harness

- frontend: Vite at `http://localhost:5173`;
- API fixture: `frontend/scripts/browser-acceptance-server.mjs` at `http://localhost:8000`;
- data: fictional local account, organization, project, template, folder, DOCX and readiness facts;
- browser: Codex in-app browser with console warning/error capture.

The fixture implements only the API boundary needed to exercise the browser flow. It stores no real
credentials and makes no Microsoft request.

## Scenarios passed

### Desktop — 1440 × 900

1. Initial session loading resolved to the login screen without protected-content flash.
2. Login restored account name, email, organization, roles and permissions from `/me`.
3. The project route rendered a real API-backed project list and opened the selected project.
4. The OneDrive workspace rendered the active Personal connection and capability-aware actions.
5. Folder navigation listed only bounded folders and DOCX entries.
6. Template, DOCX and title selection submitted the server-issued adoption snapshot unchanged.
7. The canonical document list updated from one to two documents after adoption.
8. Explicit revalidation changed the fixture result to `EXTERNAL_CHANGE_OUTSIDE_MANAGED`; UI copy
   correctly stated that this is not a conflict by default.
9. `#/workbench/m365/return?m365=connected` fetched server connection status and rendered the safe
   callback result without OAuth state, code, token or provider identifiers.
10. The document card followed the server `next_action`/`recovery_code` and exposed exactly one
    primary recovery action for the active readiness state.

### Laptop — 1024 × 768

1. Project-list hierarchy and controls remained usable without horizontal clipping.
2. The three-column OneDrive workspace collapsed to the responsive stacked layout.
3. Logout cleared the account context and returned to the responsive login screen.

### Console closeout

Browser warning and error collections were empty at closeout.

## Corroborating automated evidence

```text
frontend npm run lint                                      PASS
frontend npm test                                          29 files / 137 tests PASS
frontend npm run build                                     PASS; no demo markers
frontend npm audit --audit-level=high                      PASS; 0 vulnerabilities
focused backend operational/PR-05/PR-06 pytest            72 passed
full backend pytest after runtime fixes                    1332 passed / 95 skipped
focused backend Ruff                                      PASS
Alembic heads                                              a6d9e4c2b8f1 (single head)
```

The full backend run completed before the final three test-only hardening cases were added; those
new cases are included in the final 72-test focused run. The 95 skipped tests are local
PostgreSQL/MinIO gates and are not claimed as PASS. Live-provider results are not restated as newly
run evidence because no live Microsoft account was used on this candidate.

## Residual limitations

- This branch is unmerged and has no exact-head CI result.
- Browser API behavior used a deterministic simulated provider, not a live Microsoft account.
- Callback navigation was exercised at the fixed frontend route; live Entra redirect behavior remains
  covered by backend tests and prior provider acceptance, not this local browser run.
- PR-07 sync/conflict remains contract-only and prohibited until owner acceptance.
