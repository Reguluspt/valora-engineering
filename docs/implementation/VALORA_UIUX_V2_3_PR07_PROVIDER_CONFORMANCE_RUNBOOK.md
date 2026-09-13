# PR-07 OneDrive Personal conditional-commit conformance runbook

**Task:** `VALORA-PR07-CONFORMANCE-001` **Status:** BLOCKED — MANUAL CALLBACK HANDOFF REQUIRED
**Date:** 2026-09-13 **Authority:** accepted ADR 0042 and PR-07 implementation contract

## Purpose

Close PR-07 stop condition 332 before any schema or runtime implementation begins. The probe must
show that Microsoft Graph v1.0 on OneDrive Personal accepts a fresh exact-item final commit carrying
`If-Match`, rejects the equivalent stale final commit with HTTP `412`, and leaves a concurrent write
unchanged.

Microsoft documents `If-Match` on upload-session creation and on the explicit `sourceUrl` commit,
but the accepted boundary requires observed provider behavior rather than documentation alone.

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

## Command

From `backend`, after placing a short-lived delegated token in the process environment:

```powershell
python -m tools.pr07_onedrive_personal_if_match_probe `
  --allow-live-write `
  --cleanup-test-item
```

The only acceptable result has `status: PASS`, `fresh_conditional_commit: PASS`,
`stale_conditional_commit: HTTP_412_PASS`, both preservation booleans `true`, and cleanup
`DELETED_TO_RECYCLE_BIN`.

## Required evidence

Record only the sanitized JSON output, UTC execution time, probe commit, OneDrive Personal drive
type, delegated scope name, and confirmation that the recycle-bin item is the probe-created item.
Do not record account identity, item/drive IDs, eTags, bytes, token claims, upload URLs or secrets.

If any assertion fails, PR-07 remains blocked. Do not weaken the expected status, switch to a small
file upload, accept a create-session-only `412`, or begin runtime work on fake-provider evidence.

## Current disposition

On 2026-09-13, a bounded live attempt temporarily added delegated `Files.ReadWrite`, created a
short-lived client secret and reached the Microsoft Personal consent screen. The consent screen
showed OneDrive file access plus the normal profile/offline-access grants; no
`Files.ReadWrite.All` or application permission was requested. After consent, the controlled
browser blocked the registered `localhost` callback before the authorization code could be
captured. The probe command did not run, no probe item was created and no OneDrive content was
written.

Cleanup was verified in Entra immediately afterward: the temporary PR-07 secret and delegated
`Files.ReadWrite` grant were removed, delegated `Files.Read` remained, and the pre-existing PR-05
secret was preserved. No secret, authorization code or token was retained.

A live run now requires a user-controlled browser handoff to the registered local callback while
the probe session is listening, followed by a new short-lived `Files.ReadWrite` consent/token.
This attempt is neither provider PASS nor provider FAIL. Runtime and migration work remain paused
until sanitized PASS evidence is captured and independently reviewed.
