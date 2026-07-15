# ADR 0031 â€” Contextual Asset Identity Memory and Human-Confirmed Feedback

## Status

Accepted â€” owner-requested design authority, 2026-07-14. Runtime implementation requires S13-PR-001 design audit/merge, then assigned Sprint 14 task IDs and audit. No runtime is authorized by this ADR alone.

## Context

Valora already has CanonicalAsset, AssetVariant, AssetAlias, IdentityCandidate, SimilarityScore and review concepts. It does not yet preserve a first-class raw observation independent of an official project line, distinguish customer-specific aliases from curated aliases, or define a safe learning-feedback contract.

Historical paired dossiers show that customer text may combine local wording, asset name and technical attributes. The standardized report text must be linked to, not overwrite, that source wording.

## Decision

### 1. Create an immutable Raw Asset Observation boundary

`RawAssetObservation` links source artifact/sheet/table/row/cell, raw wording, raw unit/quantity, section context and mapping-profile version. It can exist before an official ProjectAssetLine and can represent historical dossier rows.

Raw text is immutable. Normalized/search representations are separate or derived.

### 2. Reuse canonical identity models

CanonicalAsset, AssetVariant, curated AssetAlias, taxonomy, candidate/review and duplicate/merge boundaries remain the authoritative identity domain. Asset Identity Memory is not a second canonical catalog.

### 3. Add contextual alias semantics

Customer- or organization-specific wording is represented as `ContextualAssetAlias` candidate/active memory. It is scoped by organization and optionally customer and points to a canonical asset/variant with source-decision lineage.

A contextual alias does not automatically become a global curated AssetAlias. Promotion requires curator authority.

### 4. Use layered deterministic retrieval before AI

Candidate retrieval priority:

```text
same-customer contextual alias
â†’ organization contextual alias
â†’ curated AssetAlias
â†’ canonical/variant names and codes
â†’ deterministic fuzzy/attribute retrieval
â†’ approved AI reranking
```

Score components and explanations are versioned. Price is not a primary identity feature.

### 5. Human review always controls official identity

High confidence may preselect a candidate or support an explicit batch-review screen. It never auto-approves an identity, creates active canonical knowledge or mutates official identity fields without an authorized human command.

This rule supersedes ADR 0014 wording that made high-confidence candidates eligible for automated batch approval.

### 6. Define append-only feedback

Positive learning evidence is created only by a committed human decision:

- accepted candidate;
- corrected-and-accepted candidate;
- approved contextual alias;
- approved create-new canonical/variant decision.

Negative evidence includes explicitly rejected candidates and conflict decisions with reason.

Not learning evidence:

- temporary UI selections;
- unreviewed/failed candidates;
- auto-rejected candidates without human review;
- rolled-back commands.

Feedback may update a retrieval index, but rule/model weights change only through offline evaluation and versioned release. Online per-click model training is forbidden.

### 7. Preserve provenance through merges and supersession

Contextual aliases and identity decisions remain traceable when a canonical asset/variant is merged, deprecated or superseded. Historical decisions are not rewritten.

## Conceptual records

```text
RawAssetObservation
ContextualAssetAlias
AssetIdentityCandidate (observation-backed)
SimilarityScore / explanation
AssetIdentityReviewItem
AssetIdentityDecision
LearningFeedbackEvent
AssetMatchIndex (derived/rebuildable)
```

Existing model names may be extended rather than duplicated, but the semantics above are mandatory.

## Commands/events

```text
GenerateAssetIdentityCandidates
ConfirmAssetIdentityDecision
RejectAssetIdentityCandidate
CreateContextualAliasCandidate
PromoteContextualAlias
```

Every decision is tenant-scoped and append-only, with actor, time, reason, source observation and scoring/rule/model version.

## Consequences

### Positive

- Learns real customer wording without polluting the global catalog.
- Enables Excel-only matching from reviewed historical dossiers.
- Keeps raw and standardized data side by side.
- Produces an auditable training/evaluation dataset.

### Cost

- Requires migration away from candidate-only linkage to ProjectAssetLine or a compatible observation-backed association.
- Requires new review UX and index/retrieval services.
- Requires conflict policy for the same raw alias mapping differently in different contexts.

## Acceptance gates

- Raw observation remains unchanged after normalization/identity correction.
- Customer A memory is not automatically exposed to customer B or another organization.
- Candidate scores include explainable components.
- High confidence never writes official identity without confirmation.
- Accepted/corrected/rejected decisions generate the correct append-only feedback.
- Rolled-back/unreviewed/auto-rejected candidates do not become positive learning examples.
- A new Excel-only dossier retrieves reviewed historical matches with measurable recall@k.
