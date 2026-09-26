# PR-07 OneDrive Personal conditional-commit conformance runbook — HISTORICAL DIRECT-WRITE RESEARCH

**Task:** `VALORA-PR07-CONFORMANCE-001` **Status:** G3 OPTION A APPROVED; G4 CLOSED
**Date:** 2026-09-19 **Authority:** accepted ADR 0042 and historical PR-07 implementation contract

**Current disposition note (2026-09-21):** This runbook is retained as historical evidence for the rejected direct OneDrive replacement path. It is not the current document-write roadmap. ADR 0043 moved accepted revision bytes to app-owned immutable storage; ADR 0045 governs Working-copy observation/review/human-confirmed revision. Do not rerun this provider-write research unless the Product Owner explicitly reopens direct replacement.

## Purpose

Document the bounded C2 research sequence without opening PR-07 runtime: the finalized
`C2_AUTO_V1` probe, its schema-v3 `C2_AUTO_V2` correction and each separately authorized live
observation. The probe tests whether an exact-item upload session created with frozen `If-Match`
and body `{}` protects a concurrent write when its second fragment automatically completes the
upload. A local PASS is only harness evidence; only a separately authorized live run can observe
provider behavior.

Microsoft documents the item-ID route for updating an existing file, a `412` response when the
upload-session `If-Match` is stale, and `fail` as the default upload conflict policy. It also
documents the explicit `sourceUrl` completion request for OneDrive Personal. The accepted boundary
still requires observed provider behavior rather than documentation alone.

## Isolation and safety

- use only a Product Owner-controlled Microsoft Personal account;
- use delegated `Files.ReadWrite`; do not use application permission, `Files.ReadWrite.All`,
  OneDrive for Business or SharePoint;
- supply the access token only through `VALORA_PR07_GRAPH_ACCESS_TOKEN` in the process environment;
- never paste the token into a command argument, shell history, repository file, report or chat;
- the probe refuses network access unless both write and cleanup acknowledgements are present;
- the probe creates one uniquely named root-level `.bin` item, never accepts an existing item ID or
  path, and moves that item to the OneDrive recycle bin in `finally`;
- provider IDs, eTags, upload URLs, contents and token material are excluded from stdout.

## Local command

The repository-owned controller is the only accepted operator entry point. Its exact no-network
surface can be exercised from any working directory without OAuth, Entra or Graph access:

```powershell
python backend/tools/pr07_onedrive_personal_live_controller.py --self-test --candidate C2_AUTO_V1
```

Do not invoke the probe directly for a future live attempt. A live controller invocation requires
both write acknowledgements, the exact registered app ID, a temporary client secret supplied only
through the process environment, and fresh action-time Product Owner approval. The controller uses
its own `sys.executable`, passes launcher arguments as an array with `shell=False`, and invokes the
repository-owned Node launcher exactly once without retry. Live mode rejects an alternate
`--evidence-directory`; its unresolved-attempt guard always uses the canonical Git-ignored
`local-artifacts/pr07/` ledger. Self-test mode may redirect evidence for isolated testing.

The only acceptable C2 observation has `candidate: C2_AUTO_V1`, `runtime_gate: BLOCKED`, fresh final
HTTP `200/201`, stale final HTTP `412`, all seven preservation/setup checks `true`,
`stale_candidate_observed: false`, cleanup `DELETED_TO_RECYCLE_BIN` and cleanup issue `NONE`.

## Required evidence

Each controller invocation whose evidence recorder initializes successfully writes a sanitized
atomic snapshot and append-only event journal under the Git-ignored `local-artifacts/pr07/`
directory. An evidence-initialization failure returns one sanitized stdout report and creates no
artifact. The artifacts record an attempt UUID, UTC controller/probe/request/cleanup stage events,
Git HEAD plus working-tree content/status hashes, component hashes, bounded dependency, Python,
Node and argv fingerprints, network state, sanitized launcher report and cleanup state. Do not
record account identity, item/drive IDs, eTags, bytes, token claims, authorization responses,
upload URLs, raw stderr or secrets.

The controller records `cloud_configuration` as outside its boundary. Temporary-secret and
delegated-permission creation/removal, plus preservation of the PR-05 baseline, require separate
Entra evidence before and after any authorized live attempt; the local artifacts must not be used
to claim those cloud lifecycle facts.

If any assertion fails, PR-07 remains blocked. Do not weaken the expected status, switch to a small
file upload, accept a create-session-only `412`, or begin runtime work on fake-provider evidence.

## Current disposition

On 2026-09-13, the first bounded attempt reached Microsoft Personal consent, but the controlled
browser blocked the registered `localhost` callback before token acquisition. A later manual
handoff reached the callback with mismatched OAuth state and therefore also stopped before token
acquisition. Neither attempt ran the probe or wrote OneDrive content.

The third attempt kept one exact OAuth state/PKCE flow through an external user-controlled browser.
It acquired a delegated token with `Files.ReadWrite`, verified a Personal drive and started the
probe. The probe created its isolated item, then Microsoft Graph returned HTTP `400` while creating
the first upload session. No staging or final commit occurred, so this result proves neither fresh
conditional commit nor stale `412` behavior. The probe's `finally` cleanup moved the isolated item
to the OneDrive recycle bin; no test content survived outside the recycle bin.

The old failure output intentionally omitted provider response data and therefore retained only the
HTTP status. The first minimization omitted optional `fileSize` while retaining the exact item,
`deferCommit: true`, explicit conflict behavior `fail`, and `If-Match`. Future upload-session
failures expose only a bounded provider error code plus explicit cleanup state; provider message
text, request IDs and response bodies remain excluded.

