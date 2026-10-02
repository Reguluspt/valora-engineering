# OS-G2 Asset Review line decision contract

**CANDIDATE AUTHORITY — pending the same Product Owner decision as [proposed ADR 0049](../adr/0049-asset-line-human-review-and-validation-authority.md).** Issue #77 / OS-G2 A3, 2026-10-02. Baseline `b3085242d083e03f1663aa79ea3241bd48592c84`, exact-main CI #538 SUCCESS, A2 / PR #76 MERGED/CERTIFIED. Runtime implementation is **UNAUTHORIZED**.

## 1. Scope and authority distinction

[ADR 0028](../adr/0028-official-mutation-command-and-atomic-audit-gate.md) continues to govern existing value drafts and prohibit direct status PATCH. [ADR 0048](../adr/0048-post-intake-guarded-apply-and-asset-review-authority.md) and the [accepted Case State contract](VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) govern Intake, Apply v2, seal, exact current membership, serialization and full-set accepted+valid completion. This candidate supplies no runtime permission until the Product Owner explicitly accepts its bounded successor routing distinction.

Current [Human Commit](../../backend/app/modules/project_master_data/commands/commit_asset_line_draft.py) only handles description/appraised unit price. The [S11 audit](../audits/S11_PR_006_HUMAN_COMMIT_REVIEW_GATE_AUDIT.md#4-commit-field-allowlist) and [live API contract §§12–13](../design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md#13-s11-pr-006-human-commit--review-gate) do not prove status commands exist. The [A2 provider](../../backend/app/modules/project_master_data/application/asset_review_provider.py) is current runtime, not this candidate. Historical broad remediation wording has no greater authority.

No membership add/remove, new permission, workflow status advance, later stage, price approval, frontend route or generic issue engine is introduced. No stored Case State. Command proposals below are domain contracts, not live API routes/schema claims.

## 2. Common command preconditions and receipts

Both `ValidateProjectAssetLine` (`asset-line-validation-v1`) and `DecideProjectAssetLineReview` (`asset-line-human-review-v1`) require:

- One Project and line, resolved from authenticated tenant scope. Tenant/actor come from authenticated identity, never request identity. Active human account/organization; effective existing `workbench:edit`; active owned Workbench session for this Project, resolved and checked as in S11. AI/system principals cannot invoke either command or supply human confirmation.
- Strict boolean `confirm=true`; supported command contract identifier; UUID `command_id`; positive integer `expected_row_version`; exact opaque lowercase SHA-256 `expected_case_version`. Do not accept future/stale versions or coerce booleans to versions. Reject extra fields, client-selected validation status/digests/rule outputs, or bulk line targets.
- Project DRAFT for a first mutation. Current Official Intake/Result, applied exact guarded seal, unchanged authorized membership, current lineage and membership of this line proved server-side. No command over manual/unsealed/historical-v1 lines, no source/row/membership repair.
- Project first, then A2 batch/staging/all-line order via the shared resolver; read/lock the exact scoped receipt and applicable proof/decision/issue records after those locks. Reference rows used by validation/acceptance are refreshed and held stable through commit in a deterministic order. Request line version equals locked official row version; request case token equals the one shared locked resolver's token. Session ownership, permissions and references are checked again before committing.

Additional typed review inputs: `target_review_status: accepted | flagged | rejected`, `reason_note:string|null`, and `supersedes_decision_id:UUID|null`. Validation request contains no value payload or requested verdict; immutable rule set is server-selected by the pinned contract.

Receipt uniqueness is the tenant-scoped command UUID; canonical request digest also binds actor, Project, line, command/version, confirmation, both expected tokens and every typed decision input. Any UUID reuse with a different bound value conflicts with zero writes. Exact replay after fresh actor/tenant/effective-permission/session checks returns only the original receipt, marked historical if newer mutations exist; no status restoration, row increment, generation or duplicate audit. A replay is a read, may reconcile after Project leaves DRAFT, and never permits a new non-DRAFT mutation. Apply's existing replay policy and S11 value-commit contract do not change.

## 3. Closed deterministic validation v1

Use immutable code-defined rule-set identity/digest `official-asset-line-validation-v1`. Validation reads persisted official fields only. Canonical input digest covers exactly: `asset_name`, `description`, `quantity`, `unit_id`, `raw_price`, `raw_price_currency_id`, `appraised_unit_price`, `appraised_currency_id`, `brand_id`, `manufacturer_id`, plus line identity and immutable staging lineage. Explicit null differs from empty string. Use exact Decimal canonical values, not floats or rounded display text.

Reference proof covers present Unit/Currency/Brand/Manufacturer IDs and current existence/status, deterministically sorted by type/ID. These are existing global reference lookups, not tenant-owned rows with invented organization columns. Bind rule digest and Intake/seal/membership identities separately. No taxonomy/identity matching, market quotes, workflow approval or price-presence check.

| Code | Deterministic predicate | Finding |
| --- | --- | --- |
| `asset_name_invalid` | Not a string, trimmed empty or length over the existing 255-character model bound | Error |
| `quantity_invalid` | Not a finite exact Decimal, <= 0, or not representable as Numeric(15,4) without rounding (at most 11 integer digits, four fractional places) | Error |
| `description_invalid` | Non-null and not a string, or over the existing 5,000-character official description bound | Error |
| `description_blank` | Non-null valid string whose trimmed content is empty | Advisory |
| `amount_invalid` | Any present raw/appraised amount is not finite/non-negative or not representable as Numeric(15,2) without rounding (at most 13 integer digits, two fractional places) | Error |
| `reference_invalid` | Any present named reference ID is missing or not ACTIVE in its existing lookup | Error |

All predicates are evaluated; findings ordered by rule-table order, then field name/reference ID. Nullable optional fields may be absent with no finding. A missing description, Unit, currency, brand, manufacturer or appraised amount is not an error/advisory. Zero monetary values satisfy the non-negative structural check; this does not change existing commit validators or approve a price. A blank-description advisory is corrected through the existing description Human Commit; there is no warning acknowledgment/override that converts it to valid. This is a proposed Product Owner choice, not an already accepted business rule.

Result: errors present → `invalid`; otherwise advisory present → `warning`; otherwise `valid`. `unvalidated` is absence of current proof, not a validator's business result. Optional values and reference semantics make this an official-line rule set, not blind reuse of staging proposed-name/quantity checks. Existing mutable `ValidationRule` rows do not select/override these rules. No scoped `ValidationIssue` is created/updated by this command; typed findings belong to its immutable validation generation. Independent existing issues remain independently visible/blocking under their accepted target/severity/status semantics.

Every successful invocation, including invalid/warning or identical verdict, appends one new validation generation/receipt and one success audit, writes the computed validation status, increments line row_version exactly once and makes prior accepted review non-current (`accepted` resets to `pending`). Pending remains pending; flagged/rejected holds remain until human reversal. Immutable proof records bind evaluated input/reference/rule digests, generation, pre/post row versions, seal/membership, actor/session/confirmation and request receipt. Physical storage and indexes require the separate runtime task; existing model fields are not claimed to store these records today.

Technical evaluation, persistence, flush, audit or commit failure is a safe technical error, not invalid/warning: roll back status, versions, proof, receipt and audit together. A corrupt/cross-scope authoritative pointer is an integrity denial, not a business field finding.

## 4. Human decisions and lifecycle

Acceptance is `review_status=accepted` with a current immutable human decision bound to the current valid validation generation, current official-input/reference/rule proof and membership. Validation never chooses accepted. Flagged means human clarification/correction required; rejected means human refusal of this current line's review disposition, not deletion, membership removal or workflow cancellation. Pending means no current positive acceptance. All three submitted targets require explicit confirmation and versions.

From pending/accepted/flagged/rejected, a *different* submitted target is allowed under §2. Accepted additionally requires fresh valid proof and absence of open Project/target-line BLOCKING issues. Flagged/rejected may be chosen while validation is unvalidated/warning/invalid; they cannot bypass a lineage/membership mismatch. Negative status itself does not prevent a fresh explicit reversal to accepted once the valid-proof/issue conditions are met.

Flag/reject requires a trimmed non-empty reason (maximum 2,000 Unicode characters). Any existing human decision being superseded requires its exact ID and a non-empty reason, even if its positive proof became non-current. Append one new scoped immutable decision and, when applicable, an explicit reversal/supersession record linking old/new decision; preserve all prior notes and outcomes. This is a bounded candidate domain reversal, not reuse of unrelated ChangeRequest approval or permission to rewrite the existing generic ReviewDecision model. Exact storage adaptation must maintain these bindings; raw freeform notes stay in the protected decision record, not the audit payload.

| Event/current condition | Validation authority | Review authority / stage effect |
| --- | --- | --- |
| First guarded Apply | Stored unvalidated; no official validation proof | Pending; INCOMPLETE; validate next |
| Validation valid | New current valid generation | Pending unless negative hold remains; review next; no automatic acceptance |
| Validation warning | New current warning generation | Cannot accept; INCOMPLETE unless independent blocker/negative hold; correction then confirmed revalidation |
| Validation invalid | New current invalid generation | BLOCKED; correct values then confirmed revalidation; no automatic issue resolution |
| Human accepted | Unchanged current valid generation | One current acceptance; project COMPLETE only if full set qualifies |
| Human flagged/rejected | Validation unchanged | Durable negative hold; BLOCKED; requires explicit human reversal |
| Actual official input edit via S11 Human Commit or allowed non-restricted PATCH | Prior proof becomes non-current by exact input digest; stored validation strings are historical | Prior positive acceptance non-current; negative holds survive; validation required; no direct status PATCH/reset |
| Draft save / failed edit / same canonical values | Current proof unchanged | No positive proof invalidation merely from draft or unrelated row-version change; CAS may still advance on a committed row write |
| Current reference eligibility/rule digest changes | Prior proof non-current | Positive acceptance non-current; validate next; unavailable reference may yield invalid on explicit validation |
| Scoped blocker created/opened | Proof unchanged; issue token changes | BLOCKED even if accepted+valid; positive decision remains recorded |
| Scoped blocker resolved/ignored through existing authority | No validation/decision generation created | Recompute stage; unchanged current acceptance can qualify again; line invalid/negative status is not cleared |
| Client token stale/future | No write | Conflict/reload; fresh projection is not STALE merely from old client memory |
| Immutable lineage/seal/current membership mismatch | Neither command may repair/validate it | Existing A2 STALE/BLOCKED precedence and diagnostic recovery; no mutation route |
| Confirmed revalidation on unchanged or corrected inputs | New generation even if same verdict | Prior accepted resets pending; negative holds preserved; valid requires new human acceptance |

Proof currentness compares scoped membership/line identity, current input/reference/rule digests and the latest applicable generation/decision links. It does not require a proof's recorded post-row-version to equal the present row_version: a human review or a same-value write advances CAS without changing validation inputs. Acceptance additionally binds the latest validation generation; any revalidation invalidates it even on identical inputs/verdict. Recorded row versions remain invocation/audit evidence, not a self-invalidating proof check.

Read-time currentness checks never flush, write, audit or persist Case State. The successor provider must distinguish historical stored strings from current authority: an obsolete invalid/warning validation is unfinished revalidation work, not a permanent business-invalid verdict; negative human holds remain blockers. With current lineage and no independent blocker, proof obsolescence from an authorized value/reference change is INCOMPLETE, not immutable-lineage STALE. Existing value mutation paths retain their field/permission rules; no unconfirmed restricted status side effect is added.

## 5. Case State and Next Action successor

Keep public stage results `NOT_AVAILABLE | BLOCKED | STALE | INCOMPLETE | COMPLETE` and action kinds `BLOCKER | PENDING | UNAVAILABLE | NO_AUTHORIZED_DOWNSTREAM_ACTION`. Availability, scoped issues, membership/entry blockers, current negative line findings and lineage stale precede unfinished work in existing A2 order. Preserve deterministic seal order `(source_row_number, staging_row_id, line_id)` and choose the first unfinished line, then the needed operation **on that line**; do not reorder the entire set by validation versus review.

| Current line condition after higher priorities | Kind / proposed semantic key | Typed context additions to A2 line context |
| --- | --- | --- |
| No current validation proof (including authorized input/reference changes) | PENDING / `asset_review_line_validate_required` | Reason `line_validation_required`; pinned validation contract; explicit confirmation required |
| Current warning, no negative hold | PENDING / `asset_review_line_validate_required` | Reason `line_validation_warning`; correction required before useful revalidation; current generation ID, deterministic finding codes; no override/auto-retry |
| Current valid proof; no current positive review | PENDING / `asset_review_line_review_required` | Reason `line_human_review_required`; validation generation ID; current/prior decision ID if present; explicit confirmation required |
| Current invalid validation or flagged/rejected hold | Existing BLOCKER / `asset_review_line_blocked` | Existing negative reason; fresh line/validation/decision identity where proved; diagnostic navigation for correction/revalidation or explicit human reversal, never automatic clearing |
| Full authoritative set has current accepted+valid proofs, no blocker/stale | Existing NO_AUTHORIZED_DOWNSTREAM_ACTION / null key | No later stage/command target |

Retain project_id, case_version, membership_version, line_id and line_row_version typed context. Never publish reason notes, values, SQL or paths in routing context. Mutation prerequisites are checked per branch; missing effective workbench:edit/session yields UNAVAILABLE, null mutation route/target and safe permission/session reason without changing account-independent stage truth. Higher-priority read-only diagnostics may remain. Current API exposes no new key/context until separately authorized activation.

Current A2 `asset_review_line_pending` combines two different missing authorities; it is insufficient as the successor's actionable routing identifier. The two bounded keys are proposed, not live. Preserve current_stage at ASSET_REVIEW once the four prefix stages complete; no ASSET_WORKBENCH+ activation or Project workflow transition.

Use one shared resolver/serializer with candidate envelope `global-case-state-v3-asset-review-line-decision-v1`, preserving every A2 input and adding all member lines' current input/reference/rule digests, validation-generation identity/currentness and human-decision/reversal identity/currentness (explicit absence included). Stable canonical serialization remains A2's algorithm; there is no second hashing implementation. This explicit successor avoids silently changing v2 semantics. Every new committed generation/decision increments row_version and changes token even for identical verdicts. Existing issue changes continue to alter the token, including warnings and resolved/ignored issues. Digests/generations, not freeform display text or actor permissions, enter canonical facts.

## 6. Audit/cardinality and recovery

| Outcome | Official/proof/receipt writes | Command AuditEvents |
| --- | --- | --- |
| First successful validation valid/invalid/warning | Exactly one generation, receipt and row-version increment; accepted reset if applicable | Exactly one `ProjectAssetLineValidated` |
| First successful human decision | Exactly one decision, receipt and row-version increment; reversal link if applicable | Exactly one `ProjectAssetLineReviewDecided` |
| Exact receipt replay / same-target no-op denial / contract, state, scope, permission, CAS or proof denial | Zero | Zero |
| Technical or audit failure, known rollback | Zero committed effects | Zero |
| Unknown commit reconciled as committed | Original atomic effects only | Original one success audit only |

Safe denial classes: malformed/missing contract/confirmation/versions/reason → 400; missing/inactive/unauthorized identity → established 401/403; inaccessible or cross-scope target/session → safe 404; non-DRAFT first mutation → 400; mismatched tokens/proof/membership/lineage, UUID-content conflict or same-target new command → 409. No technical failure converts line status to invalid; validation business findings return a successful typed outcome, not a retryable engine error.

Audit metadata is tenant/actor/Project/line, command ID/contract, session ID, membership/seal identity, input/reference/rule digests, generation/decision IDs, old/new row versions, prior/new statuses, confirmation and bounded finding codes; human decision adds prior decision/reversal IDs and reason-present flag. No raw field values, freeform reason notes, client files, credentials, SQL, stack or bulk line arrays. Audit sanitizer compatibility/allowlist and protected reason storage must be proven before runtime activation.

After timeout, read the exact scoped command receipt and its immutable proof/decision plus required audit. Matching committed receipt reconciles only that historical operation; compare fresh Case State to see current work. Never infer success from a line status alone. If absent with no committed outcome, reload row/case tokens and explicitly reconfirm before a new attempt. If outcome cannot be reconciled, stop mutation; no blind retry, fake receipt, status repair or stale failure audit. Any recovery lock follows Project first and suppresses writes against newer authority.

## 7. Decision boundary and future certification

Product Owner must decide the ADR bundle, especially: valid-before-accept; blank-description advisory with optional-null validity; existing permission plus owned session and human confirmation for both commands; proof currentness with negative holds; explicit append-only reversal; per-command receipt replay; and the versioned token/two-key successor. Preferred answer is accept these as one coherent contract; weaker alternatives are rejected in ADR 0049. Acceptance is not runtime authorization.

The separately assigned runtime gate must prove real PostgreSQL concurrency for review/validation/edit/issue/Project/reference changes and recovery in both orders, exact input-proof invalidation across every existing allowed writer, same-verdict generation changes, scoped receipts/replays, warning/invalid separation, safe currentness reads, audit rollback and unknown commits. It must demonstrate negative holds cannot be cleared by values/validation, old strings cannot yield COMPLETE, current full membership only, no new grants/public enums and no later-stage route. Physical storage/migration/API/UI decisions are deferred to that bounded implementation task. Tests in this authority-only task are N/A; referenced paths, diff hygiene, dual frozen-head review and exact-head CI remain required.

PRODUCT OWNER DECISION REQUIRED: YES
