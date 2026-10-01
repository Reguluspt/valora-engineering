# VF0 visual fidelity implementation evidence

Task: `VALORA-TASK-OS-G1-VF0-FRONTEND-VISUAL-FIDELITY-ALIGNMENT`

This is a working implementation audit, not design or domain authority. Baseline: `origin/main` `181c48ce007d8885c49c0dbd52040a38fbaf8cec`, exact-head CI #518 SUCCESS. Approved image files live in [`../design/visual-reference/v2.3/README.md`](../design/visual-reference/v2.3/README.md).

## VF1 initial audit, before presentation edits

| Current production surface | Visual authority | Current implementation | Major visual gap | VF0 action |
| --- | --- | --- | --- | --- |
| AppShell | `VISUAL_GRAMMAR_ONLY`; compare S10/S12 shell examples | Text-only Valora mark, flat route list, account block in sidebar, no top command/context layer | Weak product hierarchy, sparse navigation and large undirected content canvas | Done: compact grouped navigation and contextual header using real routes/account data |
| Project List / Workbench entry | `VISUAL_GRAMMAR_ONLY`; S12 shell/table grammar | Project list page in common shell | Shell and page density diverge from approved desktop app | Done: shared shell composition; existing search and route behavior preserved |
| S02 Quản lý yêu cầu sơ bộ | `VISUAL_GRAMMAR_ONLY` | Dedicated preliminary request queue | Generic panel/table presentation, limited visual hierarchy | Done: compact work queue with existing status and create action |
| S03 Tạo yêu cầu sơ bộ | `VISUAL_GRAMMAR_ONLY` | Bounded create form | Shared shell and form hierarchy are sparse | Done: shared Fluent field/action composition; creation remains simple |
| S04 Upload & Mapping Excel | `VISUAL_GRAMMAR_ONLY` | Sequential current-source/mapping page | Steps share similar large-card weight; current action and mapping grid need clearer emphasis | Done: compact completed context, dominant current task, section-local states |
| S05 Phân tích danh mục | `VISUAL_GRAMMAR_ONLY` | Editable and completed G1.1I table views | Generic panel/table, broad empty canvas around completed data, weak readiness context | Done: dense analysis workspace and intentional immutable result state |
| S10 Case Overview | `EXACT_VISUAL_BASELINE`; [Part 2B p. 3](../design/visual-reference/v2.3/baselines/s10-orchestration-hub-iteration-2-approved.png) | Backend Case State projection; summary tiles, vertical 16-row list, issue cards and rail | Approved hub has a horizontal stage strip, grouped progress, compact operational overview, balanced right rail | Done: aligned composition with current projection; unsupported mockup data omitted |
| S11 Asset Confirmation | `EXACT_VISUAL_BASELINE`; [Part 1 p. 13](../design/visual-reference/v2.3/baselines/s11-asset-confirmation-approved.png) | No dedicated current production S11 route in this VF0 scope | Screen baseline exists, runtime capability is not authorized by VF0 | Reference-only; no fake screen or route |
| S12 Workbench | `EXACT_VISUAL_BASELINE`; [Part 1 p. 14](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png) | Existing dense asset grid with workbench layout | Shared shell change could shift proportions or reduce grid space | Done: grid row/header geometry corrected with virtual offsets; browser regression checked |
| S13 Asset Context Drawer | `EXACT_VISUAL_BASELINE`; [Part 1 p. 15](../design/visual-reference/v2.3/baselines/s13-asset-context-drawer-approved.png) | Context panel within Workbench | Shared chrome must preserve S12 context when drawer opens | Done: browser regression checked with selected grid context visible |
| Workbench price/evidence context tab | `VISUAL_GRAMMAR_ONLY` for this existing tab; [Part 1 p. 16](../design/visual-reference/v2.3/baselines/price-evidence-approved.png) is the exact baseline for a separate approved full screen | Existing Workbench price/evidence panel | Shared chrome and panel density may differ; standalone capability is absent | Done: browser regression checked; fixture has no price/evidence records; no claim of whole-screen match |
| NCCQ | `EXACT_VISUAL_BASELINE`; [Part 1 p. 17](../design/visual-reference/v2.3/baselines/nccq-iteration-6-approved.png) | No full NCCQ surface in current VF0 production route set | Future capability gap, not a VF0 visual defect | Reference-only; no new NCC behavior |
| NCC Selection | `EXACT_VISUAL_BASELINE`; [Part 2B p. 2](../design/visual-reference/v2.3/baselines/ncc-selection-iteration-1-approved.png) | Table, KPI and detail drawer components | Shared shell and density could diverge from approved table-first composition | Done: drawer geometry corrected and browser regression checked |
| M365 Workspace / Return | Word return board is `EXACT_VISUAL_BASELINE` for its pattern; Workspace and OAuth callback are `VISUAL_GRAMMAR_ONLY` | Existing Workspace and OAuth callback route | Shared shell and state styling may drift | Done: browser regression checked; [Part 2B p. 8](../design/visual-reference/v2.3/baselines/m365-return-revalidation-iteration-1.png) retained for Word return |
| Cross-product states | `VISUAL_GRAMMAR_ONLY`; [Part 2B p. 6](../design/visual-reference/v2.3/baselines/cross-product-state-pattern-board-iteration-1.png) | Shared Loading, Empty, Error, status, conflict primitives and local variants | Inconsistent page/section state presentation | Done: shared shell/density applied; S04 409 visual regression captured without recovery semantic change |