Cleanup was verified in Entra after the preceding attempts: all temporary PR-07 secrets and delegated
`Files.ReadWrite` were removed, delegated `Files.Read` remained, and the pre-existing PR-05 secret
was preserved. No authorization code, token or temporary secret was retained.

### Minimized live rerun — 2026-09-13

The minimized probe was rerun from `4e97548` plus the uncommitted probe/test changes that omit
`fileSize` and report bounded provider error codes and cleanup state. The result was recorded at
`2026-09-13 08:02:19 UTC` immediately after execution. OAuth state/PKCE and delegated
`Files.ReadWrite` succeeded, and the probe verified a Personal drive. The sanitized report was:

```json
{"cleanup":"DELETED_TO_RECYCLE_BIN","http_status":409,"provider_error_code":"nameAlreadyExists","reason":"Upload-session creation failed with HTTP 409.","status":"FAIL"}
```

The isolated item was created, but its first exact-item upload-session request failed with
`409 nameAlreadyExists`. No staging or final commit occurred. Omitting `fileSize` therefore did not
close the conformance gate. The existing-item request with conflict behavior `fail` needs further
investigation; this result does not establish whether final-commit `If-Match` is enforced. Do not
change the accepted conflict semantics or the required stale `412` assertion to manufacture PASS.

The previous temporary secret was explicitly deleted to free the credential slot. The replacement
secret was deleted after the probe, and configured delegated `Files.ReadWrite` was removed. Entra
then showed only the pre-existing PR-05 secret and configured delegated `Files.Read`. The isolated
test item was moved to the recycle bin by probe cleanup and is recoverable there. Removing a
configured permission is not evidence that a previously granted user consent or issued token has
been revoked; this run did not verify consent revocation. The token-bearing runner exited, and no
secret, authorization code or token was written to a repository file or report.

### Microsoft documentation diagnosis and local candidate — 2026-09-15

Microsoft's v1.0 operation reference says an existing-file upload session uses the exact item-ID
route, needs no request body, treats conflict behavior `fail` as the default, and returns `412` when
the supplied `If-Match` does not match. The general `driveItem` reference describes conflict
behavior as an annotation for actions that create a new item. The observed `409 nameAlreadyExists`
is therefore consistent with OneDrive Personal interpreting the explicitly supplied `item`
annotation as a name/create conflict during deferred session creation. Microsoft does not document
that exact combination or validation order, so this remains an evidence-based inference and may be
a provider quirk rather than proof that the original request was syntactically invalid.

The local probe now uses this next candidate for session creation:

```http
POST /v1.0/drives/{driveId}/items/{itemId}/createUploadSession
If-Match: {frozen eTag}
Content-Type: application/json

{"deferCommit":true}
```

Only the redundant explicit conflict annotation was removed from this POST. The candidate relies on
Microsoft's documented default `fail`; it retains the exact item-ID target, frozen `If-Match`,
deferred staging, immediate pre-commit reread, explicit conflict behavior `fail` on the final
`sourceUrl` PUT, and the mandatory stale-final-commit `412` assertion. This changes the OneDrive
Personal wire shape, not the intended conflict policy. Local mocks validate the shape and fail-closed
orchestration but cannot establish provider conformance.

Microsoft's final-commit example is path-based, while its general `driveItem` reference and the
operation example disagree on whether the conflict annotation belongs in the URL or JSON body. The
exact item-ID `sourceUrl` final PUT therefore remains provider-dependent and unproven. If the next
bounded run still returns `409` at session creation, or if the final request cannot pass fresh commit
and reject stale commit with `412`, stop and present the evidence to the Product Owner. Do not switch
to `replace`, `rename`, path binding, or small-file upload.

### Bounded exact-item candidate rerun — 2026-09-15

The exact-item candidate above was run once from `4e97548` plus the four preserved uncommitted
probe, test and evidence-file changes. The result was recorded at `2026-09-15 15:28 UTC`
immediately after the callback and probe completed. One OAuth state/PKCE flow acquired delegated
`Files.ReadWrite`, and the runner verified a OneDrive Personal drive before invoking exactly one
probe. The sanitized report was:

```json
{"cleanup":"DELETED_TO_RECYCLE_BIN","reason":"Fresh conditional final commit failed with HTTP 400.","status":"FAIL"}
```

This run progressed through exact-item upload-session creation, deferred staging and the
pre-commit identity/eTag/byte-preservation checks. Microsoft Graph then rejected the fresh
exact-item `sourceUrl` final PUT with HTTP `400`; the stale-final-commit branch was not reached.
The isolated probe item was moved to the OneDrive recycle bin in `finally`.

The public v1.0 completion example targets a path and supplies `name`, while the probe deliberately
targets the accepted exact item ID and supplies only `sourceUrl` plus explicit conflict behavior.
The general `driveItem` reference also says the conflict annotation belongs in the URL rather than
the body. Those documentation differences identify the final-commit request shape as the failure
boundary, but they do not establish which difference caused the provider's `400`: this probe did
not retain or emit the provider body or message. Changing to path binding, adding `name`, moving the
conflict annotation, or weakening the exact-item condition would change the accepted contract and
requires Product Owner review before any further live attempt.

Post-run cleanup was verified in Entra: the temporary PR-07 secret was deleted, configured delegated
`Files.ReadWrite` was removed, the pre-existing PR-05 secret remained, and delegated `Files.Read`
remained. The token-bearing runner exited, its temporary dependencies and helper were deleted, and
the clipboard was cleared. No token, client secret, provider body, item/drive ID, eTag, upload URL or
file content was written to the repository or this report. Removing the configured permission is
not evidence that previously granted user consent or the issued token was revoked.

