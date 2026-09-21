> **HISTORICAL DIRECT-WRITE RESEARCH — 2026-09-21**
> Retained as evidence only. Do not execute/reopen this plan from current roadmap. Direct replacement of an existing OneDrive item is historical/blocked. Current document direction is ADR 0043–0045 + `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`.

# PR-07 OneDrive Personal provider-conformance research handoff

Status: amended 2026-09-19

## Start time

2026-09-18, Asia/Saigon.

## Initial purpose

Provide an external research team with a self-contained account of the recent PR-07 C1 trials and ask for a provider-supported way to validate optimistic concurrency on an existing OneDrive Personal item.

The accepted Valora contract requires all of the following:

- target the existing item by immutable drive/item ID, never by path;
- freeze one destination eTag in `If-Match` for each upload session and its final commit;
- stage bytes with `deferCommit: true` without changing the destination item;
- commit the fresh candidate to the same item while preserving item identity;
- reject a stale final commit with HTTP `412` after a concurrent write;
- preserve the concurrent writer's bytes after the stale rejection;
- use conflict behavior `fail`, never `replace` or `rename`;
- do not add `name`, fall back to small-file upload, or manufacture provider evidence.

Runtime implementation and migrations remain blocked until the provider behavior is proven. This document requests research and recommendations only; it does not authorize another live attempt or a change to the accepted contract.

## Strategy

The trials progressively isolated the provider wire shape, then hardened the local execution path:

1. Exercise one bounded provider attempt at a time with a temporary delegated `Files.ReadWrite` permission and temporary client secret.
2. Preserve only sanitized status, bounded provider error codes and cleanup results.
3. Remove optional or creation-oriented properties without weakening exact-item or stale-write requirements.
4. Reproduce launcher failures locally before changing the execution boundary.
5. Replace the transient runner with a repository-owned controller, launcher, durable local journal and no-network self-test.
6. Require independent review after each authorized correction round and never retry a live failure automatically.

## Checklist

- [x] Exact item-ID upload-session route exercised against OneDrive Personal.
- [x] Deferred staging exercised without changing destination identity, eTag or bytes.
- [x] Fresh exact-item final commit reached once with the earlier JSON representation.
- [x] Every provider mutation attempt used isolated content and cleanup.
- [x] Temporary Entra secret and configured `Files.ReadWrite` were removed after each recent run.
- [x] Current controller-to-Node-to-Python path passed no-network self-test and independent review.
- [x] Current source has local unit/static verification.
- [ ] Current query-parameter final-commit representation reached Microsoft Graph.
- [ ] Fresh final commit succeeded while preserving exact item identity.
- [ ] Stale final commit returned HTTP `412`.
- [ ] Concurrent bytes survived the stale rejection.
- [ ] Root OAuth error for the 2026-09-18 attempt was classified beyond the local aggregate code.

## Result

### Executive finding

Provider conformance is still unproven. The only trial that reached a fresh final commit used the earlier representation with conflict behavior in the JSON body and received HTTP `400`. The current candidate moves `@microsoft.graph.conflictBehavior=fail` to exactly one query parameter and leaves only `@microsoft.graph.sourceUrl` in the body, but every later live attempt stopped before the probe reached Microsoft Graph.

The most recent failure, `OAUTH_TOKEN_REJECTED`, is not sufficient to prove that the token endpoint was reached. The local callback page is unconditional for any structurally valid form POST, including an OAuth error response. The controller then maps every MSAL error dictionary, whether originating at the authorization response or token redemption, to the same sanitized code.

### Current candidate wire shape

Upload-session creation:

```http
POST /v1.0/drives/{driveId}/items/{itemId}/createUploadSession
If-Match: {frozenETag}
Content-Type: application/json

{"deferCommit":true}
```

Final commit, for both fresh and stale branches:

```http
PUT /v1.0/drives/{driveId}/items/{itemId}?@microsoft.graph.conflictBehavior=fail
If-Match: {sameFrozenETag}
Content-Type: application/json

{"@microsoft.graph.sourceUrl":"{uploadUrl}"}
```

The stale branch creates a second deferred session, stages a candidate, performs a separate conditional content overwrite that advances the item eTag, then sends the final commit with the now-stale frozen eTag. Acceptance requires HTTP `412`, unchanged item ID and preservation of the concurrent content.

### Trial chronology

