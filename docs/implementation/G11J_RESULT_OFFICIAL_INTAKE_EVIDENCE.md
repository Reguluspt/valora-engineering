# G1.1J Result and Official Intake candidate evidence

Task: `VALORA-TASK-OS-G1-1J-PRECASE-RESULT-OFFICIAL-INTAKE-UX`.

This is implementation evidence, not semantic or design authority. The source is the repository-local [v2.3 visual bundle](../design/visual-reference/v2.3/README.md). S09 is `VISUAL_GRAMMAR_ONLY_WITH_APPROVED_LAYOUT_CONTRACT`: [Part 1 PDF p. 4](../design/visual-reference/v2.3/VALORA_UIUX_Handoff_v2.3_RELEASE_CONFIRMATION_BASELINE_Part_1.pdf) describes the approved S09 information groups and transition behavior, but none of the three supplied PDFs contains an approved exact whole-screen S09 mockup. No new S09 baseline PNG was invented. The shared shell, compact panel hierarchy and state treatment were compared with [S10 Orchestration Hub Iteration 2, Part 2B p. 3](../design/visual-reference/v2.3/baselines/s10-orchestration-hub-iteration-2-approved.png), [S12 Workbench, Part 1 p. 14](../design/visual-reference/v2.3/baselines/s12-workbench-approved.png), and [Cross-product State Pattern Board Iteration 1, Part 2B p. 6](../design/visual-reference/v2.3/baselines/cross-product-state-pattern-board-iteration-1.png).

## Deterministic browser evidence

Run `python frontend/scripts/capture-g11j-screenshots.py` with `npm run browser:fixture` and Vite started with `VITE_API_BASE_URL=/` in `frontend/`. The script uses only synthetic fixture data, an explicit 1440×900 viewport, a fixed browser clock, and the actual UI actions for Result generation, file download, Customer selection/bind, and Official Intake. It then renders server-blocked and unavailable states. [The machine-readable manifest](g11j-screenshots/manifest.json) records each repository-local reference. Eight PNGs are 1440×900. The screen samples contain no production Customer information.

`MATCH` below means the region follows the applicable approved grammar/layout, not pixel parity with a nonexistent S09 image. `N/A` means a region is intentionally absent at that state. A GAP is a material unresolved visual difference within this task's authorized scope.

| Candidate state and screenshot | Shell | Header/context | Main content | Context rail | Primary CTA | Density/whitespace | State/error treatment | Material GAP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Result ready](g11j-screenshots/01-result-ready.png) | MATCH | MATCH: Project and 4-step status | MATCH: one current Result action | MATCH: readiness and real Project identity | MATCH: explicit generation | MATCH: short state leaves honest open canvas, with no synthetic controls | MATCH: no Result represented as pending work | 0 |
| [Result generated, Customer unbound](g11j-screenshots/02-result-generated.png) | MATCH | MATCH: Result version and unbound Customer | MATCH: immutable Result metadata/download and distinct Customer section | MATCH: warning separate from blocker | MATCH: Customer search becomes next step | MATCH: compact two-column hierarchy | MATCH: warning does not block binding | 0 |
| [Customer selected, unbound](g11j-screenshots/03-customer-selected.png) | MATCH | MATCH | MATCH: searchable master selection with one active fixture Customer | MATCH | MATCH: explicit bind action only after selection | MATCH: bounded result list | MATCH: unbound remains visible until commit | 0 |
| [Customer bound, Intake ready](g11j-screenshots/04-customer-bound.png) | MATCH | MATCH: bound Customer and Result version | MATCH: Result, Customer, freeze scope | MATCH: blocker 0, warning 1, optional S09 groups | MATCH: explicit Official Intake action | MATCH: compact stack and right rail | MATCH: warning remains non-blocking | 0 |
| [Official Intake confirmation](g11j-screenshots/05-intake-confirmation.png) | MATCH | MATCH: context remains behind modal | MATCH: names Project, Result version, Customer and freeze consequence | MATCH | MATCH: distinct final confirmation | MATCH: focused modal; surrounding context retained | MATCH: modal blocks accidental background action | 0 |
| [Open blocking issue](g11j-screenshots/06-blocking-issue.png) | MATCH | MATCH: stable S09 title and current stages | MATCH: readback remains available; Intake section names the blocking reason | MATCH: red blocking icon/status and separate amber warning; link to Case Overview for issue detail | N/A: Intake action withheld | MATCH | MATCH: blocking is visible at the action point and no automatic resolution occurs | 0 |
| [Official Intake committed](g11j-screenshots/07-intake-frozen.png) | MATCH | MATCH: stable S09 title and completed stage | MATCH: immutable Result, Customer and freeze statement | MATCH: optional S09 fields remain truthful | N/A: only navigation and immutable download | MATCH: compact read-only composition | MATCH: green success with icon; no mutation controls | 0 |
| [Result unavailable](g11j-screenshots/08-result-unavailable.png) | MATCH | MATCH: stage strip says unavailable | MATCH: distinct informational unavailable message | MATCH: no false Result-ready claim | N/A: generation withheld | MATCH: honest open canvas | MATCH: blue information state directs to Case Overview without guessing | 0 |

