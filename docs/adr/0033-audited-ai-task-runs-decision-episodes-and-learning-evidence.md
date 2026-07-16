# ADR 0033 — Audited AI Task Runs, Decision Episodes and Learning Evidence

## Status

Accepted — owner-requested design authority, 2026-07-16.

This ADR defines an implementation contract for future tasks. It does not by itself authorize an AI provider call, an autonomous command, a database migration or a change to any existing human approval gate.

## Context

Valora already has domain-specific decisions, append-only `AuditEvent` records and a generic `UserActionLog`. Design Book v1.4 and ADR 0030–0032 also define Column Mapping Memory, Asset Identity Memory and human-confirmed learning feedback.

Those foundations do not yet provide a durable, provider-independent answer to the following questions:

- What exact task did AI, a deterministic rule or a user perform?
- What authorized context and source evidence were supplied?
- Which adapter, retriever, rule, prompt, schema, provider and model versions participated?
- What proposal was produced?
- What did the user accept, correct, reject or defer?
- Which committed domain decision became reusable learning evidence?
- Can a future evaluation reproduce the same input manifest without copying sensitive source content into a general audit log?

Creating unrelated generic “Workflow Memory” and “Decision Memory” tables would duplicate domain truth and encourage accidental learning from UI clicks, temporary selections or professional judgement that must remain human-controlled.

Valora therefore needs one cross-cutting provenance contract while preserving domain-specific records as authority.

## Decision

### 1. Keep domain records authoritative

`ColumnMappingDecision`, `AssetIdentityDecision`, dossier alignment decisions, knowledge review decisions, price decisions and workflow transitions remain the authoritative business records for their domains.

The records introduced by this ADR reference those decisions. They do not replace, flatten or silently rewrite them.

Official project data, active knowledge and final valuation decisions remain outside AI memory.

### 2. Introduce a logical AI task run envelope

`AITaskRun` represents one logical execution of a registered AI-assisted task. A run may use a deterministic/mock implementation, an external provider or a future approved local model.

Conceptual fields include:

```text
id
organization_id
task_type
task_contract_version
subject_type / subject_id
status
initiator_kind                human | system | ai_service
initiator_user_id             nullable when not human
correlation_id
idempotency_key
context_manifest_id
input_schema_version
output_schema_version
prompt_version                nullable for deterministic tasks
rule_version                  nullable
adapter_version               nullable
retriever_version             nullable
requested_at / completed_at
terminal_outcome
```

`AITaskRun` is not a general conversation transcript. It records a bounded registered task.

### 3. Preserve provider attempts separately

Retries and provider fallbacks must not overwrite prior attempts. `AITaskAttempt` is append-only and conceptually records:

```text
ai_task_run_id
attempt_number
provider
model
model_release_or_alias
request_hash
response_artifact_ref / response_hash
started_at / finished_at
latency_ms
input_tokens / output_tokens
cost_amount / cost_currency
status
error_class / error_code
fallback_reason
```

Provider/model names are backend provenance and must remain hidden from ordinary client-facing UX, which uses “Trợ lý Valora”.

### 4. Use an authorized context manifest

`AIContextManifest` records the exact authorized references and transformations used to assemble task context:

```text
organization_id
task_type / contract_version
source artifact and observation references
retrieved profile/alias/decision references and versions
redaction policy version
data classification summary
content hashes and bounded counts
created_at
```

The manifest contains references, hashes, versions and bounded summaries. Unrestricted raw workbook cells, full documents, secrets or personal data are not copied into general audit payloads.

The underlying source remains in its access-controlled source/evidence store.

### 5. Introduce a Decision Episode envelope

`DecisionEpisode` links a proposal to the committed business outcome. It is append-only and conceptually records:

```text
organization_id
episode_type
subject_type / subject_id
source_decision_type / source_decision_id
proposal_source_kind          human | deterministic_rule | ai_task
ai_task_run_id                nullable
proposal_ref / proposal_hash
before_ref / before_hash
after_ref / after_hash
outcome                       accepted | corrected | rejected | deferred | reversed
reason_code / reason_text
decided_by_user_id
decided_at
policy_version                nullable while all actions require human review
```

Large or sensitive before/after payloads remain in access-controlled domain records or artifacts. The episode stores safe field-level summaries or references.

A reversal creates a new episode linked to the original. Historical episodes are never edited into the new truth.

### 6. Learning evidence comes only from committed decisions

`LearningFeedbackEvent` may be emitted only from a committed, authorized domain decision and its Decision Episode.

Eligible positive evidence includes:

- an accepted or corrected-and-accepted mapping decision;
- an accepted or corrected identity decision;
- an approved contextual alias;
- a confirmed dossier row alignment;
- another explicitly registered, human-confirmed learning outcome.

Eligible negative evidence includes an explicit human rejection or conflict decision with reason.

The following are not learning evidence:

