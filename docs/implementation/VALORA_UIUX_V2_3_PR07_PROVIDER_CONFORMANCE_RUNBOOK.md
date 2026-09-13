# PR-07 OneDrive Personal conditional-commit conformance runbook

**Task:** `VALORA-PR07-CONFORMANCE-001` **Status:** READY TO RUN — LIVE CREDENTIAL REQUIRED
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

The machine has no retained PR-05/PR-06 client secret, token or live item configuration. A live run
therefore requires a new short-lived `Files.ReadWrite` consent/token. Runtime and migration work
remain paused until the sanitized PASS evidence is captured and independently reviewed.
