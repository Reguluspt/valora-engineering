# ADR 0023 - AI Knowledge Queue Auto-Reject Policy

## Status
Proposed

## Context
AI-extracted specs and quotes serve as suggestions but must not pollute standard reviewer queues. We need to formalize automated rejection boundaries and verify that AI suggestions never approve catalog standards silently.

## Decision
1. **Suggestion Status**:
   - AI suggestions are imported as candidate proposals. They never write to official knowledge tables directly without explicit human approval.
2. **Auto-Rejection Flow**:
   - The command `AutoRejectLowConfidenceKnowledgeCandidates` scans queue candidates.
   - Any AI/system candidate with `confidence_score < 0.50` is transitioned to `status = rejected`, `auto_rejected = true`, and `auto_reject_reason = auto_rejected_low_confidence`.
   - The system user ID is logged as `reviewed_by`.
3. **Manual Exceptions**:
   - Candidates created or pinned manually by users are protected from automatic rejection, even if their confidence score is below 0.50.
4. **Queue Filter**:
   - Default queue list views filter out auto-rejected items. They are returned only if `include_auto_rejected = true` is supplied.
5. **No AI Provider Calls in Persistence**:
   - No external AI API calls, vector database lookups, or worker processes will be implemented during persistence tasks. Checks run purely as metadata rules.

## Consequences
- Keeps the curator work queue clean.
- Auditable trail of auto-rejected items.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/19_AUDIT_PATCH_AI_QUEUE_AND_CONFLICT_POLICY.md`

## Sprint 3 Scope Impact
- Dictates filtering rules for queue queries and fields on `KnowledgeQueueItem`.

## What Is Explicitly Not Implemented Yet
- AI model provider configurations.

## Risks / Follow-up
- Auto-rejection run schedules must be coordinated to prevent locking conflicts on queue items.