Runtime, migration work and PR-08 remain paused. The bounded rerun condition has now been exercised
and failed at fresh final commit, so the next action is Product Owner review rather than another
provider attempt or an implementation change.

### Local C1 final-commit wire-shape candidate — 2026-09-15

Following the fresh final-commit HTTP `400`, the Product Owner authorized local-only C1
implementation, focused tests and independent review; no live or cloud action was authorized. C1
changes only the final exact-item PUT representation:
`@microsoft.graph.conflictBehavior=fail` moves from the JSON body to one query parameter, while the
body contains only `@microsoft.graph.sourceUrl`. The exact item-ID route, frozen `If-Match`, deferred
staging, pre-commit reread, mandatory stale `412`, one-attempt rule, sanitization and cleanup remain
unchanged.

The focused probe suite passed `8/8`, Ruff `0.6.0` passed, `git diff --check` passed, and independent
review found no blocking P0-P2 issue. This is local candidate evidence only, not provider
conformance. PR-07 runtime and migrations, and PR-08, remain blocked. Any live validation requires a
separate explicit action-time Product Owner decision. If a bounded C1 live attempt is later approved
and fresh commit returns `nameAlreadyExists`, fresh commit remains HTTP `400`, or stale commit does
not return HTTP `412`, stop without another attempt and reopen Product Owner decision D6/F. Do not
fall back to path binding, add `name`, use small-file upload, or select `replace`/`rename` behavior.

### Bounded C1 live attempt — 2026-09-15

The Product Owner separately approved one C1 live attempt at action time. Entra preflight showed the
exact registered callback `http://localhost:8000/api/v1/m365/onedrive/oauth/callback`, the original
PR-05 secret and delegated `Files.Read`, with no temporary PR-07 secret or configured
`Files.ReadWrite` left from an earlier attempt. The run temporarily added exactly delegated
`Files.ReadWrite` and created exactly one temporary client secret.

One OAuth state/PKCE flow completed through the exact localhost callback. State validation passed,
the authorization code and secret stayed in process memory, and the token response reported
delegated `Files.ReadWrite`. The memory-only launcher then exited with code `1`, emitted stderr and
produced no parseable sanitized probe JSON. The candidate was not retried. A post-closeout local
diagnosis reproduced the same immediate exit, stderr-only and empty-stdout signature in the exact
Node-sandbox-to-PowerShell launch surface: `Get-Command python -ErrorAction Stop` raised
`CommandNotFoundException` before the Python module invocation. The normal local shell could import
the probe and its dependencies, while the launcher's child environment could not resolve Python.
The raw live stderr had already been cleared, so this conclusion is based on deterministic
reproduction rather than retained provider evidence.

The C1 provider probe therefore did not run. This preparation establishes no provider response
status, no fresh final-commit result, no stale `412` result, no item-identity or concurrent-byte
result, and no probe item cleanup result. It is not provider PASS and is not a contract
provider-shape FAIL.

External cleanup was completed and verified immediately afterward: the exact temporary secret was
deleted, configured delegated `Files.ReadWrite` was removed, the original PR-05 secret and delegated
`Files.Read` remained, the callback listener and child process had exited, and the clipboard and
token-bearing runner memory were cleared. No temporary runner file was created. A closeout audit
later found the attempt's `valora-pr07-live-01a0a538-deps` dependency directory under Windows Temp.
After resolving the exact path beneath Temp and confirming that it was not a reparse point, the
directory was removed from Temp to the Windows Recycle Bin and its absence was verified. Removing
the configured permission is not evidence that the OAuth consent was revoked.

The conformance gate remains blocked. Do not run another candidate or begin PR-07
runtime/migrations or PR-08 work. D6 remains unchanged because the provider probe was not invoked.
Before any future live attempt, first review a local launcher hardening candidate that uses a normal
local process plus an exact-surface no-network self-test for the interpreter, dependencies, working
directory, environment injection, stdout JSON and exit-code capture; then obtain a fresh explicit
action-time Product Owner decision for F/live execution.

### Local normal-process launcher hardening candidate — 2026-09-16

The local-only candidate adds `--self-test` to the existing module command. It is fail-closed and
cannot be combined with either live-write acknowledgement. Before constructing
`OneDrivePersonalIfMatchProbe` or an `httpx` client, it requires a non-empty token-environment value,
confirms that the process is running from `backend`, and emits exactly one deterministic sanitized
JSON line. The report records successful interpreter, dependency import, package resolution,
working-directory and environment-injection checks plus `network: NOT_ATTEMPTED`; it never includes
the environment value. Existing live flags and C1 request construction are unchanged.

From `backend`, the normal local module surface was exercised with a non-secret dummy sentinel:

```powershell
python -m tools.pr07_onedrive_personal_if_match_probe --self-test
```

It exited `0`, wrote one parseable JSON line to stdout, wrote no stderr, excluded the sentinel, and
reported all local checks `PASS` with network not attempted. The exact-surface subprocess tests also
prove a sanitized exit `1` when the environment variable is absent and reject either live flag
before client construction. Focused tests pass `13/13`; Ruff `0.6.0` passes for the probe and focused
test, and `git diff --check` passes.

The earlier launcher diagnosis remains distinct: the failed live launcher could not resolve Python
and therefore never invoked the module. A separate no-network control selecting an interpreter
without `httpx` exited `1` with a missing-dependency message on stderr and empty stdout; that control
was not the live launcher path. No raw live stderr or sensitive log is retained.

This is local candidate evidence only. It is not an independent acceptance review, does not show
that the provider probe ran, does not change D6, and does not authorize a live attempt. Before any
future attempt, obtain independent review of this candidate and a separate fresh explicit
action-time Product Owner approval. PR-07 runtime/migrations and PR-08 remain blocked.

