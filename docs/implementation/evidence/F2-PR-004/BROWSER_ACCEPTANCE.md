# F2-PR-004 browser acceptance evidence

Captured on 2026-09-24 with the Codex in-app Browser at a 1280 × 720 desktop viewport. The app ran at `http://localhost:5173/` against the repository's existing acceptance fixture at `http://localhost:8000/`. The UI and fixture source under test was `afbaf523876ac106d8da0837e623b68eb00f6f94`. These are browser screenshots of fixture data; no product or domain data was changed.

## Case Overview

| Scenario | Browser result | Evidence |
| --- | --- | --- |
| Normal | Light canvas, one primary Next Action, 1/16 complete and 12 unavailable; all 16 stages retain the server order. | [Top](case-overview-normal.png) · [Stages and issue sections](case-overview-normal-detail.png) |
| Blocking | One blocker, blocked stage label, no invented action route or primary CTA. | [Top](case-overview-blocking.png) · [Blocker section](case-overview-blocking-detail.png) |
| Warning | One warning remains separate from blockers and stale entries. | [Top](case-overview-warning.png) · [Warning section](case-overview-warning-detail.png) |
| Stale | One `SOURCE_STALE` fixture entry appears in the separate review count and section. | [Top](case-overview-stale.png) · [Stale section](case-overview-stale-detail.png) |
| Loading | Skeleton appears while the fixture delays the Case State response. | [Loading](case-overview-loading.png) |
| Error | Explicit error and `Tải lại trạng thái`; retry fetched the restored normal projection. | [Error](case-overview-error.png) |
| Unavailable | Four prefix stages complete; 12 later stages unavailable; Next Action states that the next source is unavailable, without inventing a route. | [Unavailable](case-overview-unavailable.png) |

The browser DOM contained exactly one `[data-primary-action="true"]` in the normal scenario and 16 `[data-case-stage]` rows in canonical server order. The primary action navigated to `/workbench/projects/project-acceptance` through both click and keyboard Return. The fixture does not serve the asset-workbench APIs, so the destination's data error is outside this screen acceptance.

The PR01 runtime has no authoritative stale provider. The stale API fixture is synthetic UI coverage for the existing `stale` response field; these screenshots do not claim production stale detection.

## Project List

| Scenario | Browser result | Evidence |
| --- | --- | --- |
| Populated | Compact table, project identity and description, separate `Không gian tài liệu` and `Mở tổng quan` actions. | [Populated](project-list-populated.png) |
| Loading | Explicit loading state before the delayed response. | [Loading](project-list-loading.png) |
| Empty | First-use empty message for zero projects, distinct from error. | [Empty](project-list-empty.png) |
| Error | Explicit error and `Thử lại`; retry fetched the restored populated list. | [Error](project-list-error.png) |

`Mở tổng quan` navigated to `/workbench/projects/project-acceptance/overview`; `Không gian tài liệu` navigated to `/workbench/projects/project-acceptance/documents`. The two row actions exposed button semantics in the accessibility tree. Keyboard Tab showed a visible Fluent focus ring on `Mở tổng quan`, and Return activated the route. [Focus evidence](project-list-keyboard-focus.png).

## Visual and accessibility sanity

- The browser showed a Fluent 2 light canvas, compact Project List table, two-column Case Overview, Vietnamese labels, and one primary action where the server provided a valid route. No dark/cyan/glass foundation was observed in these screens.
- Blocking, warning and stale states used separate labeled counts and sections; meaning was conveyed by text as well as color. Loading, empty, error and unavailable states remained distinct.
- Headings, table, links and buttons were exposed in the accessibility tree. Visible keyboard focus and keyboard activation were verified. This is a browser sanity check, not a formal WCAG audit.
- No source code, backend, migration, provider runtime or second screenshot framework was changed for this evidence pass.
