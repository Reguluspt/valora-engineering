# ADR 0022 - Quote Batch, Quote Line, and Appraised Price Boundary

## Status
Proposed

## Context
Raw supplier pricing and professional catalog pricing standards must remain logically distinct. We need to formalize the boundary between `QuoteBatch` aggregation and the finalized `AppraisedPriceDecision` records.

## Decision
1. **Model Separability**:
   - `MarketQuote` (QuoteBatch / QuoteLine) represents raw pricing data collected from vendor proposals or internet catalogues.
   - `AppraisedPriceDecision` represents the final catalog pricing standard determined by a professional appraiser. It links to a `QuoteBatch` and contains a written justification reason and a final unit price.
2. **Revision Rules**:
   - Approved `QuoteBatch` records are immutable.
   - Modifying vendor quote line values creates a new `QuoteBatch` revision, linking to the original via `previous_quote_batch_id` and incrementing `revision_number`.
3. **Overwrite Prevention**:
   - Approved `AppraisedPriceDecision` records are immutable.
   - Modifying a quote batch does NOT automatically update or overwrite existing appraised price decisions. Pricing standards can only be superseded by creating a new decision record.
4. **Lineage Reuse**:
   - Reusing a pricing standard in a new project requires linking the full support set (supplier quotes, appraisal reasoning, and document lineage path), not just copying the final price value.

## Consequences
- Maintains a strict logical separation between market quotes and appraisal standards.
- Prevents database state drift from altering historical appraisal rationales.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/20_AUDIT_PATCH_VERSIONING_MODEL_CLARIFICATION.md`

## Sprint 3 Scope Impact
- Controls schema structures of `quote_batches`, `quote_lines`, and `appraised_price_decisions` tables.

## What Is Explicitly Not Implemented Yet
- Auto-superseding state machines that link old appraised decisions to new ones automatically.

## Risks / Follow-up
- Ensure database cascade rules prevent delete mutations of quote lines backing active decisions.