### Repository-owned Node launcher and cleanup hardening candidate — 2026-09-16

The failed live surface was Node-to-PowerShell-to-Python, while the first local self-test invoked
Python directly. The repository now contains a Node launcher for the actual parent-process boundary.
It requires an absolute Python executable file, sets the child working directory to `backend`, and
runs a bounded preflight for Python 3.12+, `httpx`, and the exact probe module before invoking the
probe. It never resolves the literal command `python` through the child `PATH`.

The launcher never places the token in command arguments or output, and it removes the token from
the dependency-preflight environment. Only the validated probe process receives it. Child stdout
must be exactly one allowlisted JSON object; unknown fields, inconsistent exit status, invalid field
types and any field containing the token are rejected. Raw child stderr is never forwarded; the
launcher records only `EMPTY` or `PRESENT_SANITIZED`, together with the child exit code and a bounded
stage name when bootstrap or capture fails. The launcher retains at most 1 MiB of stdout while still
draining overflow until the child exits, then rejects the oversized report without terminating the
live child. Dependency and self-test subprocesses have a 15-second timeout. The live probe has no
launcher timeout because terminating it mid-write could bypass its `finally` cleanup; individual
HTTP operations remain subject to the probe's 30-second client timeout.

For no-network validation from any working directory, use an explicit machine-local path:

```powershell
node backend/tools/pr07_onedrive_personal_if_match_launcher.mjs `
  --python-executable "C:\absolute\path\to\python.exe" `
  --self-test
```

The official Microsoft identity Python web-app sample was audited at commit `c56f3938`. Only its
boundary patterns were retained: OAuth configuration comes from environment, the identity library
owns the authorization-code callback/state flow, and the access token is handed to the downstream
operation in memory. Its Flask runtime and generic downstream API call were not copied because they
do not implement the PR-07 OneDrive Personal conditional-commit contract. Valora's existing MSAL
runtime adapter and its `Files.Read` scope remain unchanged; this operator launcher does not perform
OAuth or alter permissions.

Unexpected non-`ProbeFailure` exceptions inside the probe are now converted to one generic sanitized
failure before cleanup aggregation. Each session/item cleanup boundary also sanitizes unexpected
exceptions independently, so a cancel failure cannot prevent the exact-item delete attempt and no
internal detail is emitted. The expanded local suite also covers unsafe and excessive redirects,
oversized downloads, cancel failure, partial-create fallback cleanup, absolute-path enforcement, a
real isolated Python environment with missing dependencies, stdout schema/token rejection, bounded
capture without child termination, and sanitized child exit propagation. Focused tests pass `28/28`;
Node syntax, Ruff `0.6.0`, and `git diff --check` pass.

This remains local candidate evidence. No OAuth, Entra, OneDrive or Graph request was made while
building or validating it. D6 and the PR-07 contract are unchanged; PR-07 runtime/migrations and
PR-08 remain gated. Independent review passed with no P0-P3 finding after separately exercising the
focused tests, Node syntax, Ruff, diff-check and the exact no-network launcher surface. A fresh,
separate action-time Product Owner approval is still required before exactly one live attempt.

### Bounded C1 live attempt — 2026-09-16

The Product Owner separately approved exactly one action-time C1 live attempt. The Entra app was
temporarily given delegated Microsoft Graph `Files.ReadWrite`, and exactly one temporary client
secret was created. One OAuth authorization-code flow completed through the registered localhost
callback. The execution controller then invoked the repository-owned Node launcher once, without
retry. The launcher stopped before dependency preflight or probe execution and returned only the
sanitized failure `stage=LAUNCHER_VALIDATION` with reason `Python executable path is unavailable.`
After cleanup, a direct no-network `--self-test` using the same literal absolute Python path and a
non-secret sentinel passed interpreter, dependency, package-resolution, working-directory and
environment checks with `network=NOT_ATTEMPTED`. This narrows the failure to the live controller's
argument-transfer boundary; the exact transferred value was intentionally not retained, so its
specific escaping or serialization defect is not yet proven.

The C1 provider probe therefore did not run. This attempt establishes no provider response status,
no fresh final-commit result, no stale `412` result, no item-identity or concurrent-byte result, and
no probe-item cleanup result. It is neither provider PASS nor a C1 wire-shape FAIL. D6 remains
unchanged.

Closeout was verified immediately after the failure. Temporary secret ID
`bdb08139-6c88-4975-a16c-f5f076fb497b` was deleted, configured delegated `Files.ReadWrite` was
removed, the pre-existing PR-05 secret ID `0884fe2c-8ed2-40ee-864c-c41b4b5a97eb` and delegated
`Files.Read` remained, the clipboard was cleared, and no listener remained on port 8000. No retry
occurred. Before any future live attempt, diagnose and exercise the exact controller-to-launcher
absolute-Python argument boundary locally, obtain independent review, and obtain a new explicit
action-time Product Owner approval. PR-07 runtime/migrations and PR-08 remain gated.

### Repository-owned controller and durable diagnostic evidence — 2026-09-16

The transient memory-only live controller was replaced by
`backend/tools/pr07_onedrive_personal_live_controller.py`. It owns the exact OAuth callback and
launcher boundary, selects `sys.executable` inside the running Python process, and passes the
absolute interpreter path to Node as one argv element with `shell=False`. PowerShell no longer
discovers, quotes or transfers the Python path, so the boundary responsible for the preceding
`LAUNCHER_VALIDATION` failure is removed by construction. The live branch requires the exact app ID
and both write/cleanup acknowledgements before OAuth, uses OAuth `form_post` so the authorization
response is not placed in the callback URL/history, accepts only one bounded form-encoded POST on
the exact callback path, invokes the launcher once, and has no retry path. A query-string callback
is rejected. Direct live invocation of the probe is also rejected unless the controller supplied a
valid attempt ID and existing event journal.

