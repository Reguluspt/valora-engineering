# ADR 0014 - Identity Candidate Generation Policy

## Status
Accepted for Sprint 2 candidate generation mechanics.
**Supersession (2026-07-15 / S13-PR-001):** any wording that permits **high-confidence automated batch approval** of identity is superseded by **ADR 0031** and Design Book v1.4. Official asset identity remains **human-confirmed**. Deterministic candidate-generation rationale and score persistence remain useful and are not discarded.

## Context
Project asset lines require identity suggestions during analysis. We must design a scoring system that records similarity scores without blocking execution.

## Decision
1. **Scoring Logic**:
   - Sprint 2 implements a deterministic similarity matching algorithm that records candidates in `identity_candidates`.
   - The score details are persisted in a `similarity_scores` table mapping component results (e.g. name, brand, model).
2. **Confidence Thresholds** (historical Sprint 2 wording — **superseded for approval automation**):
   - High confidence (>= 0.85): may rank candidates for human review; **not** automatic official identity approval (see ADR 0031).
   - Low confidence (< 0.65): flags human review queue entries.
3. **No External Pipelines**:
   - Matching calculation runs synchronously within API calls during development, without triggering background worker queues or external AI pipelines.
4. **Human confirmation (ADR 0031):**
   - No automated batch approval of official identity.
   - AI may only propose or rerank; it cannot confirm identity.

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
