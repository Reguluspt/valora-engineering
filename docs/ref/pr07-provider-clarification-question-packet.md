> **HISTORICAL DIRECT-WRITE RESEARCH — 2026-09-21**  
> Retained as evidence only. Do not execute/reopen this plan from current roadmap. Direct replacement of an existing OneDrive item is historical/blocked. Current document direction is ADR 0043–0045 + `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`.

# PR-07 OneDrive Personal conditional-commit clarification packet

**Submission status:** submitted with Product Owner authorization to public Microsoft Q&A on
2026-09-19; provider response pending.
**Public thread:** [OneDrive Personal upload session: does If-Match remain a commit precondition?](https://learn.microsoft.com/en-us/answers/questions/6008198/onedrive-personal-upload-session-does-if-match-rem)

The submitted packet contains no tenant, account, application, drive/item ID, upload URL, token,
secret or raw provider body. Do not repost it to another channel without separate authorization.

## Context

We update an existing OneDrive Personal item through Microsoft Graph v1.0. The intended invariant is
optimistic concurrency: an upload session created for an exact item with a frozen eTag must never
overwrite a write that changes that item before session completion.

In a bounded test, the session was created by item ID with creation-time `If-Match`. It accepted one
fragment. A separate conditional write then changed the same item's content/eTag. Sending the final
fragment to the preauthenticated upload URL returned HTTP `404` with code `itemNotFound`. An exact-
item read afterward showed that the concurrent bytes/eTag and item identity were preserved.

This single observation is not being treated as a provider guarantee. We need documented semantics
before implementing the production write path.

## Questions for Microsoft

1. On OneDrive Personal, does `If-Match` supplied to
   `POST /drives/{driveId}/items/{itemId}/createUploadSession` remain a commit precondition for the
   lifetime of that session after fragments have been accepted?
2. If the exact destination item changes after session creation, is the session guaranteed to be
   invalidated or rejected before the final fragment can overwrite the newer bytes?
3. Is HTTP `404 itemNotFound` a supported and stable response for that stale-session race? If so,
   does it guarantee that no uploaded candidate bytes were committed?
4. For OneDrive Personal with `deferCommit:true`, is there a supported explicit commit request that
   targets the existing item by immutable item ID and carries both `@microsoft.graph.sourceUrl` and
   `If-Match`, without addressing or rebinding by parent path/name?
5. Which HTTP/error-code combinations at final fragment or explicit commit guarantee that the stale
   candidate was not committed?
6. What recovery sequence is supported when the final response is lost or ambiguous, without a
   blind write retry?

## Requested answer shape

Please distinguish documented contract from current implementation behavior and identify whether the
answer applies specifically to OneDrive Personal. Links to normative Microsoft documentation are
preferred. If the behavior is not guaranteed, an explicit statement of that limitation is useful.