Every successfully initialized invocation creates two Git-ignored local artifacts: an atomically
replaced JSON snapshot and an fsync-backed append-only JSONL stage journal. Both use allowlisted
schemas and retain only attempt ID, UTC timestamps, network state, Git/component hashes, bounded
dependency/runtime/argv fingerprints, sanitized stage codes, exit status and sanitized
launcher/probe reports. Token, temporary secret, authorization code/response, account identity,
raw stderr, provider identifiers, eTags, upload URLs and content are excluded. Tests inject
secret/token canaries, reject unknown result keys and reject any canary appearance in stdout,
snapshot or journal. Failures before OAuth, missing Node, unexpected controller exceptions and
simulated live probe failure all finalize durable sanitized evidence.

The probe writes a fail-closed progress marker before each provider mutation/commit boundary and
best-effort start/completion markers around cleanup. A journal write failure during cleanup cannot
prevent upload-session cancellation or exact-item/name deletion; it makes the outcome fail because
cleanup evidence is incomplete. The item name is deterministically derived from the attempt UUID
for bounded recovery. `ATTEMPT_FINISHED` alone does not resolve a prior live attempt. A valid,
allowlisted journal is resolved only when no provider mutation began, or when its ordered evidence
proves every possibly open upload session was cancelled, exact-item deletion completed (or bounded
delete-by-name completed before an item ID was established), and the terminal launcher/probe report
has the matching successful cleanup state. The scanner accepts and schema-validates the producer's
`PROBE_FINISHED` record against the probe producer's exact report schema, reconciles it with the
controller terminal report before both the mutation and no-mutation resolution paths, rejects
Boolean exit codes, rejects any later probe stage, and requires item deletion to follow the final
provider mutation. Every session-dependent stage requires the applicable allowlisted session to be
active at that journal position; fresh verification or completed cancellation closes that session,
so a later dependent stage requires a newly opened applicable session. Once cancellation starts,
its completion marker must be the next probe stage; intervening probe activity is contradictory.
Every cleanup marker pair that appears must be complete and ordered even when it is not the selected
cleanup path, and every mutation-bearing attempt requires a valid `PROBE_FINISHED`. The controller
terminal must match the exact `ATTEMPT_FINISHED` producer schema; missing or extra fields are
rejected even when no mutation
began. Empty journals and missing, malformed, contradictory, failed or unknown cleanup evidence
block the next live invocation as
`UNRESOLVED_PRIOR_ATTEMPT` before recorder creation, OAuth, launcher invocation or network access.
Treat that state as `UNKNOWN`; the controller performs no automatic recovery. Do not retry until
the process state, deterministic probe item and separate Entra baseline have been reconciled and
the recovery disposition has been independently recorded.

The exact controller-to-Node-to-Python no-network path passed from a working directory containing
spaces, with `network=NOT_ATTEMPTED`, `shell=false`, one Python-path argv element and launcher exit
`0`. The combined probe/controller focused suite passes `68/68`; Ruff, Python compilation, Node
syntax and `git diff --check` pass. The retained local self-test snapshot/journal contain the
allowlisted `PROBE_SELF_TEST_STARTED` and `PROBE_FINISHED` events and no injected canary. Independent
review passed on 2026-09-18 with no P0-P3 finding after exercising the focused suite, static checks,
adversarial journal paths and canonical artifact
`370861c7-2d86-42d7-a2e8-13b161377c05`. This is local candidate evidence only. D6 and the PR-07
contract remain unchanged. Obtain fresh explicit action-time Product Owner approval before any new
live attempt. PR-07 runtime/migrations and PR-08 remain gated.

### Repository-controller C1 live attempt — 2026-09-18

The Product Owner separately approved exactly one action-time live attempt. The controller was
invoked once with both write/cleanup acknowledgements and no retry. Attempt
`fe63fa6a-c477-4566-a720-f56c74be2ea0` received the bounded OAuth `form_post` callback; the Product
Owner supplied a screenshot of the local `Authorization received` page. The subsequent token step
failed closed as `OAUTH_TOKEN_REJECTED`. The finalized sanitized snapshot records
`network=OAUTH_ATTEMPTED`, no launcher report and no probe stage. The launcher, provider probe and
Microsoft Graph/OneDrive mutation path did not run, so no probe item existed and no provider cleanup
was required. This is neither C1 provider PASS nor a C1 wire-shape FAIL. D6 remains unchanged.

The snapshot and append-only journal finalized with terminal `ATTEMPT_FINISHED/FAIL`. Local closeout
confirmed the canonical prior-attempt ledger is clean, port `8000` has no listener, clipboard is
empty, and the client-ID, client-secret and Graph-token environment values are absent. The Product
Owner separately confirmed that the temporary Entra secret was deleted and configured delegated
`Files.ReadWrite` was removed while the PR-05 secret and delegated `Files.Read` were preserved; this
Entra lifecycle confirmation is external to the controller artifact. Do not retry. Diagnose the
token rejection without claiming provider evidence, and require a new explicit action-time Product
Owner approval before any later live attempt. PR-07 runtime/migrations and PR-08 remain gated.

### Local OAuth diagnostics and C2 automatic-completion candidate — 2026-09-18

