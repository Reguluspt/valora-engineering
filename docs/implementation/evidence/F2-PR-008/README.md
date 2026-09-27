# F2-PR-008 OS-G0 visual closeout evidence

Baseline: integration `4d32224ea31191e9f752ad5d848278da4f3e23d7`, exact-head CI #477 / run 36237349702 (success).

The screenshots were captured in the Codex in-app browser at 1280 × 720 against the local `browser-acceptance-server.mjs` fixture and the F2-PR-008 Vite frontend. The fixture uses acceptance-only records and provider responses; no live Microsoft activity occurred. The browser route and fixture state were checked before each capture. The viewport shows a desktop layout; long pages and horizontally scrollable tables continue beyond the screenshot edge.

| Scenario | Screenshot | Browser finding |
| --- | --- | --- |
| Login/auth shell | `01-login.jpg` | Vietnamese login and light shell. |
| Project list | `02-project-list.jpg` | Single fixture project and current navigation. |
| Case Overview | `03-case-overview.jpg` | 16-stage case projection with contextual next action. |
| Workbench normal | `04-workbench.jpg` | Light dense asset table; no standalone queue navigation. |
| Workbench contextual drawer | `05-workbench-drawer.jpg` | Asset context stays inside Workbench. |
| Workbench draft conflict | `06-workbench-conflict.jpg` | Fixture 409 preserves local draft and presents one update action. |
| NCC Selection | `07-ncc-selection.jpg` | Table of six acceptance fixture lines. |
| NCC warning drawer | `08-ncc-warning-drawer.jpg` | Existing quote warnings and candidate detail. |
| Document Workspace | `09-document-workspace.jpg` | Parent title “Không gian tài liệu”; Word Save explicitly non-authoritative. |
| Provider contextual state | `10-provider-limited.jpg` | OneDrive named only as account/source context; limited rights explained. |
| Loading | `11-loading.jpg` | Vietnamese loading state. |
| Empty | `12-empty.jpg` | Vietnamese first-use empty state, no invented records. |
| Error/retry | `13-error-retry.jpg` | One primary “Thử lại” recovery action. |
| Permission denied | `14-permission-denied.jpg` | No unauthorized document contents or action. |
| Keyboard focus | `15-keyboard-focus.jpg` | `:focus-visible` true; keyboard-focused “Thử lại” button has a white 2 px plus blue 4 px box-shadow ring. This image differs from the unfocused error state in `13-error-retry.jpg`. |

The UI retained contextual validation labels and legitimate domain review states. The retired Review Queue demo and dev entry are absent from the production source and package scripts. `/queue`, `/validation`, `/workbench/queue`, and `/workbench/validation` remain forbidden constants, never registered app routes.

The focus capture was repeated after Reviewer B found that the first `15-keyboard-focus.jpg` duplicated `12-empty.jpg`. The repaired screenshot shows focus on the recovery button and was checked against both empty and unfocused error images. No production code changed during this correction.

Validation before snapshot: focused tests passed (11 suites, 104 tests); TypeScript lint passed; full frontend tests passed (36 suites, 215 tests); production build passed; npm audit reported zero vulnerabilities; `git diff --check` passed. The two removed suites belonged solely to the retired demo and retired Review Queue component. Existing route, shell, i18n, Workbench, NCC, Document Workspace and visual-system suites remain green.

Worker note: Gemini 3.8 Flash High was attempted twice with an exact file allowlist. The first request failed at the provider credit gate before any read or edit; the second reached read-only inspection and then failed at the same credit gate before an edit. Codex completed the bounded edits and inspected the diff. No permission prompt was encountered or approved.
