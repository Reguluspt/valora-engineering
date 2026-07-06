# ADR 0006 - Fuzzy Duplicate Matching Policy

## Status

Proposed

## Context

The Sprint 1 Master Data acceptance tests require a fuzzy duplicate customer warning. The design clearly blocks exact duplicate tax code creation, but it does not specify fuzzy matching algorithms, thresholds, locale rules, or blocking behavior.

## Decision

Use a deterministic warning-only fuzzy duplicate policy for Sprint 1.

Policy:

- Exact duplicate tax code is blocking for Customer creation.
- Fuzzy duplicate name matching is warning-only in Sprint 1.
- A fuzzy warning must not prevent create/update unless another explicit validation rule fails.
- Matching must be deterministic and testable.
- Matching uses normalized display/legal name comparison:
  - trim whitespace
  - lowercase
  - collapse repeated spaces
  - remove common punctuation
  - compare simple token overlap and normalized substring similarity
- Sprint 1 returns candidate duplicate metadata sufficient for the user/API caller to review.
- No AI, external enrichment, or probabilistic service is used for duplicate detection in Sprint 1.

## Consequences

- Acceptance tests can verify a deterministic warning without inventing a business-blocking workflow.
- Exact tax code uniqueness remains the hard duplicate rule.
- Better matching can be introduced later through a design change or ADR.

## Design References

- `docs/audits/S1_PR_001_PROJECT_MASTER_DATA_DESIGN_INTAKE.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `v1.2-alpha-project-master-data-completed/12_API/05_MASTER_DATA_API.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

## Sprint 1 Scope Impact

This ADR unblocks Customer acceptance tests that expect fuzzy duplicate warnings while keeping create/update behavior within documented Master Data rules.

## What Is Explicitly Not Implemented Yet

- No duplicate matching code.
- No matching dependency.
- No AI-based duplicate detection.
- No external registry lookup.
- No blocking fuzzy duplicate workflow.

## Risks / Follow-up

- The simple deterministic policy may generate false positives or miss real duplicates.
- Vietnamese company-name normalization may need a later design-specific policy.
- If product requires blocking fuzzy duplicates, that is a design change, not a Sprint 1 implementation assumption.
