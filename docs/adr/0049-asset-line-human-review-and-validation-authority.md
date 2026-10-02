# ADR 0049: Asset-line human review and validation authority

## Status and scope

**PROPOSED / PRODUCT OWNER DECISION REQUIRED.** OS-G2 A3 / [Issue #77](https://github.com/Reguluspt/valora-engineering/issues/77), 2026-10-02. Verified baseline `main=b3085242d083e03f1663aa79ea3241bd48592c84`, exact-main CI #538 SUCCESS; A2 / PR #76 MERGED/CERTIFIED; migration head `f3a4b5c6d7e8`.

This proposal and the [candidate line decision contract](../implementation/VALORA_OS_G2_ASSET_REVIEW_LINE_DECISION_CONTRACT.md) require one explicit Product Owner decision. They do not authorize runtime, schema, API, RBAC or UI changes. Nothing here is self-accepted. Historical authority descriptions in ADR 0048 are dated context; its A2 runtime is now implemented at this baseline.

Binding boundaries: [CODEX](../../CODEX.md), [permanent mutation guardrails](../../ENGINEERING_GUARDRAILS.md#6-official-mutation-guardrails), [ADR 0028](0028-official-mutation-command-and-atomic-audit-gate.md), [ADR 0048](0048-post-intake-guarded-apply-and-asset-review-authority.md) and the [accepted Asset Review contract](../implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md). Initial sealed membership, exact lineage, Project-first serialization, full-set completion and the ASSET_REVIEW stage cap are unchanged.

## Verified authority gap

The [S11 accepted audit §4](../audits/S11_PR_006_HUMAN_COMMIT_REVIEW_GATE_AUDIT.md#4-commit-field-allowlist), [live API contract §§12–13](../design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md#12-s11-pr-005-inline-draft-editing-contract) and actual [draft command](../../backend/app/modules/project_master_data/commands/commit_asset_line_draft.py) permit only `description` and `appraised_unit_price`. Both runtime handler registries have exactly those entries. The [direct PATCH](../../backend/app/api/projects.py) rejects presence of either value field or either status field, including explicit null.

The [model](../../backend/app/modules/project_master_data/models.py) has review `pending | accepted | flagged | rejected` and validation `unvalidated | valid | invalid | warning`. A2 starts lines at pending/unvalidated; the [provider](../../backend/app/modules/project_master_data/application/asset_review_provider.py) requires every member accepted+valid. Historical prose claiming generic Human Commit already handles status decisions does not supply the missing command authority.

ADR 0028's draft-path wording currently does not authorize either proposed status command. Product Owner acceptance must explicitly ratchet that bounded routing distinction through this successor, retaining authentication, permissions, DRAFT, human confirmation, exact versions and atomic audit. Until then, current code and ADR 0028 remain binding. No historical ADR body or permanent guardrail is rewritten in this task.

## Preferred contract

### D1. Separate purposes and human boundary

1. `CommitProjectAssetLineDraft` remains the only existing draft command for description/appraised unit price, with its exact draft-base/line-version equality, owned active Workbench session, validators and audit. No status is added to draft JSON, `FIELD_HANDLERS` or `MUTATION_REGISTRY`.
2. Propose `ValidateProjectAssetLine`: a human explicitly requests and confirms synchronous deterministic validation of one sealed official line. The server selects the immutable rule set and computes the outcome. The human cannot select a validation status, rule result or input digest. This is an official-line command; staging validation remains staging-only.
3. Propose `DecideProjectAssetLineReview`: an explicit human decision for one sealed official line, targeting accepted, flagged or rejected. It never assigns validation authority or edits values.

Both new commands require `confirm=true`, active human identity/organization, effective existing `workbench:edit`, an active owned Workbench session, DRAFT, exact row and shared Case State tokens, current Intake/seal/membership/lineage and atomic audit. No new permission, grant, privileged role shortcut, system caller, AI caller, job, auto-validation or auto-review is authorized. Deterministic execution occurs only within the human-confirmed command, not a rule engine's independent persistence call.

### D2. Human review

Pending means no current positive acceptance; it is initial/reset state, not a submitted target. From any existing review state, a human may choose a *different* target among accepted/flagged/rejected. Repeating the same target with a new command ID is a no-op denial; exact command replay follows D6.

Acceptance requires a current deterministic **valid** generation for the exact current official inputs and rule/reference facts, and no open blocking issue on the Project or this line. Another line's issue still blocks project completion, but does not prevent a scoped decision on this otherwise eligible line. Warning cannot be accepted as valid. Flag/reject is allowed without valid validation, to record a known human impediment, provided scope/seal/lineage are current.

Flag/reject requires a trimmed non-empty reason note of at most 2,000 Unicode characters. Any change superseding a prior human decision additionally requires a reason and exact prior decision ID. A successor decision appends an explicit reversal/supersession link to the prior decision; neither record is edited/deleted. This is the proposed bounded reversal authority, not permission to use generic workflow approval as line acceptance. No untyped mapping to existing ReviewDecision choices is assumed.

### D3. Deterministic official validation

Propose immutable rule-set identity `official-asset-line-validation-v1`, with the exact inputs/rules in companion §3. Validate current official values, not spreadsheet proposals, drafts or cached UI values. Required name/quantity integrity, optional field type/Decimal validity and the current eligibility of present Unit/Currency/Brand/Manufacturer references are structural checks. No appraised price, currency, description, identity match or later-stage fact is required to exist for completion.

Invalid means at least one business error; warning means no error but at least one explicitly listed advisory; valid means neither. Warning is not a scoped BLOCKING issue, but still fails accepted A2's valid-only completion/acceptance predicate. Unvalidated means no current validation proof. Do not silently downgrade warning to valid, permit manual overrides or execute arbitrary mutable ValidationRule rows.

No ValidationRule/ValidationIssue CRUD is reused for rule results in v1. Persist typed findings with the immutable validation generation. Existing independently scoped issues retain their own authority, permissions and Project-first writers; validation cannot create, resolve, ignore or severity-convert them. Business invalid/warning is a successful audited command outcome. Technical failure is no committed validation outcome and must not be recorded as business invalid.

### D4. Proof currentness and edits

Validation generations bind the exact official-input digest, immutable rule-set digest, current reference-fact digest and sealed membership/line identity. Every committed validation attempt creates a new generation and increments line row_version once, even when verdicts match. Prior accepted review binds its validation generation and official-input digest: a fresh validation generation requires a fresh human acceptance. Flagged/rejected holds survive value edits and revalidation until an explicit human reversal; neither operation clears a negative human decision.

All official content covered by companion §3 participates in both validation and review currentness. An actual value change makes earlier validation and positive acceptance non-current in the same transaction's new facts. Draft save alone changes neither. Input writers must never leave cached status strings sufficient for completion.

For the existing non-restricted `project:update` PATCH, preserve its value-field permission and restricted-status prohibition: do **not** write status resets through PATCH. Instead currentness is derived by the shared resolver from the new official-input/reference facts and the immutable proofs. Stored accepted/valid strings with mismatched proofs are historical, not current authority. The successor provider must expose unfinished validation work and suppress COMPLETE; a subsequent human-confirmed validation command records fresh status and resets stored accepted to pending. Human Commit retains its existing restricted value route and similarly invalidates proofs by the committed input change. This avoids turning deterministic invalidation into an unconfirmed restricted-field PATCH.

Reference eligibility changes also invalidate a proof, without pretending they changed the line's immutable staging lineage. Blocker creation/resolution invalidates Case State through issue versions; it does not rewrite a line decision or validate values. A resolved blocker may restore an otherwise unchanged current acceptance. Lineage/membership mismatch remains ADR 0048 STALE/BLOCKED, not repairable by either new command.

### D5. Serialization and projection

Retain ADR 0048's Project → selected batch → ordered staging → all ordered Project lines lock order, then ordered relevant issue/proof/receipt locks where needed; never acquire Project after a child. Use the one shared authority resolver for locked mutation CAS and snapshot reads. Recheck actor, permission, reference facts and command eligibility through outer commit. No second token hash algorithm is permitted.

Propose a versioned token successor `global-case-state-v3-asset-review-line-decision-v1` at a separately authorized activation, retaining all A2 inputs and adding line input/reference/rule digests and validation/review generation identity. This proposal does not change the live v2 token. Line row-version increments also invalidate Case State on every committed new generation; no identical-verdict token reuse.

Preserve existing public action kinds and five stage results, availability → BLOCKER → STALE → unfinished → COMPLETE, full-set truth, deterministic initial-seal ordering and ASSET_REVIEW cap. Propose separate PENDING semantic keys `asset_review_line_validate_required` and `asset_review_line_review_required`; detailed currentness, warning and negative-line behavior is in companion §§4–5. The existing `asset_review_line_pending` remains historical A2 behavior until successor activation. No frontend route, automatic command invocation or downstream action is introduced.

### D6. Audit, idempotency and unknown response

Use per-command UUID IDs and tenant/Project/line/actor-bound canonical request digests for the two new commands only. One first successful validation emits one `ProjectAssetLineValidated`; one first successful human decision emits one `ProjectAssetLineReviewDecided`, plus one immutable decision and any required reversal link. Receipt, generations, status writes and audit commit atomically. This does not alter Apply's state-based re-Apply conflict or existing draft-commit replay behavior.

Exact replay returns the original historical receipt with zero writes/audits after fresh access checks; reuse with different content/actor/scope conflicts. Preconditions denied: zero writes and zero command audits. Engine/audit/transaction failure rolls back all effects; no business-invalid status or new failure audit. Unknown outer commit is reconciled by a fresh scoped receipt read before retry. A committed receipt proves that command's historical outcome, never current acceptance after a newer mutation. No receipt: refresh tokens and obtain new human confirmation before a new attempt. Ambiguous receipt/state mismatch fails closed without SQL repair.

## Rejected alternatives

- Generic draft status entries or direct status PATCH: confuse human decisions with deterministic facts and bypass the missing successor authority.
- One human-selected accepted+valid command: lets a human assert validation without rules/proof.
- Auto-validation on Apply, edit, read, AI or worker: violates the explicit official-mutation boundary; reads only assess currentness.
- Accept before validation, accept warning, or carry acceptance across a new validation generation: creates completion from outdated/unproved facts.
- Automatically clear flags/rejections on correction/revalidation, overwrite prior decisions, or use unrelated workflow approval: erases human impediments/provenance.
- Reuse mutable ValidationRule configuration or staging name/quantity verdicts as official proof: lacks the closed official-input/rule/reference authority.
- Require appraised price/identity completion, add membership operations or advance ASSET_WORKBENCH: changes accepted stage scope.

## Product Owner choices and next gate

One preferred bundle: accept D1–D6 and companion §§1–7 together, explicitly authorizing the proposed successor routing of restricted status writes while retaining ADR 0028 safeguards. Decisions requiring confirmation are: two dedicated human-confirmed commands with existing workbench permission/session; valid-before-accept; the closed v1 rule table (including blank-description warning); proof-based invalidation with negative holds; append-only supersession; UUID receipt replay; and the versioned token/two semantic-key successor.

Acceptance freezes authority only. A separate bounded runtime task must choose durable storage and implement/certify every input writer, shared resolver, command, projection and recovery before activating the successor. No runtime, migration, RBAC/API/UI or later-stage work begins in A3. Gate Owner controls Draft integration; this document records no Product Owner acceptance.

PRODUCT OWNER DECISION REQUIRED: YES
