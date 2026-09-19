# PR-07 — provider clarification read-only plan

**Status:** COMPLETE — PUBLIC SOURCES UNDOCUMENTED
**Date:** 2026-09-19
**Authority:** G3 Option A approved by Product Owner

## Goal

Find normative Microsoft evidence for or against an exact-item OneDrive Personal conditional commit
that remains bound to a frozen eTag through upload-session completion. This work may clarify the
architecture reopen trigger; it cannot itself reopen runtime.

## Allowed work

- Read current Microsoft Learn pages, official Microsoft-owned documentation repositories and
  already-public Microsoft issue/support material.
- Compare version history or source changes in those public documents.
- Prepare a minimal, sanitized question packet for a future Microsoft support/docs request.
- Update research findings and the documentation index locally.

## Prohibited work

- No Graph, OneDrive or Entra request, permission change, secret, fixture or live probe.
- No retry or renamed rerun of C1, `C2_AUTO_V1` or `C2_AUTO_V2`.
- No GitHub issue, support ticket, email, forum post or other external message without separate
  authorization at send time.
- No ADR/contract semantics change, runtime code, migration, G4 or PR-08 work.

## Clarification questions

1. Does `If-Match` on exact-item `createUploadSession` remain a commit precondition after the session
   has accepted one or more fragments?
2. When the exact destination item changes concurrently, is session invalidation guaranteed before
   automatic completion of the final fragment?
3. Is HTTP `404 itemNotFound` a documented stale-session result for that race, or only a generic
   missing-resource/session signal?
4. Can OneDrive Personal explicitly commit a deferred exact-item session through a Graph request
   that carries both `@microsoft.graph.sourceUrl` and `If-Match` without path/name rebinding?
5. Which response codes are guaranteed to mean no stale bytes were committed?
6. What recovery/read-after-error sequence does Microsoft support without a blind provider retry?

## Evidence acceptance

Accepted clarification must be attributable to current official Microsoft documentation or an
explicit Microsoft response addressing the exact OneDrive Personal update flow. SDK behavior,
community anecdotes and repeated safe observations are corroboration only.

## Deliverables

- [x] Source inventory with access date and normative/corroborating classification.
- [x] Exact answer status for each clarification question: answered, partially documented or
      undocumented.
- [x] Sanitized question packet containing no account, drive/item ID, upload URL, token or secret.
- [x] Reopen assessment against the trigger in
      [the G3 evaluation](../../research/pr07-stale-session-404-decision.md): not met.
- [x] `git diff --check` and documentation-index synchronization.

## Stop condition

If public official material remains silent, record `UNDOCUMENTED` and stop. Do not substitute another
live observation for a provider guarantee and do not send the prepared question packet without new
authority.

## Completion

The public-source pass is recorded in
[provider clarification from public sources](../../research/pr07-provider-clarification-public-sources.md).
The exact-item commit guarantee remains undocumented, so the reopen trigger is not met and this plan
stops. At completion time, a sanitized
[question packet](../../ref/pr07-provider-clarification-question-packet.md) had been prepared locally
but had not been sent; the separately authorized later submission is recorded below.

## Post-completion external escalation

With separate send-time Product Owner authorization, the sanitized packet was posted to
[Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/6008198/onedrive-personal-upload-session-does-if-match-rem)
on 2026-09-19. This does not reopen the completed research plan, authorize another provider mutation
or change D6. An attributable Microsoft answer must still satisfy the evidence acceptance section.