The Product Owner approved G1/WP0–WP7 only. The repository now binds the explicit candidate
`C2_AUTO_V1` through controller, Node launcher and probe; current evidence uses schema version `2`
and rejects C1-shaped or candidate-mismatched output. Historical schema-less C1 journals remain
read-only compatible, while mixed or unresolved evidence continues to block before OAuth.

OAuth failures are separated into authorization-response, state/flow-validation and token-redemption
phases. Persisted diagnostics have one bounded allowlisted object containing only phase, OAuth error
enum, at most eight integer AADSTS codes and a canonical correlation UUID. Raw callback values,
descriptions, claims, codes, PKCE material and provider messages remain excluded. The callback page
now confirms only that an authorization response was received; it does not imply token success.

The C2 probe creates an isolated `655360`-byte fixture and sends two `327680`-byte fragments for
both fresh and stale branches. Session creation uses the exact item ID, frozen `If-Match` and body
`{}`. The final fragment is the only completion operation: there is no `deferCommit`, `sourceUrl`,
final-fragment `If-Match`, retry, polling or fallback. Every dispatched partial/final outcome is
followed by a bounded metadata-content-metadata coherent read. Classification depends on observed
destination bytes and eTag, so a stale overwrite is `UNSAFE_STALE_OVERWRITE` even when the response
is `412` or lost; alternate rejection, third-state data and incomplete reads remain inconclusive.

Session-role journal events distinguish fresh and stale lifecycle state. Durable mutation markers
precede requests; session completion must be proven or cancellation must complete before exact-item
deletion can resolve a v2 ledger. Cancellation/evidence failure does not suppress best-effort item
deletion and cannot convert an observed unsafe result into inconclusive or PASS.

Local verification on 2026-09-18 passed `45/45` focused tests, Ruff, Python compilation, Node syntax
and `git diff --check`. The real controller → Node → Python self-test passed from the repository with
`network=NOT_ATTEMPTED`, candidate `C2_AUTO_V1`, schema `2`, `shell=false` and no provider/OAuth/Entra
access. Component SHA-256 values at that checkpoint were controller
`b64840590069be8b8167275457b90c0ccf0f1cd7867b5768d55c0a105200ae2a`, launcher
`e0ce3685e4cc2734349e91a4f3a30a5a3e097b23a9212e0af4f3765d5b857d3f`, and probe
`ff4b2980f4d94b8d615e093c5aab9bb2d4a4c3dbffca49d8175ec94c83f46d5b`.

This is local harness evidence only. It is not a Microsoft Graph observation, does not amend ADR
0042/D6, does not open PR-07 runtime or PR-08, and does not authorize G2. The independent-review
result belongs to the implementation-task closeout against the exact final diff/hashes; this
runbook does not self-certify that review.

### C2 local correction checkpoint — 2026-09-18

The first independent implementation review found six P2 issues and no P0/P1/P3 issue. The
Product Owner approved one local correction plus a new independent review for exactly those six
findings. The corrected probe no longer treats observed stale bytes as proof that an upload session
closed: only a validated `200/201` completion response for the same item can close it; `412`, lost
response or invalid completion identity leaves the session eligible for cancellation. Journal
marker failure after a dispatched fragment is recorded as `EVIDENCE_INCOMPLETE` but cannot suppress
the mandatory coherent post-state read or erase an observed unsafe overwrite.

The corrected v2 resolver requires item creation to precede the session lifecycle, forbids any
interleaved probe stage while cancellation is pending, and accepts bounded delete-by-name cleanup
only when no session or item-identity evidence exists. Controller, probe and Node validators now
share the same safe-observation/PASS predicate. OAuth tests use a state-aware MSAL double with a
separate redemption-transport counter: wrong or missing state and a valid authorization-error
callback all prove zero token-redemption transport calls.

The focused probe/controller suites pass `52/52`; Ruff, Python compilation, Node syntax and
`git diff --check` pass. The wider backend gate reached `870 passed, 50 skipped` and then stopped at
the pre-existing local-infrastructure boundary because MinIO was unavailable at `localhost:9000`;
no PR-07 test failed before that point. Corrected component SHA-256 values are controller
`bb3ff05235e9af4bbdae0976e5b02e9103259da4b3f06a14a6e2cc094296ba5a`, launcher
`e0ce3685e4cc2734349e91a4f3a30a5a3e097b23a9212e0af4f3765d5b857d3f`, and probe
`c6f3f22807c509417bd0b07ae070366f474bddb5a77aba5ae7b28e39170aa850`. A new independent review of
the exact corrected snapshot remains the final G1 gate. No OAuth, Entra or Microsoft Graph action
occurred in this correction; G2–G4 remain closed.

### C2 `checked_at` validator parity correction — 2026-09-18

The subsequent independent review verified all nine supplied source hashes and found one additional
P2: controller and probe validators required an ISO timestamp with timezone, while the Node
launcher accepted date-only and timezone-naive timestamps through `Date.parse()`. The Product Owner
approved one correction and a new independent review for exactly this finding.

The correction adds shared regression vectors for `2026-09-18` and
`2026-09-18T00:00:00`. Both Python validators already reject those values. The Node boundary now
also requires an explicit `Z` or `±HH:MM` timezone suffix before applying `Date.parse()`. The Python
validators were not relaxed and no adjacent validation or provider behavior was refactored.

Focused tests pass `54/54`; Ruff, Python compilation, Node syntax and `git diff --check` pass. The
real controller → Node → Python self-test passes with `network=NOT_ATTEMPTED`, candidate
`C2_AUTO_V1` and schema `2`. Component SHA-256 values are controller
`bb3ff05235e9af4bbdae0976e5b02e9103259da4b3f06a14a6e2cc094296ba5a`, launcher
`3be52c56e60fb407c4a18081db3c5bdcd8a3473cea5bf228ad19c04667656602`, and probe
`c6f3f22807c509417bd0b07ae070366f474bddb5a77aba5ae7b28e39170aa850`. The wider backend gate was
not rerun for this Node/test-only correction; its prior `870 passed, 50 skipped` result remains the
earlier checkpoint and still stopped at unavailable local MinIO.

