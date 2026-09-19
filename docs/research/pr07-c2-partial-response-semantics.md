# PR-07 C2 partial-response semantics research

Status: amended 2026-09-19 — live observation closed under G3 Option A

## Start time

2026-09-18, Asia/Saigon.

## Initial purpose

Determine whether the first-fragment predicate used by `C2_AUTO_V1` matches the published
Microsoft Graph contract, and identify the smallest safe next step after the single live attempt
stopped before the fresh final fragment.

This research does not authorize another Graph invocation, an Entra permission/secret change, an
ADR change, or PR-07 runtime work.

## Strategy

1. Separate retained facts from assumptions at the live failure boundary.
2. Compare the predicate with current Microsoft Graph documentation and official SDK parsers.
3. Trace the local report and journal validators across the probe, launcher and controller.
4. Choose a correction that remains fail-closed, preserves historical evidence and improves the
   next observation without adding a retry or an extra provider call.

## Checklist

- [x] Confirm the exact local predicate that stopped the attempt.
- [x] Confirm fragment size, order and upload-URL header behavior against Microsoft documentation.
- [x] Check how official Microsoft Graph SDKs interpret `nextExpectedRanges`.
- [x] Determine what the finalized local evidence can and cannot reconstruct.
- [x] Trace schema and journal compatibility implications of additional diagnostics.
- [x] Record a bounded correction proposal.
- [ ] Implement the correction.
- [ ] Complete local verification and independent review on the corrected snapshot.
- [ ] Request any new live authority.

## Result

### Retained facts from `C2_AUTO_V1`

The one authorized live attempt, `af114cc0-4a10-46eb-ba60-108facc7daa0`, created the isolated
fixture and a fresh exact-item upload session, then dispatched one `327680`-byte fragment for a
`655360`-byte payload. A coherent exact-item post-read proved that the item ID, eTag and bytes were
unchanged. The probe stopped before the final fragment, concurrent write and stale branch. Session
cancellation and recycle-bin fixture cleanup completed.

The retained journal proves that the exact partial-response validator did not pass. It does not
retain the partial HTTP status or a bounded classification of the returned range. The response can
therefore no longer be distinguished among an alternate valid range representation, missing or
malformed JSON, a non-`202` response, or another rejected shape. No inference about the actual
provider response is justified beyond the failed predicate.

### Published provider contract

Microsoft documents that upload fragments must be sequential and, when split, each fragment size
must be a multiple of `320 KiB`. The current first fragment is exactly `320 KiB`. An intermediate
successful upload returns HTTP `202` and `nextExpectedRanges`, but the documented representation is
a collection of missing ranges rather than one fixed literal. The examples include an open-ended
range such as `"26-"`; the documentation also warns that multiple ranges can be returned, that the
property might not list every missing range and that returned ranges are not upload-size
instructions.

The official Microsoft Graph JavaScript SDK parses the first returned range and accepts a missing
end value. The official .NET SDK parses every returned range and supports both finite and
open-ended forms. Neither implementation requires equality with one literal array value.

Sources:

