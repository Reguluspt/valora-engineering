# Preliminary-create contract and implementation evidence

## Current governing status — 2026-10-25

The [PM adjudication](https://github.com/Reguluspt/valora-engineering/pull/219#issuecomment-6394281774) governs this checkpoint: PR #219 remains **OPEN / DRAFT; INTEGRATION HOLD for F1; READY_FOR_MERGE=NO**. The reviewed candidate is `27635fc860b5c29b1c12555267201def24ca199e`, based on main `85adc2280b929381aa2f03dc0d915f3cc36e441b`, with exact-head CI #676 SUCCESS. [Both original reviewer reports](https://github.com/Reguluspt/valora-engineering/pull/219#issuecomment-6394240489) are received and adjudicated, with qualifications. They certify no later source revision.

F1/F2/F5 correction is a separate bounded local assignment, `VALORA-219-REVIEW-FINDINGS-CLOSEOUT-01`. A changed candidate requires its own authorized freeze, exact-head CI and separately released review; this document does not grant any of those steps. Existing accepted A26/Local Saturation evidence retains the disposition recorded by PM; it is not replaced by the historical STOP statements below.

Every checkpoint after the historical-record heading is an **as-of record**, including sentences that called their checkpoint “current” at that time. In particular, old `A26_OVERALL=PARTIAL`, `LOCAL_SATURATION=NOT_PASS` and `FIRST_PUSH=NOT_AUTHORIZED` values describe their dated checkpoints, not the current PR or a new candidate. Original wording, outcomes and failures remain retrievable in the [unchanged historical document at the reviewed SHA](https://github.com/Reguluspt/valora-engineering/blob/27635fc860b5c29b1c12555267201def24ca199e/docs/implementation/VALORA_UAT203_217_PRELIMINARY_CREATE_CONTRACT.md) and its linked original Issue #217 records. Relative private-evidence locators below identify retained developer artifacts, not public certification or portable machine paths.

### Local correction verification (not a frozen-candidate certification)

The F1/F2/F5 working-tree correction passed 134 focused/affected backend tests on disposable PostgreSQL 16.15 and 91 frontend tests across 11 files, plus Ruff, frontend typecheck/build and npm audit (zero findings). These local results do not replace exact-head CI or the new candidate's required independent reviews.

The first native-PG regression run recorded three expired-session test failures with the server's local timezone. Repeating the affected suite with the existing UTC test convention (`PGOPTIONS=-c timezone=UTC`, process-local only) passed all 134 tests; no auth/login implementation was changed. The failed run remains retained evidence, not counted as PASS. Real ASGI/HTTP smoke verified both an actual pre-D7 database and a migrated database; the SQL preflight refused the former and passed the latter. New browser/native-tab acceptance was not claimed or rerun; the F2 regression and existing feature/component tests cover the changed confirmation branch, without changing visual composition or the previously adjudicated A26 gate.

Raw logs and the exact local diff/hash manifest are retained in the task evidence set `VALORA-219-REVIEW-FINDINGS-CLOSEOUT-01`; the bounded closeout is delivered to PR #219 for PM assessment. No new freeze/push/reviewer call is inferred from these local checks.

## F1 activation and recovery boundary

New creation is opt-in: absent `VALORA_PRELIMINARY_CREATE_ENABLED` means disabled; only the exact value `true` enables creation of a new receipt. In both POST and GET, authorization precedes a read-only PostgreSQL catalog check. If the receipt relation is absent, POST returns typed non-final `503 CREATE_UNRESOLVED` and GET returns typed non-final `503 RECOVERY_UNAVAILABLE`, before querying that relation. No Project/audit/receipt write is attempted. A failed schema/query never causes legacy POST fallback or a new identity.

On a migrated database, POST still checks committed receipt identity and canonical bytes before the new-create flag: matching replay returns the original COMMITTED identity with HTTP 200 even when the flag is absent/false; conflicting bytes retain HTTP 409. GET recovery remains available with its existing permission and scope. The catalog guard prevents absent-table reads; the unchanged receipt query and transaction still fail closed on unusable columns/SQL. It does not replace applying the full atomic D7 migration and its constraints.

### Executable migration/activation verification

Run the following preflight against the explicitly selected deployment database using its normal authorized SQL client with stop-on-error enabled (for psql, `-X -v ON_ERROR_STOP=1`). It is read-only and must complete successfully before enabling create or the browser entry. The expected revision is this candidate's migration head; a future descendant requires its own accepted rollout contract.

```sql
BEGIN READ ONLY;
DO $$
BEGIN
  IF pg_catalog.to_regclass('preliminary_project_create_receipts') IS NULL THEN
    RAISE EXCEPTION 'D7 receipt schema is absent; activation blocked';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = '0a1b2c3d4e5f') THEN
    RAISE EXCEPTION 'D7 migration head is not applied; activation blocked';
  END IF;
  IF 11 <> (
    SELECT count(*) FROM pg_catalog.pg_constraint
    WHERE conrelid = pg_catalog.to_regclass('preliminary_project_create_receipts')
      AND conname = ANY (ARRAY[
        'uq_pcreate_scope', 'uq_pcreate_project', 'uq_pcreate_audit',
        'ck_pcreate_version', 'ck_pcreate_code', 'ck_pcreate_digest', 'ck_pcreate_payload_size',
        'fk_pcreate_org', 'fk_pcreate_actor', 'fk_pcreate_project', 'fk_pcreate_audit'
      ]) AND convalidated
  ) OR NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_constraint
    WHERE conrelid = pg_catalog.to_regclass('audit_events')
      AND conname = 'uq_pcreate_audit_binding' AND convalidated
  ) THEN
    RAISE EXCEPTION 'D7 constraints are incomplete; activation blocked';
  END IF;
END $$;
ROLLBACK;
```

1. Keep create explicitly disabled while applying the unchanged additive migration through `0a1b2c3d4e5f`; do not downgrade or backfill retained receipts. Record target identity, applied revision and successful SQL preflight result.
2. On an isolated synthetic acceptance target, verify the disabled state: a new valid POST is non-final 503 with no new Project/audit/receipt; an existing matching committed replay and GET retain HTTP 200 and the original identity. Never test writes against a protected or production target under this developer task.
3. Enable `VALORA_PRELIMINARY_CREATE_ENABLED=true` explicitly only after that schema proof, then enable the compatible browser entry. On the authorized synthetic target, verify HTTP 201 once, matching replay HTTP 200, GET HTTP 200 and exactly one Project/audit/receipt binding. A prematurely enabled backend on absent schema remains non-final 503 without writes.
4. For application rollback, set the flag false and keep the compatible backend/GET/pending UI available. Verify original committed recovery/replay again. Retain markers on typed 503, unavailable recovery or old-node untyped 404; never recreate an unknown request or fall back to legacy POST. Production activation remains a separate authorized gate.

## Historical checkpoint records — as-of evidence only

## A26 Case U fixture diagnosis — STOP before activation

Date: 2026-10-21, Asia/Saigon. Task continuation: `A26-U-FIXTURE-READONLY-DIAGNOSIS`. This current checkpoint supersedes the historical status statements below. [PM decision](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6320086220) accepts **Case C COMMITTED native restoration** on PO screenshots/native-action attestation and developer read-only corroboration. The separately authenticated TestClient GET is backend evidence, never a Chrome GET. D5 permits reopening the recorded COMMITTED Project without automatic recovery GET. No Case C repeat is required.

**PROJECT_AUTHORITY_READY=YES; CASE_U_READY_FOR_OPERATOR=NO; A26_OVERALL=PARTIAL; LOCAL_SATURATION=NOT_PASS; FIRST_PUSH=NOT_AUTHORIZED.** Fetch/live main and worktree HEAD are `85adc2280b929381aa2f03dc0d915f3cc36e441b`; CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`; exact-main CI #674/run 39269296495 completed/SUCCESS, read only. Issue #217 OPEN; no remote task branch/PR. Requested `gpt-6.1-sol/high` is listed in the local model catalog; no independent runtime-model attestation or provider invocation. Bootstrap/resume/dev-handoff, CODEX §§1/8.1/10, Guardrails, Protocol V2, Compact Contract and applicable Frontend Architecture Rule were consulted. Optional OpenViking recall unused; automatic recall/capture/injection OFF.

### Verified cause of the ordinary response

The existing `tests/e2e/issue217_preliminary_create.py` initializes `BrowserFixture.mode="normal"`. Only the separate `/__issue217_fixture/control?mode=truncated_response` operation arms truncation. Neither server nor frontend consumes `a26_case`; it is a human case label. HTML startup fault injection consumes a different `issue217_fault` parameter and offers storage/CSPRNG/marker faults, not truncated-response activation. The earlier CDP-dependent `operator_browser.py prepare` explicitly included the control call, but was not executed; it remains outside the permitted browser route.

The retained preparation response at 14:37:51 UTC records normal/posts0. `operator-http.jsonl` has one control call (row 4 at 14:37:51.313476 UTC) and no later control call before its only create (row 18 at 15:14:42.809561 UTC). That POST returned 201 and was followed by reads of Project `793f2c1e-a123-44d9-a9de-0bd469f07699` and Intake resources. The live process PID 22036 started before that preparation checkpoint and is still the listener on 127.0.0.1:8017. Thus the supported HTTP activation step was omitted; navigation to the labelled URL could not arm it. This is a preparation/execution gap, not a demonstrated hash-routing or product-create defect. The log deliberately omits queries and bodies, so the old normal-mode value comes from the saved response, not reconstructed query text. No direct historical process-memory trace or browser body capture is claimed.

**201 alone is inconclusive:** the active truncation branch also emits HTTP 201. On underlying 200/201 it replaces the response with Content-Type application/json, Content-Length 999 and only the byte `{`, resetting its mode to normal before body completion. Expected browser results are an incomplete-body/JSON error, UNCERTAIN state and no Intake navigation. Those are expected from source, not newly executed evidence. Previous validated COMMITTED identity plus Intake navigation and absent arming establish the ordinary-response disposition.

### Route, service and scope verification

The exact future URL is `http://127.0.0.1:8017/?a26_case=U#/workbench/preliminary-requests/new`. The query before `#` reaches the HTML proxy and is ignored as an activation signal. The fragment never reaches HTTP; App.tsx reads it and uses exact route equality. The old pathname-only URL has no matching hash and opens the neutral Project list; appending the label inside the hash changes the route string and is unsupported. The observed attempt used the correct hash and reached creation, so the old pathname error does not explain this attempt.

Canonical UI/API origin is 127.0.0.1:8017, with API base `http://127.0.0.1:8017/api/v1`. Its ASGI wrapper handles the control path first, serves /api and /health directly through the fixture/application, and proxies frontend content to preview 127.0.0.1:5417 (PID 10468). The served HTML and `index-YmY1_JKi.js` match current dist bytes; the compiled client has empty API base and relative API calls. Direct 5417 use is not equivalent: the Vite configuration proxies /api to 8000 and bypasses this wrapper. No intercepting service worker or browser-installed fixture is required by the harness.

Matching is **process-wide mode + exact POST /api/v1/projects/preliminary-create**. There is no browser, actor, tenant, request UUID, name, query or hash matcher. Backend authorization still applies, but fixture fault selection is not browser-scoped. Any later operator run needs exclusive coordinated use of this disposable service, no competing create traffic, and actual browser identity verification before arming. Do not invent a case-specific matcher or bypass a scope check.

Read-only SQL reverified container `valora-issue217-disposable-pg16`, task label issue217, loopback 55417, DB `valora_issue217_disposable`, migration `0a1b2c3d4e5f`, transaction_read_only=on. Primary synthetic owner is active: organization `0bbb53e7-a14d-4453-86bf-645595aa13d5`, actor `813d35dc-abc9-422e-8587-41319b0a4189`, permissions project:create/read. Current primary Project/receipt/audit counts are 21/21/45, comparison tenant 0/0/2, global 357/334/417. These match PM's post-auth-refresh checkpoint and are not a new per-case baseline. The earlier C request `cf88f789-da67-45b0-adfd-1742b811fa24` still binds the accepted Project and receipt `e0cbf5ff-65ef-4e9c-a279-067de2510b0a` and ProjectCreated audit. No authenticated GET, new session or browser inspection was executed here. Current operator browser scope remains unverified.

### Exact activation proposal and read-only STOP

The existing private runbook now contains the complete **deferred** Case U procedure: verify actual synthetic browser account and fresh scoped tab without clearing C; record DB/log/process boundary; after PM approval issue exactly the existing GET control with mode=truncated_response; require a 200 JSON acknowledgement of that mode and unchanged post counter before release to the operator; then a separately authorized single explicit UI submission. Do not call normal between arming and that submission. Preserve one generated request UUID, raw UNCERTAIN marker, malformed-response evidence and exact DB binding; collect immediate pre-close and untouched native-restoration evidence; only later use the app's explicit GET recovery for that same UUID. No automatic replay or replacement UUID, and no further Case C submission.

**Precise limitation:** there is no pure read-only status/dry-run endpoint. Even control without mode assigns self.mode and, when normal, sets the release event. Arming changes shared in-memory fixture state, although it does not itself write the DB. Proving the actual truncated POST transport requires a business write. Neither operation was executed. Static routing and source establish the existing supported activation method, not current armed state or verified live truncation. CASE_U_READY_FOR_OPERATOR therefore remains NO.

Minimal proposed repair is procedural: perform the omitted existing control operation with acknowledgement and exclusive synthetic scope under separate authorization. No source change or architecture/security change is needed for that proposal. If PM requires an entirely read-only live-mode probe or per-browser fault isolation, the current harness cannot supply it; return that capability gap to PM rather than adding an endpoint or changing security here.

### Evidence and preservation

Only this existing diagnostic document and existing private A26 runbook, preparation-status evidence and TASK_STATE were updated. All other 27 changed implementation/test/dependency paths retain their starting SHA256 bytes; the changed-path inventory remains 28, index empty, HEAD unchanged. Existing log entries and historical evidence are preserved. Live proof and file manifests are retained under the new diagnosis entry in the existing private preparation-status JSON. Diagnosis made only read-only SQL, static HTTP GETs and repository/GitHub inspection; no fixture-control call, create POST, DB mutation, source change, browser launch, policy bypass, provider/reviewer call, commit, push, PR, CI trigger or protected #199/#203/#205 change occurred. Earlier test results are historical, not rerun or newly certified.

**NEXT_AUTHORIZED_ACTION: STOP.** PM must verify the exact activation procedure and separately authorize fixture arming, actual-browser preflight and any subsequent single controlled U submission. No operator create request is made now.

## A26 operator-only preparation — procedure ready; actual browser fixtures pending

Date: 2026-10-21, Asia/Saigon. **AWAITING_OPERATOR_A26=YES; A26 PARTIAL; Local Saturation NOT_PASS.** This checkpoint supersedes current-status claims in the historical sections below. It does not request the operator to act. [PM authority](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6318593615) permits preparation only and preserves the binding automated browser-policy denial.

Bootstrap/resume reverified live main and assigned worktree HEAD `85adc2280b929381aa2f03dc0d915f3cc36e441b`, CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`, exact-main CI #674/run 39269296495 completed/success, Issue #217 OPEN and no task-branch PR. The local model catalog lists `gpt-6.1-sol` with HIGH; runtime identity is not independently attested. No additional model/provider/reviewer was invoked. No commit, push, PR, CI trigger, freeze, deploy or PO UAT occurred. Optional OpenViking recall was not used; automatic recall/capture/injection remain OFF.

All 28 working-tree file hashes matched the retained prior final manifest before this continuation. Only this existing evidence document changes in the worktree; the other 27 implementation/test/dependency files remain byte-identical, preserving D7, Option A and the E2E fixture. No path expansion, new endpoint, migration or fixture source change occurred. Existing private runbook, TASK_STATE, preparation status, environment snapshot and process inventory were updated in place.

Verified the existing PostgreSQL container label and loopback binding, actual database `valora_issue217_disposable`, migration head `0a1b2c3d4e5f` and 508 synthetic-only organizations through the existing READ ONLY collector. Primary tenant remains **20 Projects / 20 receipts / 42 audits**, foreign tenant **0 / 0 / 2**; global synthetic counts **356 / 333 / 414**. There were no business writes this continuation. Canonical application `http://127.0.0.1:8017`, API `/api/v1`, upstream production preview `127.0.0.1:5417` and health/page responses are verified. Actual API PID is 22036, superseding the stale inventory PID 21656. Existing server logging contains only timestamp/method/path/status; zero create POSTs, fixture normal/posts0. Existing account hashes and owner/viewer scopes were verified privately without credential disclosure or new authenticated sessions.

**Exact initialization boundary:** actual request UUIDs are generated on deliberate UI submit; the real tab writes/reads its scoped sessionStorage marker before POST. The server cannot initialize storage in an unopened browser. U and C therefore remain **NOT_INITIALIZED**, with request IDs **NOT_ALLOCATED**. A fabricated UUID/receipt, copied marker, restored-marker fault or URL alone would not meet A26. No browser was opened, no native action performed and the existing CDP-dependent `operator_browser.py` was not executed. The prior approval rejection remains `blocked by policy`; no alternative launch/instrumentation was attempted.

The corrected future case URLs are `http://127.0.0.1:8017/?a26_case=U#/workbench/preliminary-requests/new` and the corresponding `a26_case=C` URL. `App.tsx` initializes navigation from the hash; the old pathname-only reserved URLs land on the neutral list. Query labels initialize no recovery state. The prepared procedure uses actual U submission with the existing truncated-success control, independent normal C submission, and same-tab return through the existing recovery button to retain COMMITTED. U represents uncertain client knowledge even though that fault commits a real receipt. Predicted setup increments are not recorded as observations.

The existing private `A26_OPERATOR_RUNBOOK.md` now covers ordinary Windows profile setup subject to policy, private synthetic credential retrieval without printing the credential, exact submissions, actual marker confirmation, immediate per-case DB/log baselines, native Ctrl+W/Ctrl+Shift+T, untouched observation, explicit GET recovery (including C's separate GET evidence tab), original Project opening, actor/tenant masking and unchanged count/binding/digest comparisons. It distinguishes initialization navigation from native restoration and never assumes storage survives. The handle omits phase, and UNCERTAIN/PARKED share a UI label: exact marker evidence needs separately permitted manual read-only Storage inspection or another accepted supported route. If unavailable, mark that evidence BLOCKED; no DevTools policy change, console code or CDP is proposed. Server GET alone cannot prove correct restored tab state.

Retained raw evidence was checked: npm audit **0 vulnerabilities**, pip audit **84 dependencies/0 findings/0 skips**, frontend **68 files/557 passed**, PostgreSQL **219 passed/14 warnings/0 skips**. These are previous passing runs, not reruns or a new complete T3 browser acceptance. A01–A31 remains **30 retained PASS / A26 PARTIAL**. Current environment snapshots are not pre-close case baselines. No final candidate freeze/review/CI is authorized. **STOP at prepared procedure:** actual browser setup, U/C IDs/markers and real native evidence require later permitted voluntary human participation; none has been requested at this checkpoint.

Preparation housekeeping: the collector import generated one private Python bytecode cache (`__pycache__/task_runtime.cpython-312.pyc`). Automatic approval rejected its removal before execution with `blocked by policy`; no alternate removal was attempted. The cache remains outside the worktree and does not change the 28-path product inventory. Final `git diff --check` passed; index and HEAD remain unchanged.

## T2 remediation complete; A26 isolated-browser setup requires operator/Gate action

Date: 2026-10-21, Asia/Saigon. **T2 SECURITY PASS; A26 PARTIAL; LOCAL SATURATION NOT_PASS; AWAITING_OPERATOR_A26.** This is the current checkpoint and supersedes status claims in the historical sections below. The [PM continuation](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6318136600) released dependency remediation independently from A26 and approved isolated operator-test preparation. No commit, push, PR, reviewer/provider call, manual CI, merge, deployment, issue mutation or Product Owner UAT occurred.

### Authority, preservation and exact scope

Fetched live main, task HEAD and GitHub main remain `85adc2280b929381aa2f03dc0d915f3cc36e441b`; CODEX blob remains `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`. Exact-main CI #674 / run `39269296495` is completed/success on that SHA. Issue #217 is OPEN; the existing implementation branch has no PR. Bootstrap/resume/live-authority/dev-handoff and named repository authorities were applied. The local catalog lists `gpt-6.1-sol` with `high`; independent runtime-model attestation is unavailable. Automatic OpenViking recall/capture/injection remained OFF; no memory/provider/reviewer call was made.

All 25 retained paths matched the prior security-continuation SHA256 manifest before edits. This continuation changes only this existing evidence document plus the three expressly conditional security paths. The other 24 original paths, including backend/frontend source, E2E harness, migration and historical tests, remain byte-identical to the start manifest. D7 refusal and Option A are unchanged. Exact total: **28 changed paths**, comprising the original 25 plus `frontend/package.json`, `frontend/package-lock.json` and `backend/pyproject.toml`. No new tracked path beyond that amendment is required.

### Dependency remediation and independent checks

| Check | Verified outcome |
| --- | --- |
| Vite floor and resolution | `^6.4.3` → `^6.4.5`; installed/locked **6.4.5**, the smallest verified patched release for [GHSA-8g5g-mxqh-grgj](https://github.com/vitejs/vite/security/advisories/GHSA-8g5g-mxqh-grgj). |
| npm integrity and tree | Official registry tarball/integrity match. Only root manifest metadata and `node_modules/vite` change in the lock. Every other locked package remains identical; full `npm ls --all` passes, and plugin-react/Vitest/mocker deduplicate to Vite 6.4.5. |
| Clean npm installation and audit | Task-worktree `npm ci` succeeds; fresh full `npm audit --json` reports **0 vulnerabilities of every severity**. No blanket update, major upgrade, suppression or script-policy change. |
| Actual certifi dependency scope | Runtime `httpx 0.28.1 → certifi`, `httpcore → certifi`, and `msal 1.39.0 → requests 2.34.2 → certifi`; pip-audit tooling also uses requests. This is not a tooling-only dependency. |
| Reproducible certifi floor | Added only `certifi>=2026.10.19` to backend runtime requirements, preventing production resolution of the vulnerable baseline. [Reviewed GHSA](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) requires that floor. No backend lockfile or global Python mutation. |
| Isolated Python environment | Fresh task-owned Python 3.12 environment installs the previous 84 third-party versions with **only certifi 2026.7.22 → 2026.10.19**. All runtime/dev manifest requirements and `pip check` pass. The shared prior environment is read-only and is not used by the prepared task runtime. |
| Python package provenance | Installed certifi SHA256 matches official PyPI release metadata; compromised `emSign ECC Root CA - G3` is absent; HTTPS PyPI verification succeeds with the new environment. Private exact requirements and installer report retain reproducible local resolution. |
| Fresh pip audit | **84 dependencies, 0 known vulnerabilities, 0 skipped local project distributions**; source imports use the assigned worktree rather than installing unrelated local distributions. |
| Frontend regression and candidate checks | **68 files / 557 tests PASS**, zero skips; `npm run lint` and `npm run build` PASS, including TypeScript and production-bundle assertion. Existing >500 kB chunk warning remains. |
| Backend/API/real PostgreSQL regression | **219 PASS**, zero failures/skips, 14 existing warnings, 126.70s, in the fresh safe environment. Includes focused create/API/PG/migration, affected project/Pre-case/auth suites and all three authorized historical PG/migration suites. Counts overlap earlier runs and are not additive. |
| Source security/static checks | Backend `ruff check .`, `python tests/check_security.py`, and E2E-harness Ruff PASS. The private runtime/observer helper Ruff checks also pass. |

Raw evidence is retained in `private-evidence/issue217-t2-operator-20261021`: start/final manifests, exact changed-path inventory, clean-install/audit/tree reports, Python version/chain/provenance/installer reports, frontend test/lint/build logs, `backend-regression-pg.log`, read-only database snapshots and TASK_STATE. The pre-existing 45 historical migration tests are included in the fresh 219-test run. No mandatory skipped check is treated as PASS.

### A26 preparation and genuine execution blocker

The retained task-only PostgreSQL container `valora-issue217-disposable-pg16` was label/port/volume verified before startup: label `valora.task=issue217`, host binding **127.0.0.1:55417**, database **valora_issue217_disposable**, migration head **0a1b2c3d4e5f**. Read-only inventory after regressions contains 508 organizations: 506 `i217-*` fixtures and only the two known synthetic browser tenants. Browser tenant `issue217-browser-synthetic` is `0bbb53e7-a14d-4453-86bf-645595aa13d5`; the other-tenant fixture is `7c151780-0a38-4c8b-86bd-0fa6c8b19427`. Baseline browser-tenant counts are **20 Projects / 20 receipts / 42 audits**; other tenant **0 / 0 / 2**. These are pre-existing synthetic facts, not newly prepared A26 requests.

The newly built production preview listens at **127.0.0.1:5417**. The task-only fixture/proxy at **http://127.0.0.1:8017** uses the fresh safe Python environment; `/health` returns 200. A private ASGI wrapper records timestamp, HTTP method, path and response status to `operator-http.jsonl`, excluding bodies, headers, cookies, tokens and query parameters. It imports the unchanged approved E2E harness, including its truncated-response mode. The private preparation helper is written to create two independent cases through actual UI submissions, capture only scoped non-secret markers, and collect read-only page/account/lifecycle evidence. It has **not executed**.

**Automatic approval review rejected the tool action to launch a new temporary isolated Microsoft Edge profile with loopback debugging and prepare the tabs. The only stated reason was `blocked by policy`. The rejected command did not execute.** No external browser launched, no profile/session was accessed and no A26 request/marker was created. No alternate launcher, unsupported native restore action or policy bypass was attempted. The built-in browser's already known missing restore API was not investigated again.

Accordingly, **A26_OPERATOR_ENV_READY is PARTIAL, not YES**: server, disposable DB, logging and runbook are ready; the isolated operator browser, authenticated tabs, independent request IDs and pre-close markers remain pending. Intended non-secret URLs are `http://127.0.0.1:8017/workbench/preliminary-requests/new?a26_case=U` and the same path with `a26_case=C`. Opening these alone does not initialize a recovery marker. No native-close, native-restore, restored-storage, HTTP-create delta or post-restoration database proof is claimed.

The required next action is an operator/Gate-approved isolated browser setup route within the host's tool policy. After setup and actual pre-close fixtures are verified, the operator runs Case U and Case C separately: select the prepared tab, **Ctrl+W**, then browser-native **Ctrl+Shift+T**, leave the restored page untouched and report completion. Collection must first capture actual marker retention/loss, account/tenant, UI, lifecycle trace and request/DB deltas; then explicitly perform authenticated recovery GET against the same ID and verify same-/foreign-scope visibility. No automatic create POST, replacement request ID, duplicate Project or receipt/audit change is allowed. Marker loss must be assessed honestly against accepted D5/A26, without reinjection or assuming persistence. Native restoration remains mandatory.

### Checkpoint disposition

T0/T1 and independent T2 checks PASS; real PostgreSQL T3 PASS. A01–A31 remains **30 retained PASS / A26 PARTIAL**; F02/A31 source is unchanged, but final browser validation of the new bundle awaits the approved browser route. Browser T3 remains PARTIAL and Local Saturation remains **NOT_PASS**. The task-only API/preview/container remain running for the operator checkpoint. No #199/#203/#205 environment, personal browser profile, global Python installation or later product gate was modified. Full current fields, remaining blocker and next action are in the private `TASK_STATE.txt`; no first-push permission is active until mandatory native evidence and final gates pass.

## Security/A26 final continuation — native restoration capability STOP

Date: 2026-10-21, Asia/Saigon. **STOPPED_A26_NATIVE_RESTORE_UNAVAILABLE; LOCAL SATURATION NOT PASS; NO COMMIT OR FIRST PUSH.** This checkpoint supersedes the current-state claims below and preserves their historical evidence. The [PM security/A26 amendment](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6317917187) now authorizes up to three conditional dependency paths; the earlier request for dependency authorization is historical. Execution stopped at the amendment's independently mandatory browser capability boundary before dependency installation or source changes.

### Reverified authority and preservation

Session-bootstrap, worktree-resume, live-authority-bootstrap and dev-handoff skills were read. Fetched `origin/main` and task HEAD both remain `85adc2280b929381aa2f03dc0d915f3cc36e441b`; both CODEX blobs are `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`. Live exact-main CI #674/run `39269296495` is completed/success on that SHA. Issue #217 is OPEN; the implementation branch has no PR. The local model catalog lists `gpt-6.1-sol` and supports `high`; independent runtime-model attestation is unavailable. No model substitution or provider call occurred.

Before this evidence update, all **25/25** working-copy hashes matched the previous `issue217-f02-20261021/final-manifest.json`. Only this approved evidence document changes during this continuation. Backend/frontend implementation, historical tests, dependencies, D7 refusal and Option A are byte-preserved. No protected #199/#203/#205 target, Python environment, database, service or browser application state was mutated. No stack was started; no new browser acceptance schedule was executed. Optional OpenViking recall/capture remained OFF.

### Exact A26 capability blocker

The Browser skill connected to **ChatGPT in-app browser**, browser ID `2`, selected for canonical `http://127.0.0.1:8017`. Its complete supported API exposes `Tab.close()`, `Tabs.new()`, `Tab.reload()` and navigation, but **no native restore/reopen-closed-tab operation**. Live `browser.capabilities.list()` advertises only `visibility` and `viewport`; `browser.tabs.list()` returns `[]`. The unavailable action is restoration of an actually closed tab through native browser session restoration, preserving or observably discarding that tab's browser-managed scoped sessionStorage. Creating another tab, navigating to its old URL, reloading or injecting markers cannot establish this lifecycle.

Private evidence is retained under `private-evidence/issue217-security-a26-final-20261021`: `browser-supported-api.txt`, `browser-capabilities.json`, preservation manifest, baseline/registry evidence and final TASK_STATE. No undocumented restore method, alternate browser automation, browser policy bypass or repeated shortcut attempt was used. The previous native-shortcut failure remains historical; the prior restored-marker fixture remains supplemental. There is no new before/after screenshot, request trace or database delta because actual native restoration could not be exercised. **A26 stays PARTIAL / INCOMPLETE, never PASS or N/A.**

### Dependency findings at the stop

| Item | Verified result / remaining evidence |
| --- | --- |
| Vite installed/tree | Actual installed and locked root Vite **6.4.3**; plugin-react 4.7.0, Vitest 4.1.11 and its mocker deduplicate to that root. Manifest remains `^6.4.3`. |
| Vite patch source | Official [GHSA-8g5g-mxqh-grgj](https://github.com/vitejs/vite/security/advisories/GHSA-8g5g-mxqh-grgj), **Moderate**, identifies 6.4.4 affected and **6.4.5** patched. Earlier retained audit contains GHSA-587h-7wmj-h5pm (**High**) and GHSA-698v-4r3x-3vcv / GHSA-r825-w8mm-5pxw (**Moderate**) affecting installed 6.4.3. |
| Authentic registry availability | Read-only `npm view vite@6.4.5 version dist.integrity dist.tarball --registry=https://registry.npmjs.org --json` returns version **6.4.5**, official tarball `https://registry.npmjs.org/vite/-/vite-6.4.5.tgz`, integrity `sha512-4enwjFfi4IwtEh0w+jPzpLVOFQiPHmmzPxcHXQOyEur47o6u0jE573DmGpjA+7irXoMLYRZD5ZaFUEneS3abPg==`. No package was installed or independently validated through clean install/audit. Secure candidate selection remains pending those checks. |
| certifi advisory | Official [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2), **Critical**, fixes affected certifi at **2026.10.19**. The retained isolated-environment audit reports **2026.7.22**, `PYSEC-2026-4320`, fixed 2026.10.19. This continuation did not inspect/reinstall that environment or verify fixed-release availability. Runtime/dev parent and reproducible remediation remain **UNVERIFIED**. No runtime floor was added. |
| Manifest/lock/tree changes | **None.** No new dependency paths, transitive changes, suppression, waiver, global package mutation or major upgrade. |
| Audits and regressions | Prior npm/pip audits remain **FAIL**. Clean `npm ci`, fresh audits and dependency-change regressions were **NOT RUN**, following the explicit capability STOP. No secure-after claim is made. |

### Minimal operator-assisted A26 verification

This procedure is pending PM/Gate Owner coordination; it is developer acceptance evidence, **not Product Owner business UAT**.

1. Provide a browser with an operator-accessible native **Reopen closed tab** action. Reverify the existing #217 task-owned PostgreSQL container, synthetic database and canonical `127.0.0.1:8017` stack before starting only those isolated services. Use the approved production frontend fixture. Do not connect protected UAT targets.
2. Sign in as the synthetic owner. Use the existing test-only `truncated_response` mode and explicitly submit one synthetic intent. Record its generated non-secret request ID, scoped pending marker and UNCERTAIN UI before closure. Capture only this feature's marker, excluding authentication/session secrets. Record baseline scoped Project/receipt/ProjectCreated audit counts and request trace.
3. Close that actual tab through browser UI; record closure. Invoke the browser's native **Reopen closed tab** action; record restoration. Do not substitute a fresh URL, reload, React remount or marker injection. Capture the browser/version, screenshots and actual scoped marker retention/loss. If storage is lost, record that lifecycle and the support/handle behavior without claiming persistence.
4. Observe the restored page before intervention: no automatic POST, replacement request ID or additional Project/audit/receipt. If the marker survives, explicitly invoke authenticated GET recovery for the same ID and verify the original committed identity. Record the HTTP method/path/status and sanitized response, then compare scoped database counts/bindings.
5. Repeat native closure/restoration with a retained COMMITTED marker. Verify it opens only the original Project without dispatching creation. Exercise the applicable different-actor/tenant restoration schedule and verify quarantine/no foreign marker details, privacy-safe foreign GET and no cross-scope mutations.
6. Preserve screenshots before closure and after native restoration/recovery, the native action record, scoped marker snapshots, sanitized request trace and synthetic SQL count/audit bindings. PM/Gate Owner must assess these artifacts against A26. After the capability/evidence disposition permits resumption, complete the authorized dependency fixes, audits, affected regressions and final Local Saturation review before commit/push.

### Current TASK_STATE

```text
TASK_ID: VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT
PROJECT_AUTHORITY_READY: YES; capability STOP applies
MODEL_USED: gpt-6.1-sol/high local catalog; runtime not independently attested
BASELINE_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b
CODEX_BLOB: dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e
EXACT_MAIN_CI: #674 / 39269296495 / completed-success / exact SHA
VITE_VERSION_BEFORE: 6.4.3 installed and locked
VITE_VERSION_AFTER: 6.4.3 unchanged
VITE_PATCH_VERIFIED: 6.4.5 official advisory and registry metadata; install/audit pending
NPM_AUDIT_RESULT: retained FAIL; not rerun
CERTIFI_VERSION_BEFORE: 2026.7.22 retained audit; live environment not reverified
CERTIFI_VERSION_AFTER: unchanged by this continuation; live value not reverified
CERTIFI_DEPENDENCY_SCOPE: UNVERIFIED at capability STOP
PIP_AUDIT_RESULT: retained FAIL; not rerun
DEPENDENCY_CHANGED_PATHS: NONE
TOTAL_CHANGED_PATHS: 25; only existing approved evidence document updated this turn
D9_SCOPE_COMPLIANCE: YES; no new path
F02_STATUS: retained RESOLVED; implementation hashes unchanged
A26_NATIVE_RESTORE: INCOMPLETE / supported native restore operation unavailable
A01_A31_RECONCILIATION: retained 30 PASS, A26 PARTIAL; no new browser proof
T0_RESULT: retained PASS; no implementation change
T1_RESULT: retained PASS; 557 frontend and retained backend evidence
T2_RESULT: FAIL; dependency remediation/audits pending
T3_POSTGRESQL_RESULT: retained PASS; 107 combined, 45 historical; no PG rerun
T3_BROWSER_RESULT: PARTIAL; A26 native restore missing
LOCAL_SATURATION_GATE: NOT_PASS
FIRST_PUSH_MATURITY: NOT_REACHED / NO_PUSH
DRAFT_PR_URL: NOT_CREATED
FROZEN_PR_HEAD: NONE
AUTO_CI_RUN: NONE
AUTO_CI_STATUS: NOT_TRIGGERED
REVIEWER_A: NOT_RUN
REVIEWER_B: NOT_RUN
MERGE: NOT_AUTHORIZED
PO_UAT: NOT_RUN
REMAINING_BLOCKERS: unavailable native restoration operation; dependency remediation and fresh audits
READY_FOR_PM_REVIEW: YES for blocker/evidence disposition only; NO for candidate approval
NEXT_AUTHORIZED_ACTION: PM/Gate Owner coordinates supported native restoration/operator evidence and resumption
```

## Historical checkpoint — F02 repaired; dependency security gate blocked

Date: 2026-10-21, Asia/Saigon. **F02 RESOLVED; LOCAL SATURATION NOT PASS; NO FIRST PUSH.** This section supersedes the historical checkpoints below. All 25 task-owned paths and earlier raw evidence are preserved. No files are staged; no commit, push, PR, reviewer/provider call, manual CI, merge, deployment or PO UAT was performed.

### Live authority and preservation

Reverified the [F02 PM authority](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6317003062), [accepted D1–D9](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6293809877) and historical-test amendment. Live main/task HEAD remain `85adc2280b929381aa2f03dc0d915f3cc36e441b`; CODEX blob remains `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`; exact-main CI #674/run `39269296495` is completed/success. Issue #217 remains OPEN and the bounded branch has no PR. The selected local model/catalog remains `gpt-6.1-sol` / `high`; independent runtime attestation is not claimed.

Task-only PostgreSQL 16.15 remains in the labeled `valora-issue217-disposable-pg16` container at `127.0.0.1:55417`, database `valora_issue217_disposable`, head `0a1b2c3d4e5f`. Final inventory: 425 organizations, zero outside the known synthetic fixture patterns. Four exercised A22/A23/A26 request IDs each have exactly one receipt, one distinct Project and one distinct audit binding. Protected #199/#203/#205 were not connected or mutated. Browser/API origin is `http://127.0.0.1:8017`, production preview upstream 5417. Synthetic account details remain test fixtures; no real credentials/client data were added. Optional OpenViking recall/capture remained OFF.

SHA256 comparison against the preserved F02 start manifest confirms unchanged backend implementation, schema, migration and all backend tests, as well as the three historical migration tests. The same exact 25 paths remain: D9's original 22 plus the three specifically authorized historical tests. All excluded-file hashes remain identical, including `precase.css`, `AppShell.tsx`, `main.tsx`, shared API/auth, global themes and frontend dependency manifests. F02 changed only the two feature presentation files, their existing recovery test, the approved E2E harness, and this evidence document.

### F02 root cause, bounded fix and visual proof

The hypothesis was verified before mutation. The production DOM had no `.fui-FluentProvider` ancestor or portal boundary; `--colorBrandBackground` and `--spacingHorizontalM` were empty, and recovery buttons computed padding `0px` / border `0px none`. The production CSS and 14 Griffel stylesheets were loaded, and existing Valora variables resolved. The failure was missing Fluent theme context plus feature-local action/entry spacing, rather than an absent bundle. Multiple entries represented separately retained legitimate intents.

`PreliminaryRequestCreatePage.tsx` now establishes `FluentProvider theme={webLightTheme}` only for the create/recovery feature. Local composition uses existing Valora spacing/canvas tokens and existing panel structure. `PreliminaryCreateRecovery.tsx` separates each retained intent into an independently labeled region with heading, status badge, wrapped locator and grouped actions; common navigation/session actions use the panel footer. Existing shared MessageBar supplies accessible feedback. Storage-persistence failure after a valid receipt is distinguished from an unknown business outcome. The distinct-intent acknowledgment describes parked uncertainty only when a parked entry exists. No nonce, replay, transaction, migration or shared-auth policy changed. F01's one-submit acknowledgment reset is retained.

Final production-build browser observations: Fluent provider present; brand `#0f6cbd`; button padding `5px 12px`, border `1px solid`; 16px separation between retained entries. At 1280×800 and 960×800, both unresolved/parked and COMMITTED entries remained independently visible/actionable with no horizontal overflow, clipping or overlap; the form follows a separate panel. The page scrolls vertically when retained evidence exceeds the viewport. Keyboard Tab showed visible focus and status announcements use polite live feedback. No facts were removed to improve layout. Component regressions cover independent multi-intent actions and acknowledged COMMITTED identity surviving local persistence failure.

Private sanitized artifacts are under `private-evidence/issue217-f02-20261021`: `before-computed.json`, `before.dom.txt`, `before-1280.png`, `layout-1280.json`, `layout-960.json`, `keyboard-focus.json/png`, `final-1280.jpg`, `final-960.jpg`, A22/A23/A25/A26 screenshots/text, API logs and audit/test outputs. Earlier PG/F01/HTTP-loss proof remains under `private-evidence/issue217-resume-20261020`. These are local developer evidence, not published PO UAT artifacts.

### Current checks and security blocker

| Check | Final observed result |
| --- | --- |
| Focused backend/API/real PG/migration command recorded below | Retained **107 passed**, zero skips; raw log re-read and every relevant source/test hash unchanged during F02. Covers Option A, races, process death, commit ambiguity, auth and D7. |
| Three historical migration suites | Retained **45 passed**, zero skips; raw log and unchanged hashes verified. |
| Affected backend create/auth and lifecycle/Analysis/Result/Intake regressions | Retained **152 passed** and **202 passed**, overlapping earlier runs, not additive totals. Product backend unchanged. |
| Frontend `npm test` on final presentation/copy | **68 files / 557 passed**, zero skips, 7.83s. Includes the affected focused suites and F01/F02 regressions. |
| `npm run lint`; `npm run build` | PASS, including TypeScript and production-bundle assertion. Existing >500 kB chunk warning remains. The real browser loaded this final production asset. |
| Backend `ruff check .`; `python tests/check_security.py`; harness Ruff | PASS after final fixture edits. |
| `git diff --check`, exact 25-path inventory and excluded-file SHA256 comparison | PASS. Final source review found no further in-scope code correction; first-push approval remains withheld by the gates below. |
| Fresh `npm audit --audit-level=high` | **FAIL**, exit 1: installed/locked Vite 6.4.3, one aggregate High vulnerability with three launch-editor advisories. Earlier zero-vulnerability result is superseded. |
| Fresh `python -m pip_audit --progress-spinner off` | **FAIL**, exit 1: installed certifi 2026.7.22, `PYSEC-2026-4320`, fixed version reported 2026.10.19. Two local project distributions remain unauditable as local source projects. Earlier clean third-party audit is superseded. |

The Vite advisory [GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm) and related [GHSA-698v-4r3x-3vcv](https://github.com/advisories/GHSA-698v-4r3x-3vcv) / [GHSA-r825-w8mm-5pxw](https://github.com/advisories/GHSA-r825-w8mm-5pxw) list Vite **6.4.4** as the patch on this release line; registry availability was read-only verified. The [certifi maintainer advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) and audit identify the certificate-bundle issue. No exploit was attempted, and no exposure of a protected runtime is claimed.

**Precise PM disposition requested:** authorize a separately bounded dependency correction for `frontend/package-lock.json` (Vite 6.4.3 → 6.4.4, compatible with the existing `^6.4.3` manifest), plus refresh certifi in the named local Python test environment to 2026.10.19 or later. No Python requirements lock is tracked in this repository; reproducible deployment pinning, if required, needs its own explicit path decision. These are proposals only: no `npm audit fix`, install/upgrade, manifest/lock mutation or dependency suppression was performed. The F02 handoff explicitly excludes dependencies and requires Local Saturation before first push. After authorization, renew audits, affected tests/build and final browser bundle evidence before delivery.

### D8 reconciliation — no skipped check promoted to PASS

| Row | Disposition and evidence |
| --- | --- |
| A01 | PASS: atomic defaults/API/PG plus real-browser required name, optional description, no code and correct Intake navigation. |
| A02 | PASS: strict schema/duplicate JSON/Unicode/raw and normalized bounds; focused/API tests. |
| A03 | PASS: Python/frontend canonical vectors, scalar boundaries, actual PG forced digest collision with exact-byte comparison. |
| A04 | PASS: immutable replay after Project edits; zero extra facts. |
| A05 | PASS: changed-body conflict, unchanged committed receipt and explicit browser GET/open without claiming rejected content saved. |
| A06 | PASS: independent PG connections, barriers and observed same-key advisory waiter. |
| A07 | PASS: different payloads in both winner orders. |
| A08 | PASS: fully rolled-back X leaves no binding; waiting Y may commit first; later X conflicts. Option A unchanged. |
| A09 | PASS: same-key replay after full rollback. |
| A10 | PASS: actor rollback, independent actor/tenant nonce tuples, foreign GET masking. |
| A11 | PASS: real subprocess death after each of three flush stages and zero surviving facts. |
| A12 | PASS: real PG commit-ack loss and browser truncated HTTP response; fresh GET original identity without replacement POST. |
| A13 | PASS: audit/receipt/constraint failures and database-aborted commit remain atomic. |
| A14 | PASS: five-second lock ceiling, actual cancellation and deadlock; transaction release and safe later replay. |
| A15 | PASS: forced hash-collision waiter serializes independent keys without merging receipts. |
| A16 | PASS: UUID PK/numeric legacy code and concurrent legacy collision preserve historical identity. |
| A17 | PASS: generated numeric/UUID resolution and retained legacy resolver regressions. |
| A18 | PASS: affected explicit-code/lifecycle/Analysis/Result/Intake regressions; no broader legacy atomicity claim. |
| A19 | PASS: deliberately distinct keys may create same-name Projects. |
| A20 | PASS: actual cookie/API CSRF/Origin/RBAC/expiry/inactive/tenant matrix; browser viewer and fresh cross-tenant 404 masking. |
| A21 | PASS: GET during flushed uncommitted POST, both later commit and rollback, with no visible writes or command lock. |
| A22 | PASS: real browser double-click/keyboard, slow held response, route unmount, malformed/truncated success and failed Intake GET; recovery opens same Project, no automatic POST or route takeover after leaving. |
| A23 | PASS: real-browser sole expired-session denial retained; prior uncertainty followed by synthetic later 401/422/CSRF 403 preserved same nonce. Five deliberate sends total in that schedule; refresh counter zero; later explicit same-body replay yields exactly one Project/audit/receipt. Synthetic envelopes test UI behavior; actual security gates remain proven by cookie/API cases. |
| A24 | PASS: explicit exact frozen-body replay, reload/lost-body GET-only, logout/actor/tenant late-response quarantine. |
| A25 | PASS: real-browser denied/quota/corrupt storage and unavailable CSPRNG block dispatch; post-dispatch quota preserves acknowledged identity/support/export. No automatic replacement or unsafe memory-only create. |
| A26 | **PARTIAL**: actual reload, logout/login, other tenant, late response, cross-tenant denial, back navigation, handle export and actual tab closure/fresh-tab loss verified. Restored-storage fixture in the real browser correctly showed GET-only parked state, reopened the exact COMMITTED Project and made zero POST/refresh calls. Native undo-close/browser tab restoration itself is unavailable: the supported shortcut restored no tab. This fixture is supplemental and is not represented as native restore evidence. Gate Owner must disposition that remaining schedule or provide a browser with native restore control; no after-deletion guarantee is added. |
| A27 | PASS: park/support/ordinary navigation, old marker retained, explicitly distinct intent and fresh acknowledgment per accepted submit; F01 regression and actual browser proof. |
| A28 | PASS: additive synthetic-history migration, cross-scope/duplicate constraints, actual empty/populated D7 refusal with exact rows/version retained. |
| A29 | PASS: compatible application rollback retains recovery; bare old-node 404 remains unavailable, no legacy POST fallback. |
| A30 | PASS: digest/audit/payload/code integrity faults never create or falsely report COMMITTED. |
| A31 | PASS: F02 real-browser theme/computed-style/1280px/960px/multi-intent/focus/feedback evidence on final production bundle. |

A26 restoration coverage is reported separately because the Operating Protocol says an unavailable required check remains incomplete. A reload/fixture test does not silently waive that scenario. T3 browser is therefore PARTIAL even though F02 and the other remaining rows are closed. No overall 31/31 PASS is claimed.

At this stop, every task-created browser tab was closed and the viewport restored to 1280×800. Only the command-line-verified task API/preview listeners and label/localhost-binding-verified #217 PostgreSQL container were stopped; its volume/data remain retained. No protected runtime was stopped. The final private SHA256 manifest records all 25 preserved working-copy files.

### Current TASK_STATE / stop boundary

```text
TASK_ID: VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT
PROJECT_AUTHORITY_READY: YES for bounded F02 work; dependency expansion NOT_AUTHORIZED
MODEL_USED: gpt-6.1-sol / high local configuration/catalog; no independent runtime attestation
BASELINE_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b
F02_ROOT_CAUSE: verified missing feature Fluent theme context plus missing local action/entry spacing
F02_FIX_PATHS: two feature presentation files, approved recovery test and E2E harness; evidence updated
F02_SCOPE_COMPLIANCE: YES; exact 25 paths, excluded files byte-identical
FLUENT_THEME_CONTEXT: feature-local FluentProvider/webLightTheme verified in production DOM
F02_BEFORE_AFTER_EVIDENCE: private-evidence/issue217-f02-20261021, 1280x800 and 960x800
A31_BROWSER_RESULT: PASS; F02 resolved
A22_RESULT: PASS
A23_RESULT: PASS
A25_RESULT: PASS
A26_RESULT: PARTIAL; native closed-tab restore unavailable, fixture/reload evidence explicitly bounded
A01_A31_RECONCILIATION: 30 PASS, A26 PARTIAL; no total PASS
T0_RESULT: PASS; retained 107 focused backend/API/PG/migration and current frontend focused coverage
T1_RESULT: PASS; frontend 557, unchanged affected backend regressions retained
T2_RESULT: FAIL; fresh npm High and pip certifi audit findings; lint/type/build/source-security PASS
T3_POSTGRESQL_RESULT: PASS; unchanged source/raw logs verified, 107 combined and 45 historical, zero skips
T3_BROWSER_RESULT: PARTIAL; native A26 restore schedule remains unverified
TOTAL_CHANGED_PATHS: 25
D7_RETENTION: PASS; implementation unchanged, empty/populated rows/version preserved after refusal
LOCAL_SATURATION_GATE: NOT_PASS
FIRST_PUSH_MATURITY: NOT_REACHED / NO_PUSH
DRAFT_PR_URL: NOT_CREATED
FROZEN_PR_HEAD: NONE
AUTO_CI_RUN: NONE
AUTO_CI_STATUS: NOT_TRIGGERED
REVIEWER_A: NOT_RUN
REVIEWER_B: NOT_RUN
MERGE: NOT_AUTHORIZED
PO_UAT: NOT_RUN
BLOCKERS: excluded-scope dependency security correction; native A26 restore capability/disposition
READY_FOR_PM_REVIEW: YES for blocker disposition only; NO for candidate certification
NEXT_AUTHORIZED_ACTION: PM/Gate Owner bounded dependency amendment and A26 test-capability/evidence disposition
```

## Historical stop — F01 repaired; F02 visual acceptance failed

Date: 2026-10-21, Asia/Saigon. **STOPPED_BROWSER_T3_F02; LOCAL SATURATION NOT PASS.** This section supersedes every checkpoint below. The Product Owner's direct continuation instruction authorized resuming the previously reported F01 repair within the existing scope. No commit, stage, push, PR, reviewer/provider call, manual CI, deployment or PO UAT occurred. Task-created browser tabs were closed and the viewport reset; only the verified task API/preview processes and #217 disposable PostgreSQL container were stopped, retaining its data.

### Authority, preservation and isolation

Fetched live main and task HEAD remain `85adc2280b929381aa2f03dc0d915f3cc36e441b`; CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`; exact-main CI #674/run `39269296495` completed/success on that SHA; #217 OPEN. The existing `codex/issue217-preliminary-create-implement` worktree retains exactly D9's 22 paths plus the three approved historical tests. Local configuration/catalog selects `gpt-6.1-sol`/`high`; no independent model attestation or provider execution is claimed.

The API fixture on `127.0.0.1:8017` uses only the labeled `valora-issue217-disposable-pg16` container, PostgreSQL 16.15 at `127.0.0.1:55417`, database `valora_issue217_disposable`, migration head `0a1b2c3d4e5f`. Read-only inventory found zero organizations outside the known synthetic fixture patterns (341 total at this continuation's bootstrap). Synthetic owner/viewer accounts and task-scoped permissions were reverified. Browser tests used an empty in-app-browser session, task-created tabs and 1280×800 viewport; no personal browser state was inspected or used. No Work/browser security policy changed.

Frontend final tests/build ran first; the final real-browser checks used that production bundle through a separate localhost preview process on 5417, with canonical browser/frontend/API origin `http://127.0.0.1:8017`. Earlier developer observations used Vite development serving; those are separately retained. Protected #199/#203 runtimes and #205 artifacts were not connected, restarted, migrated or mutated.

### Findings and changes

**F01 / D5 / A27: RESOLVED.** The distinct-intent acknowledgment now clears when its submit is accepted by the UI guard, while that send still receives the captured acknowledgment. The next parked or recovered intent requires a fresh acknowledgment. Two new component regressions first reproduced the existing defect (**2 failed, 2 passed**); the corrected focused frontend run passed **16 tests**. The real browser reproduced the previous conflict/recovery schedule and observed `createEnabled=false`, `checked=false`. The old parked locator remained present. Rejected content was never labeled saved. No nonce, adapter, domain, migration or shared auth policy changed for this repair.

**F02 / Frontend Architecture Rule / A31: OPEN, mandatory STOP.** The newly introduced Fluent Button/Input/Checkbox controls have no Fluent theme provider in this create/recovery surface. On the actual production build, recovery actions run together and controls lose their expected visual boundaries. Read-only DOM/computed-style evidence observed empty `--colorBrandBackground` and `--spacingHorizontalM`, button padding `0px`, and border `0px none`. Other existing Fluent feature regions explicitly establish `FluentProvider theme={webLightTheme}`; neither this surface nor App establishes that context. This is a task-owned presentation/Level-1 visual-integrity failure, not a browser permission or database-isolation failure. No fix, new theme system or broader provider refactor was attempted after observing F02, under the handoff's stop-on-contract-violation condition.

Sanitized local artifacts are retained outside Git under `private-evidence/issue217-resume-20261020`: `browser-stale-distinct-ack.*` (original F01), `browser-f01-fixed.json/png`, `browser-f02-unstyled-controls.png`, and its DOM snapshot; raw focused/frontend test logs; HTTP-fault evidence. No credentials or client data are added to this document. The fixture's synthetic HTTP truncation intentionally produces a server protocol error after the real business commit; the browser correctly keeps uncertainty, rather than treating that expected injected error as a rolled-back command.

### Verification commands and observed outcomes

All Python commands used the existing Python 3.12 task virtual environment. Database commands were wrapped by a private launcher that validates the task container label and exact localhost binding and supplies only the disposable database settings; its credential values are not published. API unit fixtures retain their explicit localhost CORS configuration; actual browser/API origin remains canonical 127.0.0.1.

| Command/check | Observed outcome and validity |
| --- | --- |
| `pytest tests/test_preliminary_project_create.py tests/test_preliminary_project_create_api.py tests/test_preliminary_project_create_postgresql.py tests/test_preliminary_project_create_migration.py -q --tb=short --disable-warnings -rs -x` | **107 passed**, 0 failed/skipped, 14 existing warnings, 34.11s. Final expanded focused/API/PG/migration run. Supersedes overlapping earlier 82/32/46 runs; counts are not additive. |
| `npm test -- --run src/components/precase/__tests__/PreliminaryRequestCreatePage.test.tsx src/components/precase/__tests__/preliminaryCreateIntent.test.ts src/components/precase/__tests__/PreliminaryCreateRecovery.test.tsx src/api/__tests__/preliminaryCreate.test.ts src/__tests__/App.preliminaryCreate.test.tsx` | **5 files / 16 tests passed** after F01; superseded by full frontend run. |
| `npm test` | **68 files / 555 tests passed**, 0 failed/skipped; 7.67s; includes both new F01 regressions. |
| `npm run lint`; `npm run build` | PASS; production-bundle assertion PASS; existing >500 kB chunk warning retained. Browser tested this build. |
| `ruff check .`; `python tests/check_security.py` from backend; `ruff check tests/e2e/issue217_preliminary_create.py` | PASS before the last test-only API/PG/HTTP-fault extensions. Product backend files were unchanged; final post-extension static closeout remains pending at STOP. |
| Three historical migration suites, exact commands/results in the earlier checkpoint | Retained **45 passed**, zero skipped; those files remain unchanged in this continuation. Their own raw logs were read and preserved. |
| Earlier affected backend create/auth regression and lifecycle/Analysis/Result/Intake runs | Retained **152 passed** and **202 passed** respectively, as historical working-copy evidence; overlapping tests are not summed. No production backend source changed during either browser continuation. |
| `git diff --check`; path inventory | PASS after evidence update. Exact comparison with the preserved original manifest confirms the same 25 authorized paths, zero staged files and byte-identical D7 migration implementation. Full final-diff approval and Local Saturation not reached. |

The final 107-test run includes newly added real cancellation/deadlock, observed advisory-lock collision serialization for distinct keys, PK/concurrent legacy-code collision, actor rollback/independent nonce scope, flushed-uncommitted GET commit/rollback schedules, aborted commit, mismatched audit/code corruption, idle/absolute expiry and inactive organization, cross-scope/duplicate evidence constraint attempts, and empty/populated D7 refusal/row retention. No new database or runtime implementation was introduced to make these pass.

### D8 acceptance reconciliation at STOP

PASS below applies only to the named acceptance row and cited evidence. A partial browser row and F02 are mandatory unfinished gates; none counts as PASS or N/A. Unit/API/PG cases are not presented as browser tests.

| Row | Required evidence | Disposition |
| --- | --- | --- |
| A01 | Focused/API/PG atomic defaults; browser name/optional description/no code and Intake | PASS; synthetic single Project/audit/receipt and prior real-browser double-click/Intake proof retained. |
| A02 | Strict schema/JSON/Unicode rejection | PASS; final focused/API suite. |
| A03 | Canonical equivalence/distinction/scalars/B-H collision | PASS; focused Python/frontend vectors and actual PG digest-collision comparison. |
| A04 | Immutable same-key replay after Project edits | PASS; PG proof plus API GET/replay. |
| A05 | Changed-payload POST conflict; GET COMMITTED | PASS; PG and real-browser competing-payload/explicit recovery schedule; F01 resolved separately. |
| A06 | Same-key concurrent connections and observed waiter | PASS; actual PG barriers and lock observation. |
| A07 | Different payloads, both winner orders | PASS; parametrized PG schedules. |
| A08 | Fully rolled-back winner leaves no binding | PASS; both PG schedules, original payload later conflicts with committed other payload. |
| A09 | Same-key replay after full rollback | PASS; actual rollback/fault/replay proofs. |
| A10 | Actor rollback and independent actor/tenant nonce scopes | PASS; expanded PG plus real-cookie API masking. |
| A11 | Process death after each of three flush stages | PASS; subprocess exit/zero-facts/replay proofs. |
| A12 | Commit acknowledgment and HTTP response loss | PASS; actual PG after-commit acknowledgment fault; real-browser truncated Content-Length connection close; fresh GET exact identity, no replacement POST. |
| A13 | Audit/receipt/aborted-commit atomicity | PASS; expanded PG fault/constraint tests. |
| A14 | Lock ceiling, cancellation, real deadlock | PASS; actual PG schedules, typed non-final unresolved and safe replay. |
| A15 | Forced hash collision for distinct keys | PASS; final PG observed waiter/serialization and two independent correct receipts. |
| A16 | PK/code collision, concurrent legacy writer | PASS; final PG proofs preserve legacy identity and zero extra evidence. |
| A17 | Generated numeric/UUID and retained code/name/slug resolution | PASS; final API generated-code proof and unchanged historical resolver regression. |
| A18 | Legacy explicit-code/lifecycle/Analysis/Result/Intake | PASS; retained affected regressions and final API legacy create; no claim of repairing legacy two-commit behavior. |
| A19 | Same name, intentionally distinct keys | PASS; PG creates two legitimate Projects. |
| A20 | Cookie/session/CSRF/Origin/tenant/RBAC | PASS for exercised matrix; final API suite includes idle/absolute expiry/inactive org; PG auth recheck and earlier browser viewer masking retained. |
| A21 | GET during flushed uncommitted POST, commit and rollback | PASS; new real-connection schedules, read-only zero visible facts then correct later result. |
| A22 | Duplicate/slow/unmount/malformed success/navigation | PARTIAL; double-click/held response/route-unmount/malformed body observed; final complete failed-navigation reconciliation pending. |
| A23 | Auth/CSRF rejection and preservation of prior uncertainty | PARTIAL; browser sole expired POST and same-intent later CSRF denial preserved; complete later-401/422 browser reconciliation pending. |
| A24 | Frozen same-body replay/lost bytes/reload/wrong-account late response | PASS for executed unit/browser schedules; logout cleared volatile payload and late owner response did not disclose/navigate as viewer. |
| A25 | Denied/quota/corrupt storage/CSPRNG/post-dispatch failure | PARTIAL; denied storage, no CSPRNG and post-dispatch persistence failure observed; corrupt-marker and pre-dispatch quota browser completion pending. |
| A26 | Reload/logout/tenant/back/tab restore/lost locator | PARTIAL; reload and actor-switch/late-response checks observed; full tenant/tab/back matrix remains pending. |
| A27 | Parking, safe exit and explicit distinct intent | PASS for F01 repair proof; old marker retained, fresh acknowledgement required after each accepted submit, parked/committed unit cases and real conflict/recovery case. |
| A28 | Additive migration/constraints/retention | PASS; final real PG migration/constraint evidence; historical suites retained. |
| A29 | Application rollback retains GET; untyped old-node 404 | PASS for PG activation and browser old-node checks; no legacy POST fallback. |
| A30 | Corrupt digest/audit/code cannot create or return false COMMITTED | PASS; final PG digest plus three mismatched-evidence variants. |
| A31 | Keyboard/focus/Vietnamese/Fluent layout at 1280px | FAIL: F02 missing Fluent theme context and merged/unstyled recovery controls. Keyboard/focus observations do not waive visual failure. |

### Current TASK_STATE / required report

```text
TASK_ID: VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT
PROJECT_AUTHORITY_READY: YES
MODEL_USED: gpt-6.1-sol / high local configuration/catalog; no independent runtime attestation
BASELINE_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b
EXACT_MAIN_CI: #674 / 39269296495 / completed-success on exact baseline
BROWSER_CAPABILITY: PASS
DEVELOPER_BROWSER_ENV_READY: YES
CANONICAL_URL: http://127.0.0.1:8017
SYNTHETIC_DATA_ISOLATION: VERIFIED; task-only PostgreSQL16; #199/#203/#205 untouched
T0_RESULT: PASS for 107 focused/backend and 16 focused/frontend tests; counts overlap later gates
T1_RESULT: PASS retained affected regressions; final frontend 555 PASS
T2_RESULT: Frontend PASS; product backend static/security PASS; final test-only static reconciliation pending at STOP
T3_POSTGRESQL_RESULT: PASS for required PG rows; final focused/API/PG/migration run 107 PASS, zero skips
T3_BROWSER_RESULT: FAIL / INCOMPLETE; F01 resolved, F02 open
A01_A31_MATRIX: row-by-row reconciliation above; no total PASS
FAILED_OR_BLOCKED_CASES: A31/F02; A22/A23/A25/A26 incomplete
D7_RETENTION_PROOF: empty/populated refusal and exact row/version retention PASS; migration implementation unchanged
CHANGED_PATHS: 25, original D9 22 plus exactly three approved historical test files
SCOPE_COMPLIANCE: YES for path inventory; final full diff review not reached
LOCAL_SATURATION_GATE: NOT_PASS
FIRST_PUSH_MATURITY: NOT_REACHED / NO_PUSH
IMPLEMENTATION_BRANCH: codex/issue217-preliminary-create-implement
IMPLEMENTATION_HEAD: 85adc2280b929381aa2f03dc0d915f3cc36e441b plus uncommitted task changes
DRAFT_PR_URL: NOT_CREATED
FROZEN_PR_HEAD: NONE
AUTO_CI_RUN: NONE
AUTO_CI_STATUS: NOT_TRIGGERED
REVIEWER_A: NOT_RUN
REVIEWER_B: NOT_RUN
MERGE: NOT_AUTHORIZED
PO_UAT: NOT_RUN
UNRESOLVED_FINDINGS: F02; remaining browser rows and final local verification incomplete
READY_FOR_PM_REVIEW: NO (blocker handoff only)
NEXT_AUTHORIZED_ACTION: PM/Gate Owner disposition of F02 and bounded continuation, then remaining browser/matrix/static/diff gates before any push
```

## Historical continuation — Browser T3 recovery acknowledgment repair

Date: 2026-10-21, Asia/Saigon. **IN DEVELOPMENT; LOCAL SATURATION NOT PASS.** This section supersedes the historical checkpoints below. The Product Owner's direct instruction to continue follows the reported Browser T3 failure; remediation remains within the existing 25-path scope. No provider/reviewer, commit, push, PR, integration or UAT action has occurred.

Rebootstrap fetched live main: `85adc2280b929381aa2f03dc0d915f3cc36e441b`; CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`; exact-main CI #674/run `39269296495` completed/success; #217 OPEN. Original implementation branch and all 25 task-owned files remain preserved. Browser capability was available in the preceding execution. The task runtime was stopped with its disposable data retained; protected runtimes were untouched.

The real-browser finding is `F01 / A27`: a distinct-intent checkbox remained checked after the request it authorized recovered as COMMITTED following POST_CONFLICT. The Create button was enabled with the rejected form content still present, without a fresh distinct-intent acknowledgment. Sanitized local screenshot, complete DOM/accessibility snapshots and observed `createEnabled=true` / `distinctAcknowledgementChecked=true` are retained under `private-evidence/issue217-resume-20261020`. No extra create was dispatched to demonstrate the risk. Product implementation had not been changed when that continuation stopped.

Pre-stop verification added only authorized tests/harness coverage: focused canonicalization/API/PG run **82 passed**; expanded PG/migration run **46 passed**, zero failures/skips; earlier intermediate expanded PG **32 passed** is superseded, not additive. The final 46 include real cancellation/deadlock, PK and concurrent legacy-code collisions, actor rollback/independent nonce scope, uncommitted GET commit/rollback schedules, mismatched audit/code rejection, cross-scope/duplicate evidence constraints, and both D7 retention cases. The three historical migration suites' **45 passed** and final frontend **553 passed**, lint/build and backend static/security results are retained historical evidence, subject to affected-check revalidation after this repair. No total A01–A31 PASS is claimed.

### TASK_STATE

```text
TASK_ID: VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT
PHASE: BROWSER_T3_RESUME_F01_REPAIR
PROJECT_AUTHORITY_READY: YES
BASELINE_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b
IMPLEMENTATION_BRANCH: codex/issue217-preliminary-create-implement
IMPLEMENTATION_HEAD: baseline plus 25 uncommitted task-owned paths
T3_POSTGRESQL_RESULT: 46 focused/expanded tests PASS; final matrix reconciliation pending
T3_BROWSER_RESULT: F01 observed; repair and remaining matrix pending
LOCAL_SATURATION_GATE: NOT_PASS
FIRST_PUSH_MATURITY: NOT_REACHED
DRAFT_PR_URL: NOT_CREATED
REVIEWER_A: NOT_RUN
REVIEWER_B: NOT_RUN
PO_UAT: NOT_RUN
READY_FOR_PM_REVIEW: NO
NEXT_AUTHORIZED_ACTION: Consume each distinct-intent acknowledgment once; revalidate affected tests and browser matrix before delivery
```

## Historical resume checkpoint — D9-MIGRATION-TEST-SCOPE-FIX

Date: 2026-10-20, Asia/Saigon. **STOPPED_REQUIRED_BROWSER_UNAVAILABLE; LOCAL SATURATION INCOMPLETE.** The historical migration scope conflict below is resolved. This current checkpoint supersedes the earlier stop-state fields retained later in this document. No implementation/source certification is claimed.

Live [PM amendment `6294587539`](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6294587539) was retrieved and verified before edits. Existing worktree/branch and all original 22 paths were preserved. Main remains `85adc2280b929381aa2f03dc0d915f3cc36e441b`, CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`, exact push/main CI #674/run `39269296495` completed/success. Issue #217 is OPEN; no #217 implementation PR exists. Local model catalog continues listing `gpt-6.1-sol` with `high`; no substitution/provider/reviewer calls. Session-bootstrap and worktree-resume applied; read-only status/diff inspection preceded edits.

### Approved changes in this continuation

Only the three authorized historical test paths, the original #217 migration test and this existing evidence document changed during the resume. No product-source or migration implementation was changed. No historical assertion was deleted or replaced with an unrelated D7 assertion. No skip/xfail or workflow/dependency edits were introduced.

| Path | Correction and preserved coverage |
| --- | --- |
| `backend/tests/test_g11b_lifecycle_postgresql.py` | Historical receipt roundtrip/refusal setup stops at verified D7 parent `f9a0b1c2d3e4`; original G1.1B nonempty receipt refusal and retained version/receipt assertions unchanged. All other runtime scenarios still use live `head`. |
| `backend/tests/test_g11a_foundation_postgresql.py` | Parametrize the nullable Customer/ownership fixture at both live head and pre-D7. Both exercise all ownership/lineage constraints; only the pre-D7 case attempts the historical downgrade and asserts the original `unbound Customer history` refusal. Other historical backfill, representability and runtime tests remain intact. |
| `backend/tests/test_s12_pr_004_proof_matrix.py` | Historical lineage upgrade/DML/downgrade cycle runs through pre-D7; its final upgrade still reaches live head and now repeats the schema and full DML constraint proof there. No downgrade crosses D7. |
| `backend/tests/test_preliminary_project_create_migration.py` | The isolated synthetic historical-data upgrade proof now runs separately with empty and populated new receipt tables. Populated evidence comes from the actual command service on that new database. A real Alembic downgrade attempt must refuse; exact Project/audit/receipt rows and Alembic revision must equal their pre-attempt snapshots in both cases. |

Migration graph revalidated: one head `0a1b2c3d4e5f`, parent `f9a0b1c2d3e4`. D7 implementation remains unchanged and unconditionally refuses downgrade. Tests ran only on the existing task-owned disposable PostgreSQL 16.15 server, localhost port 55417, with newly created disposable databases for historical migration cycles. No protected database or original design document was modified. The task-owned PostgreSQL container was stopped again after evidence capture; its data was retained.

### Resume verification results

| Command/check | Raw result |
| --- | --- |
| `pytest tests/test_g11b_lifecycle_postgresql.py tests/test_g11a_foundation_postgresql.py tests/test_s12_pr_004_proof_matrix.py -q --tb=short --disable-warnings -rs` | **45 passed**, 0 failed, 0 skipped; 14 existing warnings; 83.37s. Includes the exact previously failing G1.1B node, G1.1A old refusal, S12 historical cycle and current-head DML. |
| `pytest tests/test_preliminary_project_create_migration.py -q --tb=short --disable-warnings -rs` | **4 passed**, 0 failed, 0 skipped; 13 existing warnings; 15.56s. Includes empty and populated D7 refusal, row preservation and unchanged version. |
| Frontend `npm test` | **68 files / 553 tests passed**, 0 failed/skipped; 10.11s. Final feedback-focus addition included. |
| Frontend `npm run lint` and `npm run build` | PASS; production bundle assertion PASS. Existing large-bundle warning retained. |
| Backend whole-tree `ruff check .`, `python tests/check_security.py`, test harness Ruff | PASS after resume edits. |
| Alembic single-head check and `git diff --check` | PASS. |
| Git inventory | **25 changed paths** = original D9 22 plus exactly the three PM-approved tests; all uncommitted; no staged files, commit, push or Draft PR. |

Raw historical-suite and D7 logs are retained in the task's private local evidence directory as `historical-tests.log` and `d7-tests.log`; no private paths/credentials are published here. This continuation recorded zero test failures/skips. Earlier outcomes below remain historical, not added to these counts. Previously passed unchanged-source focused/API/lifecycle/PG tests remain recorded; they were not expensively repeated without a new affected-source reason. Full final T0–T3 completion is not claimed.

### Required browser blocker

The connected Browser capability rejected `browser.tabs.list()` with **`Local browser use is disabled in Work settings`**. The documented bootstrap-troubleshooting request returned the identical denial. No browser interaction, fault scenario, bypass, alternative automation surface, or settings modification was performed during this continuation. Browser availability from the preceding run is not current evidence.

Consequently remaining real-browser T3 scenarios from A22–A31, final matrix reconciliation and a full Local Saturation PASS cannot be completed in this run. Prior screenshots/partial browser observations below are retained as prior evidence only. No mandatory unavailable browser test is marked PASS or N/A. Follow the user-required STOP boundary; do not push to obtain this missing local evidence through CI.

### Historical TASK_STATE / final handoff

```text
TASK_ID: VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT
PROJECT_AUTHORITY_READY: YES; STOPPED_REQUIRED_BROWSER_UNAVAILABLE
MODEL_USED: gpt-6.1-sol / high local catalog/configuration; no independent runtime attestation
BASELINE_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b
CODEX_BLOB: dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e
BASELINE_CI: #674 / 39269296495 / exact push-main SHA / completed-success
D9_AMENDMENT: 6294587539 / D9_TEST_SCOPE_EXPANDED
ORIGINAL_22_PATHS_PRESERVED: YES
ADDITIONAL_TEST_PATHS: test_g11a_foundation_postgresql.py; test_g11b_lifecycle_postgresql.py; test_s12_pr_004_proof_matrix.py
TOTAL_CHANGED_PATHS: 25
SCOPE_COMPLIANCE: YES
G11A_HISTORICAL_PROOF: PASS, including original refusal and current-head ownership constraints
G11B_HISTORICAL_PROOF: PASS, including exact formerly failing migration node
S12_HISTORICAL_PROOF: PASS, including current-head schema/DML phase
D7_EMPTY_DOWNGRADE_REFUSAL: PASS, all snapshots/version retained
D7_POPULATED_DOWNGRADE_REFUSAL: PASS, all snapshots/version retained
T0_RESULT: PASS for resumed focused migration scope; original focused results retained
T1_RESULT: Historical blocker resolved; 45 affected tests PASS; prior unchanged-source regressions retained
T2_RESULT: PASS, final frontend tests/lint/build and backend static/security checks
T3_POSTGRESQL_RESULT: All resumed migration proofs PASS; full acceptance reconciliation pending
T3_BROWSER_RESULT: INCOMPLETE; browser disabled in Work settings
LOCAL_SATURATION_GATE: INCOMPLETE / NOT_PASS
FIRST_PUSH_MATURITY: NOT_REACHED / NO_PUSH
IMPLEMENTATION_BRANCH: codex/issue217-preliminary-create-implement
IMPLEMENTATION_HEAD_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b; uncommitted, no candidate HEAD
DRAFT_PR_URL: NOT_CREATED
PR_HEAD_SHA: NONE
AUTO_CI_RUN_URL: NONE
AUTO_CI_STATUS: NOT_TRIGGERED
AUTO_CI_CONCLUSION: N/A
REVIEWER_A: NOT_RUN
REVIEWER_B: NOT_RUN
MERGE: NOT_AUTHORIZED
PO_UAT: NOT_RUN
KNOWN_LIMITATIONS: Remaining browser matrix and final acceptance/diff completion still required
UNRESOLVED_FINDINGS: Required local Browser capability disabled; no remaining observed migration blocker
READY_FOR_PM_REVIEW: NO (blocker/status handoff only)
NEXT_AUTHORIZED_ACTION: Restore local Browser access in Work settings, rebootstrap, finish required T3/matrix and Local Saturation before any push
```

## Previous stop record — retained historical evidence

Date: 2026-10-20, Asia/Saigon. Status: **STOPPED_SCOPE_CONFLICT; NOT READY FOR PM CANDIDATE REVIEW**. This is an uncommitted local checkpoint, not a release, certification or completed acceptance report.

## Authority and scope

- Task: `VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT`.
- Accepted contract: [D1–D9, Option A](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6293809877), authorized by [PM implementation release](https://github.com/Reguluspt/valora-engineering/issues/217#issuecomment-6293908887).
- Verified execution baseline: `main@85adc2280b929381aa2f03dc0d915f3cc36e441b`; CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`; CI #674, run `39269296495`, push/main, exact SHA, completed/success; all five jobs success.
- Model availability/configuration: local catalog lists `gpt-6.1-sol` with `high`; local configuration selects that model and effort. This is configuration evidence, not an independent runtime model attestation. No other provider or reviewer invoked.
- Dedicated branch: `codex/issue217-preliminary-create-implement`; Git HEAD remains the baseline; source changes are uncommitted.
- Only D9's 22 paths are modified/created. No parallel agents. Existing design-worktree documents and protected #199/#203/#205 environments/artifacts remain untouched. No credentials, real client data, dependency changes or global configuration changes are included.
- Read session-bootstrap/live-authority/dev-handoff/PostgreSQL-proof skills, scoped CODEX, Guardrails, Operating Protocol V2, Compact Task Contract and Frontend Architecture Rule. `VALORA_LEAN_MCP`: no recall/capture/persistence.

## Confirmed blocker and requested scope amendment

D7 requires revision `0a1b2c3d4e5f` to refuse every downgrade before any DROP/DELETE, even with zero creation receipts. Historical tests upgrade to dynamic `head` and subsequently expect to downgrade through that revision. Preserving both the new retention contract and the existing test suite requires changes outside the current allowlist.

| Additional path requiring PM approval | Exact conflict | Evidence |
| --- | --- | --- |
| `backend/tests/test_g11b_lifecycle_postgresql.py` | Migration test upgrades to `RUNTIME_HEAD="head"` at line 104, then requires downgrade to historical `CURRENT` at line 109 | Executed on a new disposable database: **1 failed**, zero skipped; new migration raises its required retention exception |
| `backend/tests/test_g11a_foundation_postgresql.py` | Live-head fixture later expects the old downgrade error `unbound Customer history` at lines 249–251 | Source-confirmed: new unconditional refusal intercepts this historical expectation; this node was not executed |
| `backend/tests/test_s12_pr_004_proof_matrix.py` | Historical lineage proof upgrades to dynamic head at line 495 and expects downgrade to lineage parent at line 506 | Source-confirmed: downgrade crosses the new refusing revision; this node was not executed |

Minimal alternative for PM consideration: isolate those historical downgrade proofs at the verified pre-receipt revision in their own disposable fixtures, retaining separate live-head runtime/retention proofs. Preserve their original historical assertions, run the affected PostgreSQL regressions, and keep the new migration's unconditional refusal. This is a proposed test-scope amendment, not permission already exercised. Risk: weakening/pinning historical tests carelessly could lose current-schema regression coverage; scope the historical fixtures and retain current-head proofs explicitly.

No additional path has been edited. No skip, xfail, migration bypass, retention exception or workflow change was introduced to evade the failure. Implementation and delivery stop here pending Gate Owner disposition.

## Implemented local source, still subject to completion and review

Exact changed paths, verified against Git at stop (22; all within D9):

```text
backend/app/api/projects.py
backend/app/modules/project_master_data/models.py
backend/app/modules/project_master_data/preliminary_project_create_schemas.py
backend/app/modules/project_master_data/application/preliminary_project_create_service.py
backend/alembic/versions/0a1b2c3d4e5f_preliminary_project_create_receipts.py
backend/tests/test_projects_api.py
backend/tests/test_preliminary_project_create.py
backend/tests/test_preliminary_project_create_api.py
backend/tests/test_preliminary_project_create_postgresql.py
backend/tests/test_preliminary_project_create_migration.py
frontend/src/App.tsx
frontend/src/components/precase/PreliminaryRequestCreatePage.tsx
frontend/src/components/precase/__tests__/PreliminaryRequestCreatePage.test.tsx
frontend/src/api/preliminaryCreate.ts
frontend/src/api/__tests__/preliminaryCreate.test.ts
frontend/src/components/precase/preliminaryCreateIntent.ts
frontend/src/components/precase/PreliminaryCreateRecovery.tsx
frontend/src/components/precase/__tests__/preliminaryCreateIntent.test.ts
frontend/src/components/precase/__tests__/PreliminaryCreateRecovery.test.tsx
frontend/src/__tests__/App.preliminaryCreate.test.tsx
tests/e2e/issue217_preliminary_create.py
docs/implementation/VALORA_UAT203_217_PRELIMINARY_CREATE_CONTRACT.md
```

- Dedicated static POST and authenticated GET routes; strict duplicate-member JSON rejection, UUIDv4/scalar/raw/normalized validation, frozen NFC/trim/CRLF canonical bytes/digest and typed errors. Legacy explicit-code creation/resolver unchanged.
- Fresh READ COMMITTED Session and outer transaction; five-second advisory lock, fifteen-second statement ceiling, authorization recheck after lock, full-scope receipt lookup; Project, success audit and immutable receipt inserted atomically. Detached scalar DTO returned after acknowledged commit. Commit ambiguity remains unresolved.
- Server UUID and 39-decimal-digit code; receipt/audit candidate-key migration from freshly verified parent `f9a0b1c2d3e4`, restrictive tenant/actor/Project/audit FKs; no historical backfill; unconditional refusing downgrade.
- Application rollback control, feature-local `VALORA_PRELIMINARY_CREATE_ENABLED=false`: deny new receipt-absent creates before writes while retaining GET and committed replay. No rollout or deployment was performed.
- Feature-local adapter suppresses shared POST auto-refresh/replay. Scoped tab marker, volatile original body, duplicate-submit lock, explicit same-body replay after fresh typed-unresolved GET, committed identity reopening, logout/scope generation quarantine, recovery handle and parking/distinct-intent acknowledgement.
- Fluent primitives compose existing Valora presentation/CSS. No native coupling or new visual system. Name/description only, explicit Create/Cancel, recovery feedback and focus support.

## Executed checks and exact limits

All database mutation/fault/migration tests used a newly provisioned, dedicated `postgres:16` container (server **16.15**, localhost-only port 55417) with synthetic data. Migration historical-cycle tests and the blocker reproduction created additional new disposable databases on that same server. Protected database targets were not migrated. The auth concurrency test's separate `TEST_DATABASE_URL` was explicitly set to the same disposable server for its successful final run.

| Check / final recorded run | Raw result | Disposition |
| --- | --- | --- |
| `pytest tests/test_preliminary_project_create.py tests/test_preliminary_project_create_api.py tests/test_preliminary_project_create_postgresql.py tests/test_preliminary_project_create_migration.py tests/test_projects_api.py tests/test_g11e_precase_api.py tests/test_g11h_preliminary_management.py tests/test_auth_endpoints.py tests/test_auth_rbac_foundation.py -q --tb=short --disable-warnings -rs` | **152 passed**, 0 failed, 0 skipped; 14 existing warnings | Focused/new PG/API plus affected regressions passed at that checkpoint |
| `pytest tests/test_g11b_lifecycle_service.py tests/test_pr01_preliminary_analysis_service.py tests/test_pr01_preliminary_result_service.py tests/test_pr01_official_intake_service.py -q --tb=short --disable-warnings -rs` | **202 passed**, 0 failed, 0 skipped; 13 existing warnings | Additional legacy lifecycle/Analysis/Result/Intake service regression passed |
| `pytest tests/test_g11b_lifecycle_postgresql.py::test_receipt_migration_roundtrip_and_nonempty_downgrade_refusal -q --tb=short --disable-warnings -rs` | **1 failed**, 0 passed, 0 skipped; 13 existing warnings | Confirmed scope conflict; Local Saturation FAIL |
| Frontend `npm test` | **68 files / 553 tests passed**, 0 failed/skipped | Before the final recovery-feedback focus addition; final frontend rerun still required |
| Frontend focused adapter/intent/create/recovery/App run | **5 files / 14 tests passed** | Earlier focused checkpoint; included in the full run, not additive |
| Frontend lint, production build/bundle assertion | PASS | Build predates final feedback-focus addition; final rerun required. Existing large-bundle warning retained |
| `npm audit --audit-level=high` | **0 vulnerabilities** | Full dependency audit passed |
| Backend whole-tree Ruff and `tests/check_security.py` | PASS | Later final task-path Ruff recheck also PASS |
| `pip_audit --progress-spinner off` | No known vulnerabilities; **2 local project distributions unauditable** | `valora-backend`/`valora-worker` are local projects, not PyPI packages; this does not audit their own source |
| Alembic empty-to-head and synthetic-history additive upgrade | PASS | New single head `0a1b2c3d4e5f`; retained downgrade refusal proven |
| `git diff --check` | PASS | No commit/stage/push performed |

Earlier edit-loop failures were fixed within allowed paths: malformed Unicode reflected in a 422 response, fixture resolver URL/import/flush setup, route-order introspection, crash-test model initialization and a historical audit-count assumption. Earlier selected auth runs recorded one unavailable-PG skip; after setting its explicit test URL, the final 152-test run includes that test without skipping. These earlier failures/skips are not counted as PASS. The one out-of-scope historical migration conflict remains unresolved.

## Real browser observations

Used a separate local fixture on ports 5417/8017 and synthetic owner/viewer accounts, through the Browser skill. These are developer tests, not PO UAT scenarios. Task-created tabs and temporary viewport override were closed/reset at stop; only task-created frontend/backend fixture processes were stopped.

Observed at 1280×800:

1. Required Vietnamese name and optional description, no manual code field; keyboard Tab/Enter submission navigated to the server-created Project's Preliminary Intake.
2. A real successful commit followed by a deliberately incomplete success body left UNCERTAIN, blocked another initial create, and exposed read-only original payload/replay confirmation. No automatic POST.
3. Reload retained the request locator and lost the volatile payload; only GET recovery remained. Explicit GET recovered the original immutable identity without another POST.
4. A synthetic uncertain/uncommitted attempt returned typed UNRESOLVED; parking permitted navigation to other work and the shell returned to the retained marker. Explicit confirmation plus fresh GET replayed the same captured request ID/body successfully.
5. Logout/login as viewer showed denial and no owner marker details; returning as owner retained the owner's committed locator.
6. A separate test-only document with denied sessionStorage showed recovery/storage feedback and disabled Create, with no command dispatch.

Saved local screenshots `issue217-uncertain.png` and `issue217-recovered.png` outside the repository. No screenshot path was added to the allowlist. The test harness's startup fault controls remain test-only. The CSPRNG-unavailable document was opened but its outcome was **not verified** before the scope stop. Corrupt marker, post-dispatch storage failure and the complete browser A22–A31 matrix are **not certified complete**. Full A01–A31 coverage reconciliation remains pending; the above observations cannot be promoted to a total T3 PASS.

## TASK_STATE / required handoff fields

```text
TASK_ID: VALORA-UAT203-217-PRELIMINARY-CREATE-IMPLEMENT
PROJECT_AUTHORITY_READY: YES at bootstrap; implementation STOPPED_SCOPE_CONFLICT
MODEL_USED: local gpt-6.1-sol / high configuration; no provider substitution
BASELINE_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b
CODEX_BLOB: dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e
BASELINE_CI: #674 / 39269296495 / exact push-main SHA / completed-success
CONTRACT_VERSION: accepted D1-D9 / preliminary-create-v1 / Option A
IMPLEMENTATION_BRANCH: codex/issue217-preliminary-create-implement
IMPLEMENTATION_HEAD_SHA: 85adc2280b929381aa2f03dc0d915f3cc36e441b (uncommitted changes; no candidate HEAD)
CHANGED_PATHS: D9's 22 allowed paths; uncommitted
SCOPE_COMPLIANCE: YES; three further test paths proposed, not edited
ATOMICITY_IMPLEMENTED: local code and focused PG proof; final acceptance incomplete
IDEMPOTENCY_IMPLEMENTED: local code and scoped replay/race/rollback proof
RECOVERY_IMPLEMENTED: local code and partial real browser proof; full matrix incomplete
TENANT_CSRF_RBAC_PROOF: focused real-cookie API/PG matrix and browser viewer observations passed
LEGACY_COMPATIBILITY: selected regressions pass; historical migration-test compatibility blocked
MIGRATION_PROOF: isolated additive upgrade and refusing downgrade pass; historical test conflict remains
T0_RESULT: focused tests passed; not overall completion
T1_RESULT: FAIL (one confirmed out-of-scope migration regression); 354 other selected backend tests passed
T2_RESULT: static/security/audit checks passed; final frontend rerun pending
T3_POSTGRESQL_RESULT: focused proofs passed; overall gate blocked/incomplete
T3_BROWSER_RESULT: PARTIAL / INCOMPLETE
LOCAL_SATURATION_GATE: FAIL
FIRST_PUSH_MATURITY: NOT_REACHED / NO_PUSH
DRAFT_PR_URL: NOT_CREATED
PR_HEAD_SHA: NONE
AUTO_CI_RUN_URL: NONE
AUTO_CI_STATUS: NOT_TRIGGERED
AUTO_CI_CONCLUSION: N/A
REVIEWER_A: NOT_RUN
REVIEWER_B: NOT_RUN
MERGE: NOT_AUTHORIZED
PO_UAT: NOT_RUN
KNOWN_LIMITATIONS: uncommitted implementation; browser matrix and final verification incomplete
UNRESOLVED_FINDINGS: D7 unconditional retention refusal conflicts with historical live-head downgrade tests outside D9
READY_FOR_PM_REVIEW: NO (scope decision only)
NEXT_AUTHORIZED_ACTION: PM/Gate Owner resolves exact three-path test-scope amendment; rebootstrap before resuming
```

On resumption fetch/reverify live main, CODEX, exact CI, Issue/PR and this worktree. Do not silently rebaseline. Keep #217 open, #218 separate and #203 E2E-01 FAIL_OBSERVED / RETEST_PENDING. Do not push until the approved scope, all mandatory checks, final diff and Local Saturation Gate pass. No reviewer, Ready, merge, certification or UAT authority is inferred.