Every row uses the same S09 classification and the repository-local references linked above. The fixture contains one Customer and one Result, so its whitespace and data density are not a production dataset claim. The ready state deliberately has one small current-action panel because adding unsupported records, workflow actions or metrics would falsify the product.

## S09 information availability

Part 1 p. 4's 2A fields (appraised asset, purpose, note), 2B dates/numbers, 2C total/value-inclusion/fee, and liquidation fields are not jointly exposed by an accepted public S09 information contract. The current Project read supplies case code/name and some older Project fields, but it does not establish the whole S09 field set or an authorized S09 edit command. The candidate shows real Project code/name as identity, the current Result and Customer, and truthful `Chưa bổ sung tại bước này` for the optional 2B/2C groups. The accepted Official Intake command requires current Result, Customer, Project CAS and confirmation; it does not require these optional S09 fields. No unavailable field is fabricated or treated as an Intake blocker. Adding an S09 field/edit contract remains outside G1.1J.

## Local acceptance results

| Check | Result |
| --- | --- |
| Focused frontend model/page/route | Initially 3 files, 18 passed, 0 failed; latest page suite has 15 passed, 0 failed, including permission denial and Customer read degradation |
| Focused backend Result/Customer reads | 4 passed, 0 failed, 13 existing Pydantic deprecation warnings |
| Full frontend | Final local run: 44 files, 306 passed, 0 failed, 0 skipped |
| Typecheck/lint and production build | `npm run lint` PASS; `npm run build` PASS, including production bundle assertion |
| Backend Ruff and security policy | `python -m ruff check .` PASS; `python tests/check_security.py` PASS |
| Dependency audit | `npm audit --json`: 0 vulnerabilities at all severity levels |
| Deterministic browser acceptance | Final candidate: 8/8 1440×900 captures; two consecutive runs yielded identical SHA-256 for all eight PNGs; one complete fixture mutation flow and Result download PASS |
| Local full backend diagnostic | The broad run reached about 73% with many failures in unrelated suites and was interrupted after long external-service waits. A `--maxfail=1` rerun recorded 175 passed, 7 skipped, 1 error, 14 warnings. The first error is `tests/test_document_storage_service.py` fixture setup on local SQLite: `no such table: main.project_asset_import_batches`. That test/model is byte-identical to `origin/main`; no G1.1J code is on its path. CI's exact-head Linux/Python 3.12 backend job remains the integration gate. |
| Targeted PostgreSQL | Not run locally: this change adds read-only GETs and no migration, persistence authority or write semantics. |

## Independent review adjudication

