> **HISTORICAL DIRECT-WRITE RESEARCH — 2026-09-21**  
> Retained as evidence only. Do not execute/reopen this plan from current roadmap. Direct replacement of an existing OneDrive item is historical/blocked. Current document direction is ADR 0043–0045 + `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`.

# PR-07 — C2_AUTO_V2 partial-response local correction plan

**Status:** Completed locally on 2026-09-19; verification and independent review `READY`.

**Goal:** Correct the over-strict first-fragment response predicate, retain bounded diagnostics for
the same boundary, and preserve historical C1/schema-v2 evidence without performing network work.

**Authority:** This document records the approved local implementation and closeout. It does not
authorize Graph/OneDrive access, Entra changes, another live invocation, commit, push, PR, merge or
runtime enablement.

**Candidate:** `C2_AUTO_V2`. **Evidence schema:** `3`. **Runtime gate:** `BLOCKED`.
**G3–G4:** closed.

**Research basis:**
[C2 partial-response semantics](../research/pr07-c2-partial-response-semantics.md).

## 1. Scope and invariants

Allowed implementation scope after separate local approval:

- `backend/tools/pr07_onedrive_personal_if_match_probe.py`
- `backend/tools/pr07_onedrive_personal_if_match_launcher.mjs`
- `backend/tools/pr07_onedrive_personal_live_controller.py`
- `backend/tests/test_pr07_onedrive_personal_if_match_probe.py`
- `backend/tests/test_pr07_onedrive_personal_live_controller.py`
- directly related PR-07 documentation

The correction must preserve all current safety properties:

- exact drive/item-ID targeting after fixture creation;
- one sequential two-fragment session per reached branch;
- no `Authorization` header on the preauthenticated upload URL;
- no polling, status GET, resend, retry, fallback or replacement session;
- coherent exact-item post-read after every dispatched partial or final fragment;
- no final fragment unless the partial response and destination preservation both validate;
- session cancel and recycle-bin fixture cleanup on every reachable exit;
- no raw response body, raw range, upload URL, token, secret or callback material in evidence;
- `runtime_gate=BLOCKED` in every report.

Do not touch `backend/app/**`, database migrations, frontend, workers, PR-05 credential behavior,
accepted ADR/contract text or unrelated formatting.

## 2. Version and compatibility contract

Use `C2_AUTO_V2` with schema version `3`; do not relabel or mutate the finalized
`C2_AUTO_V1`/schema-v2 evidence.

The controller must have three explicit readers:

1. legacy C1 evidence;
2. schema v2 + `C2_AUTO_V1`, read-only compatibility;
3. schema v3 + `C2_AUTO_V2`, current producer and live-candidate validator.

Unknown versions, mixed version/candidate pairs and v3 fields in v2 records fail closed. The
unresolved-ledger scanner must continue to resolve the existing finalized v2 attempt and must not
route it through the C1 parser. Controller, launcher and probe self-tests use only the current v3
candidate. A live CLI invocation must reject `C2_AUTO_V1`; historical support is read-only.

## 3. Bounded range parser

Add one pure parser/classifier with inputs `nextExpectedRanges`, `expected_start=327680` and
`total=655360`. It must not receive or persist the full response object.

Accepted response requirements:

- HTTP status is exactly `202`;
- `nextExpectedRanges` is a non-empty list with an explicit small upper bound;
- every element is a bounded-length string matching decimal `start-end` or `start-` syntax;
- booleans, signs, whitespace, decimals and non-string values are invalid;
- every start is within `327680..655359`;
- every finite end satisfies `start <= end <= 655359`;
- the first range starts at exactly `327680`;
- duplicate, overlapping or internally contradictory finite ranges fail closed;
- both `"327680-"` and `"327680-655359"` are accepted;
- a bounded multi-range value is accepted only when all ranges are valid and the final fragment
  `327680-655359` covers them all.

The parser returns only one enum:

- `EXPECTED_START`
- `UNEXPECTED_START`
- `MISSING`
- `MALFORMED`

`EXPECTED_START` is the only class that permits the final fragment. The existing coherent
destination-preservation check remains a separate mandatory gate.

## 4. Evidence schema v3

Add one exact-key report object:

```json
{
  "fresh": {"http_status": null, "range_class": "NOT_OBSERVED"},
  "stale": {"http_status": null, "range_class": "NOT_OBSERVED"}
}
```

The report key is `partial_observations`. Each role has exactly `http_status` and `range_class`.
Status is `null` or a real integer in `100..599` with booleans rejected. Allowed classes are:

- `NOT_OBSERVED`: no HTTP response object was available;
- `NOT_APPLICABLE`: a response existed but status was not `202`, so no range was parsed;
- `EXPECTED_START`, `UNEXPECTED_START`, `MISSING`, `MALFORMED`: parser results for a `202`.

Add reason codes `PARTIAL_HTTP_UNEXPECTED`, `PARTIAL_RANGE_MISSING`,
`PARTIAL_RANGE_MALFORMED` and `PARTIAL_RANGE_UNEXPECTED`. Preserve `TRANSPORT_UNKNOWN` for a
dispatched request without an HTTP response. `phase` continues to identify fresh versus stale.