S02–S05 have no approved exact whole-screen mockup in the supplied references. Their classification is deliberately `VISUAL_GRAMMAR_ONLY`.

## Candidate implementation and screenshot method

The candidate keeps all runtime API/domain work in the frontend. The shared shell now has a 216 px grouped navigation rail, a 44 px context bar, active route treatment, and the real signed-in account. It omits the mockup's global search and notification controls because this runtime has no corresponding behavior. S10 uses the existing Case State projection for its 16-stage strip, seven display groups keyed by canonical stage IDs, issue panels and next-action rail; absent activity and metrics remain truthful unavailable states. S02–S05 use the same compact header, status, table and action grammar without claiming an exact page mockup. S04 compresses completed steps when the mapping proposal is actionable. S05 shows real reviewed/total counts and keeps the finalized table read-only. The Workbench now shows a summary using the real total, loaded row and local draft counts. Its grid row geometry is 44 px, with its virtualization offsets updated together. The NCC drawer starts below the context bar.

Run `python frontend/scripts/capture-vf0-screenshots.py` with the local fixture API (`npm run browser:fixture`) and Vite (`npm run dev -- --host localhost`) running in `frontend/`. The script uses synthetic fixture data, a fixed browser clock and 1440×900 viewport; it adds 1920×1080 for S10. [The machine-readable manifest](vf0-screenshots/manifest.json) records the route, viewport, authority type and repository-local reference for every image. Captures contain no customer data. The fixture's small row set explains some unused canvas; it is not evidence of production dataset size.

## Region-level visual comparison

Verdicts apply to the **embedded approved screen**, not the surrounding PDF page. `MATCH` means the approved composition is present. `ACCEPTABLE_SEMANTIC_VARIATION` means real data or authorized capability differs while the region's layout is retained. `GAP` means an unresolved material visual difference. The checked exact-baseline captures have **0 material GAPs**.

| Exact surface; approved repository-local reference | Shell / header | Main / grid | Panel / CTA | Status / density | Verdict and variation |
| --- | --- | --- | --- | --- | --- |
| S10, [Part 2B p. 3, Orchestration Hub Iteration 2](../design/visual-reference/v2.3/baselines/s10-orchestration-hub-iteration-2-approved.png); [1440×900](vf0-screenshots/s10-overview-1440x900.png), [1920×1080](vf0-screenshots/s10-overview-1920x1080.png) | ACCEPTABLE_SEMANTIC_VARIATION: compact rail/context bar and case identity, without unbacked mockup identity facts | MATCH: horizontal 16-stage strip and left-group/right-issue composition | MATCH: right next-action rail and one real action | ACCEPTABLE_SEMANTIC_VARIATION: projection has no activity stream or mockup's extra metrics | ACCEPTABLE_SEMANTIC_VARIATION; backend Case State is the only stage/action authority |
| S12, [Part 1 p. 14, Workbench](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png); [1440×900](vf0-screenshots/s12-workbench-1440x900.png) | MATCH: shared shell and Workbench context | ACCEPTABLE_SEMANTIC_VARIATION: real-count summary, filter toolbar, 17-column virtualized grid and persistent status bar; latter columns need horizontal scrolling | ACCEPTABLE_SEMANTIC_VARIATION: drawer closed in this capture; row action opens it | MATCH: 44 px rows, visible scroll affordance and focus/status controls | ACCEPTABLE_SEMANTIC_VARIATION; actual API row schema cannot produce the mockup's richer column/KPI set |
| S13, [Part 1 p. 15, Asset Context Drawer](../design/visual-reference/v2.3/baselines/s13-asset-context-drawer-approved.png); [1440×900](vf0-screenshots/s13-asset-context-drawer-1440x900.png) | MATCH: Workbench shell remains visible | MATCH: selected row and grid context remain visible | MATCH: right drawer, asset heading, section actions and close control | ACCEPTABLE_SEMANTIC_VARIATION: fixture context has no Knowledge detail | ACCEPTABLE_SEMANTIC_VARIATION; no invented Knowledge content |
| NCC Selection, [Part 2B p. 2, Iteration 1](../design/visual-reference/v2.3/baselines/ncc-selection-iteration-1-approved.png); [drawer open](vf0-screenshots/ncc-selection-1440x900.png), [eligible quote selected and CTA visible](vf0-screenshots/ncc-selection-candidate-selected-1440x900.png) | MATCH: compact rail and visible context bar | MATCH: KPI row, search, table-first asset selection | MATCH: right drawer below context bar; primary commit CTA appears after explicit human quote selection | ACCEPTABLE_SEMANTIC_VARIATION: fixture has six rows and existing quote/commit semantics | ACCEPTABLE_SEMANTIC_VARIATION; the approved denser quote set is sample data |