| Date | Boundary reached | Sanitized result | What it proves | What it does not prove |
| --- | --- | --- | --- | --- |
| 2026-09-13 | First exact-item upload-session request | HTTP `400` | OAuth and Personal-drive access reached the provider | No staging, final commit or stale behavior |
| 2026-09-13 | Minimized exact-item upload-session request without optional `fileSize` | HTTP `409`, `nameAlreadyExists`; item recycled | Optional `fileSize` was not the blocker; cleanup completed | Whether the creation-oriented `item` annotation caused the conflict |
| 2026-09-15 | Session creation, deferred staging and pre-commit preservation; earlier final-commit representation | Fresh exact-item final PUT returned HTTP `400`; item recycled | Existing-item session creation and staging can succeed; failure boundary was final commit | Which request element caused `400`; stale branch was not reached |
| 2026-09-15 | OAuth completed; transient launcher boundary | Launcher exit `1`, stderr only, no probe report | Token reported delegated `Files.ReadWrite` | No provider call under the adjusted C1 representation |
| 2026-09-16 | OAuth completed; repository-owned Node launcher invoked | `LAUNCHER_VALIDATION`: Python executable path unavailable | Failure was before dependency preflight and probe | No provider call or cleanup claim from the probe |
| 2026-09-18 | Repository-owned controller-to-Node-to-Python self-test | PASS, `network=NOT_ATTEMPTED`; attempt `370861c7-2d86-42d7-a2e8-13b161377c05` | Exact local execution path, journaling and sanitization work without network | Provider or OAuth conformance |
| 2026-09-18 | Bounded OAuth `form_post` callback | `OAUTH_TOKEN_REJECTED`; attempt `fe63fa6a-c477-4566-a720-f56c74be2ea0` | Callback state matched; controller failed closed before launcher/probe | Whether callback contained `code` or `error`; whether token endpoint was called; any provider behavior |

No live attempt was retried. The last attempt produced no launcher report, no probe stage and no provider mutation. Its local artifact ledger finalized cleanly. The Product Owner separately confirmed removal of the temporary secret and configured delegated `Files.ReadWrite`, while the pre-existing PR-05 secret and `Files.Read` remained.

### Local candidate verification

- Focused controller/probe suite: `68/68` passing at the reviewed candidate.
- Ruff: pass for the four related Python files.
- Python compilation: pass for controller and probe.
- Node syntax check: pass for the launcher.
- `git diff --check`: pass.
- Independent review on 2026-09-18: pass with no P0-P3 finding.
- Current component hashes recorded by the no-network/live evidence:
  - controller: `ad96e05d41ef4e644ba421fc850f283bcfeea2e0530b24eff8443b1e1b37ec30`;
  - probe: `5c895bfa129c7d0ae3a569c2345cea247004371b1db420fbbff669a7c09a92c3`;
  - launcher: `8fcc9a86803e8759ca6387c2c78cdfd083631f6459e6af6911f2ec51cbccb3a2`.

Local artifacts are intentionally Git-ignored. They contain sanitized state only and are not part of this handoff repository commit.

### `OAUTH_TOKEN_REJECTED` diagnostic boundary

The installed MSAL flow has two relevant outcomes after state validation:

1. A callback containing `error` returns an error dictionary without redeeming an authorization code.
2. A callback containing `code` performs token redemption and can return an error dictionary such as `invalid_client`, `invalid_grant` or `invalid_scope`.

The controller clears callback material after MSAL returns and records neither the safe OAuth `error` class nor whether the error came from the authorization response or token endpoint. The final artifact therefore cannot distinguish:

- authorization/consent rejection, account selection or provider policy;
- an invalid temporary client credential, including copying Secret ID instead of Secret Value, truncated clipboard data, wrong-app secret or whitespace;
- authorization-code, PKCE or redirect redemption failure;
- invalid or unavailable requested scope.

Static configuration is a weaker suspect because earlier runs with the same consumer authority, client ID and localhost callback acquired delegated `Files.ReadWrite`. If the callback contained an authorization code, temporary client-secret handling is the leading operational hypothesis. This is not verified because the exact MSAL error was intentionally discarded.

### Questions for the research team

1. Does Microsoft Graph v1.0 officially support committing a deferred upload session to an existing OneDrive Personal item through `PUT /drives/{driveId}/items/{itemId}` with only `@microsoft.graph.sourceUrl`?
2. If supported, where must `@microsoft.graph.conflictBehavior=fail` be placed for this exact-item final commit: query parameter, JSON body, upload-session creation, or nowhere because `fail` is already the provider default?
3. Is `If-Match` documented and enforced at both exact-item `createUploadSession` and exact-item `sourceUrl` final commit for consumer OneDrive? Which endpoint is expected to return HTTP `412` after the destination eTag changes?
4. Is the public path-based completion example merely illustrative, or is path plus `name` the only supported completion shape? If so, is there another supported API that preserves the immutable item ID and stale-write rejection without `replace`, `rename` or small-file upload?
5. Are `409 nameAlreadyExists` during existing-item session creation and HTTP `400` during exact-item final commit known OneDrive Personal behaviors, documentation gaps or service bugs?
6. For MSAL Python confidential authorization-code flow against the `consumers` authority with `response_mode=form_post`, what minimal non-secret fields should be retained to distinguish an authorization response error from token-redemption `invalid_client`/`invalid_grant`?
7. Can a safe diagnostic record retain the normalized OAuth `error`, numeric AADSTS code and correlation ID while excluding `error_description`, authorization code, state, account claims, client secret and tokens?