Add `PARTIAL_FRAGMENT_RESPONSE_OBSERVED` to the v3 journal only. It has exact fields
`session_role`, `http_status` and `range_class` plus the common journal envelope. It is emitted once
after an HTTP response exists and before `PARTIAL_FRAGMENT_RESPONSE_VALIDATED` or the mandatory
post-read. It contains no raw range. A transport exception emits no false response-observed event;
the terminal report retains `NOT_OBSERVED`.

The v3 scanner must verify:

- request-start precedes response-observed when the latter exists;
- response-validated requires observed `202` + `EXPECTED_START`;
- post-read occurs after every dispatched partial request, including rejected or unknown outcomes;
- report observations agree with journal observations;
- final-fragment start requires response-validated and destination-verified for the same role;
- no extra request, validation or response event exists for either role.

## 5. Probe behavior

For each reached role:

1. Persist partial request-start before the PUT.
2. Dispatch once.
3. If an HTTP response exists, store only its status and bounded range class, then journal the
   sanitized observation.
4. Always perform the coherent exact-item post-read after dispatch.
5. Stop and classify if status/range validation or preservation fails.
6. Continue to the final fragment only for `202` + `EXPECTED_START` + preserved destination.

Fix the fake provider's defaulting bug by replacing `partial_range or ["327680-"]` with an explicit
`None` check so tests can represent an empty returned list.

Do not add a session-status request. The correction validates the provider response already
received; it does not change the live network experiment.

## 6. Required tests

### Parser and probe

- accept `["327680-"]`;
- accept `["327680-655359"]`;
- accept a valid bounded multi-range tail covered by the second fragment;
- reject empty/missing/non-list values;
- reject wrong first start, any start below or beyond the expected tail and out-of-bounds end;
- reject malformed, boolean-like, signed, whitespace, overlapping and duplicate ranges;
- classify non-`202` without parsing its body;
- retain status/class only and never raw payload/range text;
- perform post-read after every dispatched partial outcome;
- never dispatch final after invalid partial evidence;
- preserve existing safety-violation precedence for nonfinal mutation;
- continue to fresh/stale final behavior when a documented finite range is returned.

### Launcher, controller and ledger

- exact-key/type validation for the v3 report and nested observations;
- reject unknown keys/classes, boolean statuses and mixed candidate/schema pairs;
- v3 journal ordering and terminal/report agreement;
- transport-unknown path with no fabricated response event;
- resolved and unresolved v3 cleanup cases;
- finalized `C2_AUTO_V1` schema-v2 fixture remains resolvable;
- legacy C1 fixtures retain their existing result;
- v2 event/report fields are rejected in v3 and vice versa;
- self-test remains `network=NOT_ATTEMPTED`.

## 7. Verification and independent review gate

Run only local checks:

1. focused controller/probe tests;
2. Ruff on the touched Python files;
3. Python compilation for controller and probe;
4. `node --check` for the launcher;
5. real controller → Node → probe self-test with `network=NOT_ATTEMPTED`;
6. `git diff --check`;
7. independent review against exact hashes of the three tools and two test files.

The review must specifically attack parser permissiveness, schema-v2 compatibility, event ordering,
post-dispatch reads, cleanup resolution and accidental extra network requests. Any P0–P3 finding is
fixed locally and the affected checks/review rerun. Record final hashes and results in the PR-07
runbook and acceptance matrix without rewriting historical observations.

## 8. Exit condition

This plan is complete only when an approved local implementation has passed all checks and an
independent reviewer reports no unresolved P0–P3 finding on the recorded snapshot. Completion does
not open G3, G4 or a live gate.

If a future `C2_AUTO_V2` live attempt is considered, it requires a new explicit action-time approval,
new temporary delegated permission/credential handling and an invocation budget stated at that
time. It is a new candidate observation, not a retry of the consumed `C2_AUTO_V1` attempt.

## 9. Completion record — 2026-09-19

The approved local correction is implemented in the three tools and two focused test files listed
in section 1. The final focused suite passed `89/89`; Ruff, Python compilation, Node syntax and
`git diff --check` passed. A real controller → Node → probe self-test returned `PASS` with
`network=NOT_ATTEMPTED`, and the canonical prior-attempt resolver returned
`CANONICAL_LEDGER_UNRESOLVED=False`.

Independent review attacked parser permissiveness, version compatibility, report/journal parity,
post-dispatch read ordering and cleanup resolution. Review findings were corrected and covered by
regressions, including mandatory partial/final post-reads, final-response uniqueness, non-`202`
body avoidance, pre-final read substitution and false session completion without a role-matched
`200/201`. The final review matched all five hashes and returned `READY` with no P0–P3 finding:

- controller: `64af797e46d4f1a548ed6fc9268f1880ad8387a8c6e2e0b9f0a04a3fa5b9ff8d`;
- launcher: `50940a6146f1209299deb28216dd24ca31afcd4ca57818c7d7a50689c304e0c0`;
- probe: `9840ed3014c1434f99a5ac9d933b14d486b4493dfff8e049b89d9b750e6fba0f`;
- controller tests: `7bcdb25f6bd6c6407fb3cc904d6af8695e5824e06b312827f6211a3ad2ce6cd5`;
- probe tests: `be9026485bd14a0ec746e41a9ad400f28e06c56bea5ffbd0f99012801ddc1dc9`.

This closes only the local correction and review gate. No OAuth, Entra, Graph, OneDrive or other
network action occurred; `runtime_gate=BLOCKED`, G3–G4 and PR-08 remain closed.
