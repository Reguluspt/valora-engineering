# ADR 0019 - Quote Price Conflict Formulas

## Status
Proposed

## Context
Quote price conflicts can halt approval pipelines. The original design lacked a deterministic formula for detecting quote conflicts, creating ambiguity about how deviations and spreads are verified mathematically.

## Decision
1. **Inputs**: Active `QuoteLine` records in the same `QuoteBatch` sharing the same currency and normalized unit. A minimum of 2 active lines is required.
2. **Formula A (Min/Max Spread)**:
   \[spread\_percent = \frac{max(prices) - min(prices)}{min(prices)} \times 100\]
   - If `min(prices) == 0`, a manual review conflict is raised immediately since division by zero is undefined.
3. **Formula B (Median Deviation)**:
   - Identify `median(prices)`.
   - Calculate maximum median deviation:
     \[max\_median\_deviation\_percent = max\left(\frac{|price - median\_price|}{median\_price}\right) \times 100\]
4. **Thresholds & Flags**:
   - **Conflict threshold**: \(\ge 20\%\). Creates a warning `KnowledgeConflict`.
   - **Blocking threshold**: \(\ge 35\%\). Creates a blocking conflict.
5. **Approval Restriction**:
   - A blocking conflict prevents QuoteBatch approval unless the reviewer supplies a valid `override_blocking_conflict_reason`.

## Consequences
- Deterministic verification of quote pricing without relying on heuristic AI guesses.
- Clear audit trails showing calculated percentages in conflict logs.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/19_AUDIT_PATCH_AI_QUEUE_AND_CONFLICT_POLICY.md`

## Sprint 3 Scope Impact
- Controls validators for `QuoteBatch` creation/update schemas and conflict trigger routines.

## What Is Explicitly Not Implemented Yet
- Automatic currency exchange rates conversion or unit normalization converters (assumed normalized prior to ingestion).

## Risks / Follow-up
- Currency fluctuations can trigger false conflicts if lines use different source currencies. Normalization must happen before formula evaluation.