S11, the standalone Price & Evidence screen, and NCCQ exact mockups are persisted in the [visual reference README](../design/visual-reference/v2.3/README.md), but no corresponding full production route is in the current VF0 runtime scope. The separate M365 Word return/revalidation board (Part 2B p. 8) is preserved as an exact state reference; the current OAuth callback screenshot is **not** presented as that screen.

## Grammar-only and state captures

| Surface and candidate | Repository-local grammar/reference | Viewport | Region check and verdict |
| --- | --- | --- | --- |
| [S02 management](vf0-screenshots/s02-management-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [S12 table grammar](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png) | 1440×900 | Shell, queue header, create action, status/table density: MATCH to shared grammar; one fixture row leaves valid empty canvas |
| [S03 create](vf0-screenshots/s03-create-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [S11 form grammar](../design/visual-reference/v2.3/baselines/s11-asset-confirmation-approved.png) | 1440×900 | Shell, bounded form, field hierarchy, primary/secondary action: MATCH to shared grammar |
| [S04 upload](vf0-screenshots/s04-upload-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [S12 workspace grammar](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png) | 1440×900 | Current batch/source, sequential steps, upload action: MATCH to shared grammar |
| [S04 mapping review](vf0-screenshots/s04-mapping-review-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [S12 workspace grammar](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png) | 1440×900 | Prior step compresses; proposal table and explicit human decision dominate: MATCH to shared grammar |
| [S05 editable](vf0-screenshots/s05-analysis-editable-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [S12 table grammar](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png) | 1440×900 | Real reviewed/total count, dense grid and actual confirmation/finalization controls: MATCH to shared grammar |
| [S05 completed](vf0-screenshots/s05-analysis-completed-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [S12 table grammar](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png) | 1440×900 | Compact finalized state, version and immutable table: MATCH to shared grammar |
| [S04 409 conflict](vf0-screenshots/s04-conflict-1440x900.png) | [Part 2B p. 6 State Pattern Board](../design/visual-reference/v2.3/baselines/cross-product-state-pattern-board-iteration-1.png) | 1440×900 | Warning remains near mapping decision; no blind retry or last-write-wins: MATCH to shared state grammar |
| [Workbench price/evidence tab](vf0-screenshots/price-evidence-1440x900.png) | [Part 1 p. 16 standalone exact screen](../design/visual-reference/v2.3/baselines/price-evidence-approved.png), [bundle scope note](../design/visual-reference/v2.3/README.md) | 1440×900 | Current Workbench context tab stays in the drawer and truthfully reports no fixture data: MATCH to shared panel grammar; not a whole-screen match claim |
| [M365 Workspace](vf0-screenshots/m365-workspace-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md), [Part 2B p. 8 state board](../design/visual-reference/v2.3/baselines/m365-return-revalidation-iteration-1.png) | 1440×900 | Existing workspace shell and state remain usable: MATCH to shared grammar |
| [M365 OAuth callback](vf0-screenshots/m365-oauth-return-1440x900.png) | [Global bundle classification](../design/visual-reference/v2.3/README.md) | 1440×900 | Separate connection callback has one real navigation action: MATCH to shared grammar; not the Word revalidation mockup |

The current shared `StateSurface` continues to distinguish initial/section loading, four empty variants, section/page error and single recovery action. Existing mutation state code retains old data during refresh, a visible 409 conflict, and partial-success content. This PR changes their surrounding visual density, not their recovery semantics. The state board is a visual reference for currently rendered state variants, not permission to create new states or API behavior.

No unresolved material visual GAP is recorded. Knowledge/Internet/Evidence runtime, absent mockup metrics, and unimplemented S11/NCCQ routes are deferred product capabilities outside VF0, not visual-fidelity defects.

## Initial independent review adjudication

The first frozen review at `8cf4adfd6af90d1262538f8e622d6e7206eb3d5e` produced the following actionable observations. That review is historical after these corrections; the final candidate requires **both** reviewers again on one new exact snapshot.

| Observation | Classification and resolution |
| --- | --- |
| S10 group progress was full-width beneath the stage strip, with only three positional groups | `VALID` visual/robustness: now a left progress panel beside stacked issue panels, with seven display groups keyed by canonical stage IDs rather than array slices |
| S10 exposed the raw Case State CAS token in the rail | `VALID` product UI: removed the technical token; the backend version remains available for API concurrency without being shown as a user metric |
| S12 lacked a summary region and did not explain right-side column overflow | `VALID` visual: added only real total/loaded/draft counts and a horizontal-scroll affordance; the current 17-column API grid remains scrollable and is documented as `ACCEPTABLE_SEMANTIC_VARIATION` |
| S13 tabs appeared in a 2×2 button grid unlike the approved drawer | `VALID` visual: changed to one horizontal, underlined tab row while retaining accessible full labels and existing panel behavior |
| Breadcrumb had an `aria-label` but no navigation landmark | `VALID` accessibility: now a named `nav` landmark; the primary nav and main landmark remain unique in their roles |
| Price & Evidence candidate appeared to omit the standalone approved screen | `OUT_OF_SCOPE` for the present Workbench context tab: the exact full-screen baseline remains persisted, but its full route/Internet/old-dossier capabilities are not in the current runtime; evidence now classifies the tab by visual grammar only |
| NCC drawer screenshot did not show a commit CTA | `INVALID` as a missing action: the accepted contract requires explicit eligible-quote selection before the CTA appears; a second screenshot now proves its visible selected state without committing |
| Native S04/S05 input controls and smaller fixture datasets differ from mockup samples | `ADVISORY`: existing accessible form controls and actual G1.1I data contract are retained; no fake data, unbacked workflow or custom upload behavior was added |

## Local acceptance gate

| Gate | Result |
| --- | --- |
| Focused development suites | Shell 11/11; S10 and Shell 16/16; Pre-case 55/55; Intake/Analysis 36/36; Workbench grid/context 8/8 before the final integrated gate |
| Full frontend suite | `npm test`: 42 files, 287 passed, 0 failed, 0 skipped |
| Typecheck and lint script | `npm run lint` (`tsc --noEmit`): PASS |
| Production build | `npm run build`: PASS; production bundle assertion PASS |
| Dependency audit | `npm audit --json`: 0 vulnerabilities |
| Whitespace | `git diff --check`: PASS before freeze |
| Deterministic browser acceptance | 16/16 synthetic captures succeeded; rerun produced identical SHA-256 for every PNG |
| Browser accessibility assertions | One main landmark and one named primary navigation on every capture; at most one `aria-current="page"`; S13 close control receives focus; NCC detail has a named dialog and focuses its close control |
| Backend tests | N/A; no backend runtime, persistence, migration or API file changed |

The first full suite run exposed one old Shell test that treated the management route as the current page during S03 create. The UI correctly leaves `aria-current` unset there; the assertion was corrected and the full suite reran green. The first focus assertion also tried to click the Workbench drawer trigger after selecting a row, although row selection had already opened the drawer. The harness now checks focus on the actual opening interaction. Neither issue changed domain behavior.

## Hard boundary

The candidate changes presentation and frontend test/harness files plus the status note in `CODEX.md`. It adds only non-canonical PDF/PNG references and implementation evidence under `docs/`. It contains no backend runtime, API, persistence, migration, G1.1J Result/Official Intake, Apply, ProjectAssetLine mutation, NCC domain, M365 domain or OS-G2 implementation change. Existing data and route contracts remain the source of screen content.