- [Microsoft Graph — createUploadSession](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0)
- [Microsoft Graph JavaScript SDK — LargeFileUploadTask](https://github.com/microsoftgraph/msgraph-sdk-javascript/blob/dev/src/tasks/LargeFileUploadTask.ts)
- [Microsoft Graph .NET SDK Core — LargeFileUploadTask](https://github.com/microsoftgraph/msgraph-sdk-dotnet-core/blob/main/src/Microsoft.Graph.Core/Tasks/LargeFileUploadTask.cs)

### Local mismatch

`C2_AUTO_V1` accepts the first partial response only when all of the following are true:

```text
HTTP status == 202
response JSON is an object
nextExpectedRanges == ["327680-"]
```

The equality check is stricter than the published provider contract. It rejects a finite equivalent
such as `"327680-655359"` and any bounded multi-range representation even when the second fragment
would cover the entire remaining tail. This is a local false-negative risk; it is not proof that the
live response was contract-conforming because the discarded response cannot be reconstructed.

### Correction boundary

The smallest reliable correction has two inseparable parts:

1. Parse bounded documented range forms and proceed only when the first missing byte is exactly
   `327680`, every returned range is well formed and lies inside the remaining tail, and the
   destination-preservation post-read still passes.
2. Persist only a bounded partial observation: HTTP status plus a range classification. Do not
   retain raw response bodies, raw range strings, upload URLs or credentials.

Adding those observations changes the exact report and journal schemas in the probe, Node launcher
and controller. Reusing schema v2 would make two different shapes share one version and risks
misclassifying the finalized `C2_AUTO_V1` ledger. The correction should therefore use a new
candidate `C2_AUTO_V2` and schema version 3, while preserving explicit read-only compatibility for
legacy C1 and finalized schema-v2 evidence.

No upload-session status GET, polling, resend or fallback is needed. The corrected candidate keeps
the same two-fragment network shape and always performs the coherent destination post-read after a
dispatched first fragment.

## Verification

The conclusions were cross-checked against the current probe implementation, its fake-provider
tests, the launcher's exact-key validator, the controller's report validator and its durable-journal
state machine. The existing finalized artifact and event journal were inspected only through their
previously retained sanitized facts; no provider or Entra action was performed.

## Decision

Prepare `C2_AUTO_V2` as a local-only correction under
[the bounded implementation plan](../plan/pr07-c2-auto-v2-local-correction.md). Keep G3 and G4
closed. Implementation, local verification and independent review are a separate step; any future
live attempt requires new explicit action-time approval and must not be described as a retry of the
consumed `C2_AUTO_V1` invocation.

## Amendments

### 2026-09-19 — local correction closeout

The separately approved `C2_AUTO_V2`/schema-v3 local implementation, verification and independent
review are complete under
[the bounded implementation plan](../plan/pr07-c2-auto-v2-local-correction.md). The final review
matched all five supplied hashes and returned `READY` with no P0–P3 finding; focused tests passed
`89/89` and the controller → Node → probe self-test remained `network=NOT_ATTEMPTED`.

This amendment records local completion only. It does not reconstruct the discarded live response,
change the `C2_AUTO_V1` observation, amend ADR 0042/D6, authorize a `C2_AUTO_V2` live attempt or open
G3, G4, PR-07 runtime, migrations or PR-08.

### 2026-09-19 — single C2_AUTO_V2 live observation

The Product Owner later granted separate action-time authority for exactly one `C2_AUTO_V2` live
invocation on the reviewed snapshot. Attempt `2a06438c-5ad2-46f1-8da2-b60776647f86` passed OAuth.
Both first-fragment responses were HTTP `202` with bounded range class `EXPECTED_START`, confirming
that the schema-v3 partial-response correction admitted the provider's documented response shape.
The fresh final fragment returned HTTP `200`, and coherent post-read proved the fresh commit.

After a verified concurrent write, the stale final fragment returned HTTP `404` with provider code
`itemNotFound`, rather than candidate `412`. The subsequent coherent read proved item identity and
the concurrent bytes/eTag were preserved. The sanitized terminal record is
`INCONCLUSIVE` / `ALTERNATE_REJECTION`, with `stale_candidate_observed=false` and
`runtime_gate=BLOCKED`. There was no retry.

The stale session was cancelled and the fixture was deleted to the recycle bin. The canonical
ledger and local sensitive state are clean. The temporary secret and delegated `Files.ReadWrite`
were removed, and read-only Entra verification confirmed the restored baseline of the single PR-05
secret plus delegated `Files.Read` only.

This observation closes the authorized experiment but does not establish the D6-required HTTP
`412`, amend ADR 0042/D6 or open PR-07 runtime, migrations, G3, G4 or PR-08. Any further provider
experiment requires a new research decision and new action-time authority.

### 2026-09-19 — G3 Option A approved

The Product Owner approved G3 Option A: retain ADR 0042/D6, close C2 research and do not accept
`C2_AUTO_V2` as a production write mechanism. `runtime_gate=BLOCKED`; PR-07 runtime/migrations, G4
and PR-08 remain closed. Only the separate read-only provider-clarification plan may continue.