DeepSeek V4.1 Flash independently verified branch/HEAD and all `9/9` supplied SHA-256 values, read
the three validators, adversarial timestamp vectors, tests and doc claims, and returned `READY`
with no P0–P3 finding. The reviewer changed no file and ran no OAuth, Entra, Microsoft Graph,
provider, live or repository-network action. At that checkpoint this closed G1 local review only;
the later G2 observation is recorded below.

### Bounded C2 live attempt and closeout — 2026-09-18

The Product Owner approved the C2 research exception and exactly one action-time invocation of
`C2_AUTO_V1` on the reviewed snapshot. Temporary delegated Microsoft Graph `Files.ReadWrite` and
exactly one temporary client secret named `PR07 C2_AUTO_V1 2026-09-18` were added without changing
the PR-05 baseline. The controller was invoked once with both live-write and cleanup acknowledgements;
there was no retry.

Attempt `af114cc0-4a10-46eb-ba60-108facc7daa0` ran at HEAD
`46e0792b3ae697158f0fe38db8100fbd4afdc6fc`. Its controller, launcher and probe hashes matched the
reviewed values `bb3ff05235e9af4bbdae0976e5b02e9103259da4b3f06a14a6e2cc094296ba5a`,
`3be52c56e60fb407c4a18081db3c5bdcd8a3473cea5bf228ad19c04667656602` and
`c6f3f22807c509417bd0b07ae070366f474bddb5a77aba5ae7b28e39170aa850`. OAuth passed, the Personal
drive was verified, an isolated fixture was created and a fresh exact-item upload session became
available.

The first `327680`-byte fragment was dispatched. Its response did not satisfy the exact accepted
partial predicate: HTTP `202` with `nextExpectedRanges` equal to `["327680-"]`. The required coherent
post-read completed and proved that the destination item bytes and eTag were unchanged, so
`fresh_partial_preserved=true`. The probe therefore failed closed before dispatching the fresh final
fragment; no concurrent write or stale branch ran. The sanitized terminal report records
`checked_at=2026-09-18T15:32:18.893562+00:00`, `outcome=INCONCLUSIVE`,
`reason_code=FINAL_NOT_COMPLETED`, `fresh_final_http_status=null`, `runtime_gate=BLOCKED` and
controller `failure_code=PROBE_REPORTED_FAILURE`.

Cleanup completed without retry: the open fresh session was cancelled and the fixture was deleted
to the OneDrive recycle bin (`cleanup=DELETED_TO_RECYCLE_BIN`, `cleanup_issue=NONE`). The controller
cleared sensitive environment state and the clipboard; no callback listener remained on port 8000.
The Product Owner then removed the temporary secret and delegated `Files.ReadWrite`. Supplied images
and a read-only Entra verification confirmed the restored baseline of exactly one PR-05 secret and
delegated `Files.Read` only.

This observation does not prove or disprove stale-write protection because the final-fragment and
stale branches were never reached. It does not amend ADR 0042/D6 or open PR-07 runtime, migrations,
G3, G4 or PR-08. Any next step is separate provider research/architecture authority, not a retry of
this live attempt.

### C2_AUTO_V2 partial-response local correction — 2026-09-19

Provider research found that the `C2_AUTO_V1` exact equality predicate for
`nextExpectedRanges=["327680-"]` was stricter than the published response contract. Under separate
local authority, the probe, launcher and controller now use `C2_AUTO_V2` with schema version `3`.
The bounded parser accepts documented open or finite range forms only when the remaining tail begins
at byte `327680` and is fully covered by the existing final fragment. Evidence retains only HTTP
status and a bounded range class; it never persists raw response bodies or raw range strings.

The controller keeps explicit read-only readers for legacy C1 and finalized
`C2_AUTO_V1`/schema-v2 evidence. Current v3 report and journal validation is exact-key and
fail-closed. Every dispatched fragment requires its own coherent post-read; the final post-read
cannot be substituted before final dispatch. Session completion requires an observed, role-matched
final HTTP `200/201`; transport-unknown and stale `412` paths require successful cancellation.
Non-`202` partial responses are classified without parsing their body, and no polling, session
status GET, retry, resend, fallback or replacement session was added.

Focused tests passed `89/89`, with 13 existing Pydantic deprecation warnings outside this scope.
Ruff, Python compilation, Node syntax and `git diff --check` passed. The real controller → Node →
probe self-test returned `PASS` with `network=NOT_ATTEMPTED`; the canonical ledger check returned
`CANONICAL_LEDGER_UNRESOLVED=False`.

Final SHA-256 values are controller
`64af797e46d4f1a548ed6fc9268f1880ad8387a8c6e2e0b9f0a04a3fa5b9ff8d`, launcher
`50940a6146f1209299deb28216dd24ca31afcd4ca57818c7d7a50689c304e0c0`, probe
`9840ed3014c1434f99a5ac9d933b14d486b4493dfff8e049b89d9b750e6fba0f`, controller tests
`7bcdb25f6bd6c6407fb3cc904d6af8695e5824e06b312827f6211a3ad2ce6cd5` and probe tests
`be9026485bd14a0ec746e41a9ad400f28e06c56bea5ffbd0f99012801ddc1dc9`.
Independent review matched all five and returned `READY` with no unresolved P0–P3 finding and zero
reviewer file changes.