- temporary UI selections;
- autosave/draft edits without a committed decision;
- parser or model output that was not reviewed;
- system auto-rejection without human review;
- failed, timed-out or superseded task runs;
- rolled-back actions treated as positive examples;
- repeated clicks or navigation events.

Feedback may update a derived retrieval projection immediately. Model/rule weights change only through offline evaluation and a versioned release. Per-click online training remains forbidden.

### 7. Workflow patterns are derived from domain intent

A future `WorkflowPattern` is a versioned candidate derived from domain commands, task outcomes and Decision Episodes.

It must not learn raw UI click sequences, screen coordinates, component identifiers or incidental navigation order. UI implementation details are not stable business intent.

Workflow patterns may describe clerical/process behavior such as:

- which validated task normally follows another task;
- which customer/template requires an additional review step;
- which low-risk draft preparation is commonly accepted.

Workflow patterns must not encode a preferred final price, signature decision, QC approval or another professional judgement that remains human authority.

### 8. Scope memory explicitly

Reusable evidence must distinguish:

```text
organization policy
customer/template memory
project/dossier context
user preference
```

User preference may personalize workflow or presentation but cannot silently become organization policy or active valuation knowledge.

No cross-organization learning is allowed without a separate owner-approved, privacy-reviewed and opt-in contract.

### 9. Preserve time semantics

Where the domain requires it, records distinguish:

```text
observed_at    when a fact or quote was observed
effective_at   when it applied to the business context
recorded_at    when Valora persisted it
```

Ingestion time alone must not be treated as the valuation or market-observation time.

### 10. Derived retrieval indexes remain rebuildable

SQL search indexes, full-text projections, embeddings and vector indexes are derived projections. They are never the sole source of lineage or approved knowledge.

Every index release records its source dataset/version, normalization version and embedding/retriever version. Rebuilding an index does not mutate historical decisions.

### 11. Evaluation must avoid leakage

Evaluation corpora must separate training/development from evaluation by dossier and, where useful, customer and time window. Near-duplicate rows from one dossier must not appear on both sides of an accuracy claim.

Task metrics include correction rate, false high-confidence rate, source-locator completeness, latency, cost and user review time. Model self-reported confidence is not production authority.

## Conceptual records

```text
AITaskRun
AITaskAttempt
AIContextManifest
DecisionEpisode
LearningFeedbackEvent
WorkflowPatternCandidate        derived / future
RetrievalIndexRelease           derived / rebuildable
```

Existing models may be extended rather than duplicated, but the semantics above are mandatory.

## Commands and events

Conceptual commands/events include:

```text
RegisterAITaskRun
RecordAITaskAttempt
CompleteAITaskRun
RecordDecisionEpisode
RecordDecisionReversalEpisode
PublishLearningFeedbackFromCommittedDecision

AITaskRunRegistered
AITaskAttemptCompleted
AITaskRunCompleted
DecisionEpisodeRecorded
LearningFeedbackPublished
```

Application commands derive tenant and actor server-side. Client payloads cannot assert a different organization, human actor or provider outcome.

## Consequences

### Positive

- Provider/model changes do not erase accumulated knowledge.
- Mapping, identity and workflow learning share provenance without sharing domain ownership.
- Human corrections become a trustworthy evaluation and retrieval dataset.
- Sensitive source content stays out of general audit payloads.
- Future workflow-pattern discovery survives UI redesigns.

### Cost

- Requires new persistence, retention and access-control design.
- Requires task, prompt, schema, rule, adapter and retriever version discipline.
- Requires explicit links from domain decisions rather than generic JSON-only logging.

## Compatibility and supersession

- This ADR extends ADR 0030–0032; it does not weaken their human-confirmation rules.
- `AuditEvent` remains the security/mutation audit trail. `AITaskRun` and `DecisionEpisode` provide bounded task and learning provenance, not a replacement for atomic audit.
- `UserActionLog` remains a UI/workbench timeline and is not a learning dataset by itself.
- Existing historical records are not backfilled with invented AI, proposal or reason metadata. Unknown legacy provenance remains explicit.

## Acceptance gates

- Every registered AI task can be traced to an authorized context manifest and exact task/schema versions.
- Retry/fallback attempts remain distinct and append-only.
- A domain decision can be traced from source observation through proposal, human correction and final outcome.
- Rolled-back, temporary, failed and unreviewed artifacts cannot become positive learning evidence.
- Cross-tenant context, episodes and feedback fail closed.
- Raw sensitive content is absent from general audit payloads.
- Workflow-pattern inputs are domain commands/decisions, not UI clickstream.
- Retrieval indexes can be rebuilt without losing source lineage.

## Non-goals

- No autonomous execution is authorized by this ADR.
- No generic agent loop is introduced.
- No fine-tuning or online weight update is implemented.
- No final valuation preference is learned.
- No requirement to adopt a separate vector database is created.