The first frozen candidate was reviewed by DeepSeek v4.1 Flash and Gemini 3.1 Pro High at `1f101c0da723e90db287254b14b88ac2c917b78f`. Gemini found no functional or visual issue. DeepSeek inspected all seven candidate images and the three repo-local reference images, then raised four functional observations and one low-severity visual observation. This section records the decision; the revised candidate requires both reviewers again.

| Observation | Disposition |
| --- | --- |
| F1: `NOT_AVAILABLE` rendered as ordinary Result creation | VALID. The page now presents an explicit unavailable state, withholds generation, and directs the user to Case Overview. A focused test and an eighth browser capture cover it. |
| F2: Customer detail 403 blanked the whole read-only page | VALID. A 403 on the exact Customer read now keeps Result and frozen state visible, states that Customer is bound but detail cannot be viewed, and withholds Intake because Customer eligibility cannot be verified. No RBAC policy changed. |
| F3: Customer bind may remain available while a different stage has blockers | ACCEPTED by existing domain command boundary. The accepted Customer bind contract does not impose the Official Intake blocker predicate; a blocker may be the missing Customer itself. Project CAS and server validation still govern the bind. The UI never exposes Intake while an open blocker remains. |
| F4: Changed-file list omitted its own SHA manifest | VALID. The list now names every changed path, including the SHA manifest itself. SHA entries cover the other changed files; the manifest's own hash is reported separately to avoid a self-reference. Hashes are of committed Git blobs (LF canonical content), so CRLF working-tree bytes on Windows are expected to differ. |
| V1: S09 2A/Thanh lý fields absent from the candidate rail | ACCEPTED documented authority gap. The present public contract lacks the full approved S09 field set/edit command; optional fields remain truthful unavailable. No exact S09 mockup or synthetic fields are introduced. Material visual GAP remains 0. |

The second frozen candidate, `589b0ee7b38ffd9ff1c564223ebcbcdef5303a65`, was reviewed by both models. DeepSeek inspected eight candidate PNGs against the three repository-local baseline PNGs and found no material whole-screen visual gap. Gemini's follow-up pixel inspection identified state presentation details addressed in the current candidate. Both reviewers must inspect the final exact HEAD again after this change.

| Observation | Disposition |
| --- | --- |
| DeepSeek FUNC-1: Result reads allow existing `project:read` permission | ACCEPTED existing read boundary. The new exact-ID reads require authentication, tenant and Project scope and expose no storage key. Changing RBAC policy is an explicit G1.1J stop condition; the read follows existing Project visibility rather than creating a new permission. |
| DeepSeek FUNC-2: unknown Result response reconciles by Case State current Result rather than command receipt | ACCEPTED currentness boundary. Case State is the accepted authority for current Result selection. The UI does not infer latest or generate a second version after a Result appears; if no Result appears it offers deliberate same-key retry under unchanged preconditions. A command-receipt API is outside the accepted contract. |
| DeepSeek FUNC-3: reuse private storage read helper | ADVISORY. The bounded, size- and SHA-verified exact-artifact read is local to the new endpoint and adds no storage architecture or provider exposure. |
| DeepSeek VIS-1: optional S09 2A/Thanh lý fields absent | ACCEPTED documented S09 authority gap above; no fabricated fields. |
| DeepSeek VIS-2 and Gemini pixel review: unavailable message looked like an amber warning | VALID. The unavailable state now uses a blue information panel with icon and heading, distinct from warning and blocking. |
| Gemini pixel review: H1 changed to success text after Intake | VALID. The S09 page title stays stable; completion is shown in the stage strip and green success panel. |
| Gemini pixel review: completed state lacked success icon | VALID. The green completion panel now carries a visible check icon. |
| Gemini pixel review: blocked Intake section lacked an inline reason | VALID. The section now names the blocking condition and directs the user to Case Overview; it does not add a dead disabled action. |
| Gemini pixel review: right-rail blocker and warning counts lacked severity icons | VALID. Active blocker and warning counts now use distinct red and amber icons. |

