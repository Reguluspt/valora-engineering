# F2-PR-005 browser acceptance

Run on 2026-09-25 in the Codex in-app Browser against the repository's existing `browser:fixture` API and Vite at `http://localhost:5173/#/workbench/projects/workbench-acceptance`. The fixture account was `operator@valora.local` in `chi-nhanh-gia-lai`. These are fixture observations, not production data.

| Evidence | Observation |
| --- | --- |
| `01-workbench-grid.png` | Normal loaded grid, with no permanent right rail. |
| `02-active-asset-drawer.png` | Selecting asset line 1 opens its contextual drawer and shows its identity. |
| `03-price-evidence-section.png` | Price Evidence section is reachable in the selected asset context. The current context hook supplies no evidence data, so the section shows its truthful empty state. |
| `04-lineage-section.png` | Lineage section is reachable and shows the truthful empty state for this fixture. |
| `05-drawer-closed-selected-grid.png` | Closing the drawer restores focus to its trigger and keeps the active asset selected in the grid. |
| `06-inline-draft.png` | Editing a price with Enter leaves a visibly labeled local draft. The editor keeps focus when activated from the grid. |
| `07-draft-conflict.png` | A fixture 409 response shows the existing conflict warning and preserves the local draft. |
| `08-grid-loading.png` | Slow asset-line response shows a grid loading state. |
| `09-grid-error.png` | Failed asset-line response shows an error and a retry button. After switching the fixture to normal, clicking retry restored the grid. |
| `10-keyboard-focus.png` | Tab from the drawer close control moves visible keyboard focus to the first contextual section. |
| `11-saved-draft-apply-boundary.png` | A draft saved through the fixture API exposes a separate “Áp dụng nháp” action; no authoritative commit was performed during acceptance. The session stayed active after heartbeat. |

The normal fixture was restored after the loading, error, and conflict scenarios. The grid retained sorting, filtering, selection, virtualization, and the explicit apply confirmation path in focused tests. Browser inspection found no dark/glass foundation, cyan glow, or deprecated QC/reviewer/approval workflow in the active Workbench view.