This closes the local correction/review gate only. No OAuth, Entra, Microsoft Graph, OneDrive or
other network action occurred; no second live attempt was made. The historical
`C2_AUTO_V1` attempt remains `INCONCLUSIVE`, ADR 0042/D6 is unchanged, and `runtime_gate=BLOCKED`,
G3–G4, PR-07 runtime/migrations and PR-08 remain closed.

### Bounded C2_AUTO_V2 live attempt and closeout — 2026-09-19

The Product Owner separately approved the research exception and exactly one live invocation of
`C2_AUTO_V2` on the independently reviewed five-file snapshot. Temporary delegated Microsoft Graph
`Files.ReadWrite` and exactly one temporary client secret named `PR07 C2_AUTO_V2 2026-09-19` were
added for that attempt. The controller was invoked once with the live-write and recycle-cleanup
acknowledgements; there was no retry.

Attempt `2a06438c-5ad2-46f1-8da2-b60776647f86` ran at HEAD
`46e0792b3ae697158f0fe38db8100fbd4afdc6fc`. The controller, launcher, probe and both focused test
file hashes matched the reviewed snapshot recorded above. OAuth passed. The fresh first fragment
returned HTTP `202` with range class `EXPECTED_START`; its coherent post-read proved the partial
write preserved the destination. The fresh final fragment completed with HTTP `200`, and the next
coherent post-read proved the fresh commit, item identity and final bytes.

The stale session then accepted its first fragment with HTTP `202` and range class
`EXPECTED_START`. After the concurrent write, the stale final fragment returned HTTP `404` with
provider code `itemNotFound`, rather than the candidate HTTP `412`. Coherent post-read proved the
concurrent bytes and eTag were preserved, and the stale partial-write preservation check also
passed. Because the expected stale candidate was not observed, the sanitized terminal report records
`checked_at=2026-09-19T10:43:18.932461+07:00`, `outcome=INCONCLUSIVE`,
`reason_code=ALTERNATE_REJECTION`, `stale_candidate_observed=false`, `runtime_gate=BLOCKED` and
controller `failure_code=PROBE_REPORTED_FAILURE`.

Cleanup completed without retry: the stale session cancellation completed and the fixture was
deleted to the OneDrive recycle bin (`cleanup=DELETED_TO_RECYCLE_BIN`, `cleanup_issue=NONE`). The
canonical ledger is resolved; port `8000`, the clipboard and both credential environment variables
are clean. The Product Owner removed the temporary secret and delegated `Files.ReadWrite`.
Read-only Entra verification then confirmed the restored baseline: exactly one existing PR-05
client secret and exactly one delegated Microsoft Graph permission, `Files.Read`.

This observation proves fresh completion and preservation of the concurrent destination state under
the provider's alternate stale-session rejection. It does not establish the D6-required HTTP `412`
classification, amend ADR 0042/D6 or open PR-07 runtime, migrations, G3, G4 or PR-08. The single
`C2_AUTO_V2` live authority is consumed; any further provider experiment requires a new bounded
research decision and new action-time authority.

### G3 Option A architecture closeout — 2026-09-19

The Product Owner approved Option A: retain ADR 0042/D6, close `C2_AUTO_V2` as research and reject it
as a production adapter mechanism. The safe `404 itemNotFound` observation does not become an
accepted stale-plan status because Microsoft documentation does not bind that ambiguous response to
the frozen eTag through final commit. `runtime_gate=BLOCKED`; PR-07 provider-write runtime,
migrations, G4 and PR-08 remain closed.

The only authorized continuation is read-only provider clarification against official Microsoft
documentation or support material. It does not authorize an external message, another Graph/Entra
mutation, another live attempt or implementation. The architecture decision may reopen only on a
documented provider guarantee or a separately reviewed supported exact-item conditional-commit
mechanism.

### Read-only public-source clarification closeout — 2026-09-19

The approved public-source pass checked current Microsoft Learn documentation, its Microsoft-owned
source, the upload-session resource, the OneDrive error catalogue and relevant public issue history.
Creation-time `If-Match` is documented, but eTag binding through final session commit, concurrent-
write invalidation and `404 itemNotFound` stale causality remain undocumented. The documented
`sourceUrl` recovery example uses parent/path metadata and does not establish D6's exact-item-ID
boundary.

The reopen trigger is not met. Public research stops at `UNDOCUMENTED`; a sanitized question packet
exists locally but has not been sent. Sending it to Microsoft requires separate authority at send
time. D6, `runtime_gate=BLOCKED` and all G4/runtime/migration/PR-08 closures remain unchanged.

## Research handoff

The standalone [PR-07 OneDrive Personal provider-conformance research handoff](../research/pr07-onedrive-conformance-handoff.md) consolidates the recent trial chronology, current wire shape, OAuth diagnostic boundary and the specific questions that require external provider research. It authorizes neither a contract change nor another live attempt.

## Provider references

- [Microsoft Graph v1.0: create an upload session](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0)
- [Microsoft Graph v1.0: driveItem instance attributes](https://learn.microsoft.com/en-us/graph/api/resources/driveitem?view=graph-rest-1.0#instance-attributes)
- [Microsoft Graph v1.0: driveItemUploadableProperties](https://learn.microsoft.com/en-us/graph/api/resources/driveitemuploadableproperties?view=graph-rest-1.0)
- [OneDrive API: error response semantics](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/errors?view=odsp-graph-online)
- [Official OneDrive documentation issue: analogous optional-property HTTP 400 report](https://github.com/OneDrive/onedrive-api-docs/issues/1319)
- [Microsoft identity Python web-app sample](https://github.com/Azure-Samples/ms-identity-python-webapp)
