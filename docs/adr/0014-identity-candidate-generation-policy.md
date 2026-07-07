# ADR 0014 - Identity Candidate Generation Policy

## Status
Proposed

## Context
Project asset lines require identity suggestions during analysis. We must design a scoring system that records similarity scores without blocking execution.

## Decision
1. **Scoring Logic**:
   - Sprint 2 implements a deterministic similarity matching algorithm that records candidates in `identity_candidates`.
   - The score details are persisted in a `similarity_scores` table mapping component results (e.g. name, brand, model).
2. **Confidence Thresholds**:
   - High confidence (>= 0.85): eligible for automated batch approval.
   - Low confidence (< 0.65): flags human review queue entries.
3. **No External Pipelines**:
   - Matching calculation runs synchronously within API calls during development, without triggering background worker queues or external AI pipelines.

## Consequences
- Clean testing of matching algorithms.
- Clear audit trails explaining match criteria.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/12_API/07_ASSET_IDENTITY_API.md`

## Sprint 2 Scope Impact
- Controls candidate generation structures.

## What Is Explicitly Not Implemented Yet
- Production background worker queue processing or AI model inference.

## Risks / Follow-up
- Tune token comparison functions to minimize matching latency on large datasets.