The third frozen candidate, `c8dbb0f130b318a532c701d193dd0de7677bbe0c`, was reviewed by both models on all eight candidate PNGs and three repository-local baseline PNGs. Gemini reported zero functional findings and zero material visual GAPs. DeepSeek reported zero material visual GAPs, two low-severity functional findings and one informational documentation observation. The next frozen candidate requires both reviews again.

| Observation | Disposition |
| --- | --- |
| DeepSeek FUNC-1: Result/Intake actions displayed without accepted command permissions; server 403 received generic copy | VALID. The page now reads the authenticated account's effective permission list for Result generation, Customer binding and Intake, suppresses unauthorized actions, and explains missing permission. A server-side 403 after permission revocation receives explicit permission copy. The fixture actor has the required accepted permissions. Backend RBAC remains authoritative and unchanged. |
| DeepSeek FUNC-2: bound Customer read failure other than 403 hid frozen Result readback | VALID. A failed exact Customer detail read other than 401 now leaves Result/frozen context visible while withholding Intake; copy distinguishes permission denial from temporarily unavailable detail. A 401 still requires session recovery. |
| DeepSeek FUNC-3: historical PR-02 route contract lists old Workbench mapping | INFORMATIONAL. G1.1J's current route mapping and tests implement the user-requested `preliminary_ready_pending` and `official_intake_pending` URLs; the earlier PR-02 document records its historical handoff state. No runtime contract or other route changed. |

The fourth frozen candidate, `d580b6e373d76b655b49e83bc10cdd5eee68e611`, received both exact-HEAD reviews. Gemini found no functional or material visual issue. DeepSeek found zero material visual GAPs and one low-severity permission-state mismatch in Customer search; another informational note reflects an intentionally conservative Customer read. Its claim that command permissions were unseeded was incorrect: merged G1.1E already granted them to standard owner/appraiser roles. Both reviewers must inspect the next frozen HEAD after the fix below.

| Observation | Disposition |
| --- | --- |
| DeepSeek FUNC-1: Customer search shown with `project:update` but without `master_data:customer:read` | VALID. Customer search now requires both accepted permissions, and a server 403 after permission revocation gets a permission-specific message. The synthetic browser actor holds the accepted read permission. A focused test covers both missing and revoked permission. |
| DeepSeek FUNC-2: Customer detail failure withholds Intake more conservatively than the server | ACCEPTED fail-closed UI. The Customer's active status cannot be verified from current public readback, so the UI retains Result/frozen readback but withholds Intake until a successful Customer read. The server remains authoritative on commit. |
| DeepSeek FUNC-3: command permissions are intentionally unseeded | INVALID. Merged G1.1E data-only migration `a6b7c8d9e0f1_grant_precase_commands.py` grants Analysis finalization, Result generation and Official Intake commit to standard `owner` and `appraiser` roles. `test_g11e_rbac_postgresql.py` proves these grants and effective permissions on CI PostgreSQL, and proves other standard roles lack them. G1.1J only consumes the authenticated account's effective permissions; the backend remains authoritative. This PR does not change RBAC policy. No manual administrator grant is required for standard owner/appraiser roles when accepted migrations are applied; other roles remain unauthorized unless separate accepted RBAC authority grants them permission. |

## Functional boundary

Current Analysis and Result IDs, versions, Project CAS, Customer ID, blockers and route key come from Case State. The exact-ID Result GET only reads that artifact; the authenticated content GET streams the immutable stored bytes through a 10 MiB bound and verifies size and SHA-256. UI commands use confirmed payloads where required and persist one idempotency key per human attempt in session storage before sending. After any uncertain response, the UI refreshes Case State and offers a deliberate retry with the same key only while the exact preconditions still match. Post-intake controls are read-only. There is no Apply, ProjectAssetLine, S11, AI, G1.1K or OS-G2 implementation in this candidate.
