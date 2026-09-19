# PR-07 provider clarification from public Microsoft sources

**Start time:** 2026-09-19, Asia/Saigon  
**Status:** complete — exact-item session commit guarantee remains undocumented

## Initial purpose

Under approved G3 Option A, determine whether current public Microsoft material documents a
OneDrive Personal exact-item upload-session guarantee strong enough to reopen ADR 0042/D6.

This is read-only research. It authorizes no external message, Graph/OneDrive/Entra request, live
probe, ADR change, runtime code, migration, G4 or PR-08 work.

## Strategy

Review current Microsoft Learn pages and Microsoft-owned public documentation/issues. Classify each
source as normative or corroborating, answer the six approved clarification questions without
inference, and stop if the required guarantee remains undocumented.

## Checklist

- [x] Review exact-item `createUploadSession` request headers and completion examples.
- [x] Review upload-session lifetime and resumable-upload error guidance.
- [x] Review OneDrive error-code definitions.
- [x] Check the official documentation source repository for stronger wording.
- [x] Check public Microsoft-owned issue history for corroborating concurrent-write observations.
- [x] Evaluate the G3 reopen trigger.

## Result

### Source inventory

| Source | Class | Relevant documented fact |
|---|---|---|
| [Microsoft Graph `createUploadSession`](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0), accessed 2026-09-19 | Normative | `If-Match` mismatch on session creation returns `412`; automatic final-fragment completion returns `200/201`; `404` resumable guidance says the session no longer exists |
| [Microsoft Graph `uploadSession`](https://learn.microsoft.com/en-us/graph/api/resources/uploadsession?view=graph-rest-1.0), accessed 2026-09-19 | Normative | Defines expiration, missing ranges and opaque upload URL; no destination-eTag-through-commit guarantee |
| [OneDrive error responses](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/errors?view=odsp-graph-online), accessed 2026-09-19 | Normative | Distinguishes generic `itemNotFound`, `resourceModified` and `uploadSessionNotFound`; gives no stale-session mapping for `itemNotFound` |
| [Official Graph documentation source](https://github.com/microsoftgraph/microsoft-graph-docs-contrib/blob/main/api-reference/v1.0/api/driveitem-createuploadsession.md), accessed 2026-09-19 | Normative source | Matches Learn; explicit error-recovery commit uses parent/path metadata plus `sourceUrl` and may use `If-Match` |
| [OneDrive issue 1132](https://github.com/OneDrive/onedrive-api-docs/issues/1132), accessed 2026-09-19 | Corroborating only | A Microsoft contributor said concurrent requests can produce `itemNotFound`; no contract or exact-item guarantee was supplied |
| [OneDrive issue 1716](https://github.com/OneDrive/onedrive-api-docs/issues/1716), accessed 2026-09-19 | Corroborating only | Reports `resourceModified`/`412` even with an apparently current eTag; it demonstrates provider ambiguity, not a usable guarantee |

### Clarification status

| Question | Status | Finding |
|---|---|---|
| Does creation-time `If-Match` remain a commit precondition after fragments are accepted? | `UNDOCUMENTED` | Documentation defines the header on `createUploadSession`, not a durable session invariant |
| Is invalidation before final automatic completion guaranteed after a concurrent exact-item write? | `UNDOCUMENTED` | No public normative statement found |
| Is `404 itemNotFound` a documented stale-session result for that race? | `UNDOCUMENTED` | Generic error meaning is missing resource; session-specific stale causality is not defined |
| Can Personal explicitly commit by exact item ID using `sourceUrl` and `If-Match` without path/name rebinding? | `PARTIALLY_DOCUMENTED` | Error-recovery commit with `sourceUrl` and `If-Match` is shown only through a parent/path metadata request; exact-item-ID semantics required by D6 are not documented |
| Which final responses guarantee no stale bytes were committed? | `PARTIALLY_DOCUMENTED` | `412` is defined for a creation-time precondition mismatch; no final-fragment stale-response set is guaranteed |
| What supported recovery exists without blind retry? | `PARTIALLY_DOCUMENTED` | Generic guidance covers retryable `5xx` and restarting after `404`; it does not define D6-compatible same-item reconciliation |

### Reopen assessment

The G3 reopen trigger is not met. Public documentation neither binds the frozen eTag through exact-
item session commit nor defines the observed `404 itemNotFound` as a stable stale-write rejection.
The explicit `sourceUrl` recovery example uses parent/path metadata and therefore does not establish
the exact `drive_id + drive_item_id`, no-name/path-rebinding mechanism required by D6.

## Verification

The English v1.0 Learn page, its Microsoft-owned source file, the upload-session resource and the
OneDrive error catalogue were cross-checked on 2026-09-19. Search included current public issue
history for both `itemNotFound` and `resourceModified`. Corroborating issues were not promoted to
normative guarantees. No account-specific, Graph, OneDrive or Entra request was made.

## Decision

**No architecture action.** Keep ADR 0042/D6 and the PR-07 contract unchanged; C2 remains closed and
`runtime_gate=BLOCKED`. Stop public-source research at `UNDOCUMENTED`.

**Action:** retain the sanitized
[provider clarification question packet](../ref/pr07-provider-clarification-question-packet.md)
locally. Sending it through Microsoft support/docs/GitHub requires new explicit authority at send
time and is not part of this research.

**Reopen trigger:** an attributable Microsoft answer that directly addresses the six questions and
documents an exact-item conditional-commit guarantee, or a separately reviewed supported mechanism.

## Amendments

- 2026-09-19 · External escalation: after separate Product Owner authorization, the sanitized
  question was posted to [public Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/6008198/onedrive-personal-upload-session-does-if-match-rem).
  Response is pending. Posting the question does not change the `UNDOCUMENTED` result or reopen D6.