### Constraints on recommendations

Recommendations must preserve the accepted contract unless explicitly presented as a decision for the Product Owner. In particular, do not silently recommend:

- path-based binding;
- a `name` property in the final-commit body;
- conflict behavior `replace` or `rename`;
- small-file `/content` upload as the sync mechanism;
- removing the stale HTTP `412` requirement;
- accepting a new item ID after commit;
- retrying provider writes automatically;
- retaining raw OAuth/provider bodies or credentials.

If the accepted contract is impossible on OneDrive Personal, the desired research outcome is a clear impossibility argument tied to primary Microsoft documentation or a minimal reproducible provider result, plus the smallest explicit contract decision the Product Owner would need to make.

### Verification

The chronology was cross-checked against the provider conformance runbook, the PR-00 to PR-13 acceptance matrix, the current probe/controller/launcher source, the finalized sanitized 2026-09-18 artifact and its append-only journal. The current OAuth diagnosis was also checked against the installed MSAL 1.38.0 source. No new OAuth, Entra, Graph or OneDrive action was performed while preparing this report.

Claims about the provider's undocumented exact-item completion behavior remain unverified. That is the research question, not an inferred conclusion.

### Corroborating links

- [Provider conformance runbook](../implementation/VALORA_UIUX_V2_3_PR07_PROVIDER_CONFORMANCE_RUNBOOK.md)
- [PR-00 to PR-13 acceptance matrix](../implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md)
- [Current provider probe](../../backend/tools/pr07_onedrive_personal_if_match_probe.py)
- [Current live controller](../../backend/tools/pr07_onedrive_personal_live_controller.py)
- [Current Node launcher](../../backend/tools/pr07_onedrive_personal_if_match_launcher.mjs)
- [Microsoft Graph: create upload session](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0)
- [Microsoft Graph: driveItem instance attributes](https://learn.microsoft.com/en-us/graph/api/resources/driveitem?view=graph-rest-1.0#instance-attributes)
- [Microsoft identity platform authorization-code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
- [MSAL Python token acquisition](https://learn.microsoft.com/en-us/entra/msal/python/getting-started/acquiring-tokens)

## Decision

**Follow-up research:** request provider and OAuth recommendations against the seven questions above. Do not run another live attempt from this report. Any code correction requires its own local verification and independent review; any later live attempt requires fresh, explicit action-time Product Owner approval.

## Amendments

- 2026-09-18 · §§ Checklist, Result, Trial chronology, Local candidate verification and Decision:
  a separately approved single `C2_AUTO_V1` live attempt
  (`af114cc0-4a10-46eb-ba60-108facc7daa0`) passed OAuth, created the isolated fixture and fresh
  exact-item session, and dispatched the first fragment. Its response did not satisfy the exact
  accepted partial predicate (`202` plus `nextExpectedRanges=["327680-"]`), while coherent post-read
  proved destination bytes/eTag unchanged. The probe stopped before final fragment, concurrent
  write or stale branch and reported `INCONCLUSIVE` / `FINAL_NOT_COMPLETED`; no retry occurred.
  Session cancellation, recycle-bin fixture cleanup and local secret/listener/clipboard cleanup
  succeeded. The Product Owner removed the temporary secret and delegated `Files.ReadWrite`; images
  plus read-only Entra verification confirmed only the PR-05 secret and delegated `Files.Read`
  remain. Current reviewed hashes are controller
  `bb3ff05235e9af4bbdae0976e5b02e9103259da4b3f06a14a6e2cc094296ba5a`, launcher
  `3be52c56e60fb407c4a18081db3c5bdcd8a3473cea5bf228ad19c04667656602` and probe
  `c6f3f22807c509417bd0b07ae070366f474bddb5a77aba5ae7b28e39170aa850`. The Decision remains
  follow-up provider research; this amendment authorizes neither a retry nor an ADR/runtime change.
- 2026-09-19 · § Decision: after the separately recorded `C2_AUTO_V2` live observation returned
  safe but undocumented `404 itemNotFound`, the Product Owner approved G3 Option A. ADR 0042/D6
  remains unchanged; C2 research is closed and neither candidate is accepted for production.
  `runtime_gate=BLOCKED`; PR-07 runtime/migrations, G4 and PR-08 remain closed. Only read-only
  provider clarification may continue, and this amendment authorizes no external message, Graph or
  Entra mutation, or new live invocation.
- 2026-09-19 · §§ Result, Verification and Decision: the approved read-only public-source pass
  found no normative Microsoft guarantee that creation-time `If-Match` remains bound through exact-
  item session commit or that `404 itemNotFound` is a stable stale-write rejection. The reopen
  trigger remains unmet. Public research stops at `UNDOCUMENTED`; the sanitized question packet was
  prepared locally but not sent, and any external message requires new send-time authority.
