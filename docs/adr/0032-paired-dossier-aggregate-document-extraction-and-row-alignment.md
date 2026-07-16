# ADR 0032 — Paired Dossier Aggregate, Document Extraction and Row Alignment

## Status

Accepted — owner-requested design authority, 2026-07-14. Runtime implementation requires Gate 0c closure, then assigned Sprint 15 task IDs and audit. No runtime or autonomous bootstrap is authorized by this ADR alone.

## Context

Historical valuation knowledge is encoded across a customer Excel list and a final Word/PDF report. Treating those files independently loses the supervised relationship between customer raw wording, appraiser normalization, technical specifications, supplier quotes and final appraisal decisions.

The current document-intelligence persistence/API foundation does not provide an end-to-end DOCX extraction runtime, table-role model or source-backed alignment across Excel, technical, quote-comparison and result tables.

## Decision

### 1. Introduce a DossierBundle aggregate

Historical files are grouped by organization/customer/dossier as a `DossierBundle`. The bundle is separate from an active Project workflow, but it may link to an existing Project when a valid relationship exists.

This avoids manufacturing active projects solely to satisfy lineage.

### 2. Assign explicit source roles

Minimum roles:

```text
customer_asset_list
final_appraisal_report
comparison_table
supplier_quote
catalogue
approval_or_qc
other_evidence
```

Each source file is immutable, checksummed and access-controlled.

### 3. Implement a real extraction runtime

Document Intelligence shall classify, parse DOCX/PDF layout and tables, OCR only when necessary, validate extraction schemas and keep page/table/row/cell locators.

Deterministic DOCX table extraction is the baseline. AI extraction may supplement it but never becomes the only path or official mutation authority.

### 4. Assign table roles

Minimum table roles:

```text
excel_customer_asset_table
word_technical_asset_table
word_quote_comparison_table
word_final_result_table
```

### 5. Align rows explicitly

`DossierRowAlignment` links raw Excel rows to candidate rows in technical, comparison and final-result tables. Alignment uses STT, section, order, name, unit, quantity and technical attributes. Row order alone is never production authority.

Alignment states are candidate, review_required, confirmed, rejected and unresolved. Human confirmation is required before bootstrap knowledge promotion.

### 6. Keep pricing semantics separate

- Customer/working price is a raw observation.
- Appraiser-added H-like price is a proposal observation.
- Each supplier amount is an individual QuoteLine candidate with time/source.
- Final report price is an AppraisedPriceDecision candidate with rationale/evidence.
- Evidence-note text is preserved raw before typed resolution.
- Unit and rounding transformations are explicit lineage events/fields, not silent raw edits.

### 7. Bootstrap candidates, not active knowledge

Extraction/alignment may create identity, contextual alias, technical-specification, quote, appraised-decision and KnowledgeVersion candidates. Existing human review/approval commands control activation.

Direct bulk SQL insertion into active knowledge is forbidden.

## Conceptual records

```text
DossierBundle
DossierSourceFile
ParsedDocument / ExtractedTable / ExtractedTableRow
DossierTableRole
DossierRowAlignment
PriceProposalObservation
EvidenceNoteObservation
BootstrapBatch / BootstrapCandidateLink
```

The implementation may reuse existing EvidenceFile, ParsedDocument, ExtractedField, QuoteBatch/Line, AppraisedPriceDecision and KnowledgeVersion structures where semantics match.

## Commands/events

```text
CreateDossierBundle
AttachDossierSource
ExtractDossierDocument
AssignDossierTableRole
GenerateDossierRowAlignments
ConfirmDossierRowAlignment
BuildBootstrapCandidates
PromoteReviewedBootstrapCandidates
```

No extraction/alignment command mutates active project or knowledge data directly.

## Consequences

### Positive

- Preserves the exact raw-to-standardized training pair.
- Recovers supplier/time/evidence context rather than only final price.
- Supports historical bootstrap without misusing active Projects.
- Gives Word extraction and row alignment an auditable boundary.

### Cost

- Requires new aggregate persistence and orchestration across Excel, Document Intelligence, Identity and Knowledge contexts.
- Requires table/row source locators and review UX.
- Requires explicit handling of missing, split, merged and reordered rows.

## Automation-readiness compatibility

- Long-running extraction/alignment tasks follow ADR 0033 task/context/attempt provenance and ADR 0034 durable idempotent job semantics.
- Confirmed/rejected alignment outcomes link to Decision Episodes without replacing the authoritative `DossierRowAlignment` decision state.
- Extraction and alignment remain R0/R1 proposal work in S15–S16. No R2 bootstrap promotion is authorized without a later task-specific evaluated release.
- Database/object-storage partial failures and stale generations must be recoverable and must preserve prior reviewed extraction.

## Acceptance gates

- PD-001 bundle holds both source files and immutable checksums.
- Runtime extracts 49 technical rows, 147 supplier quote observations and 49 final-result rows.
- 49 sample alignments are reviewable, with unit and rounding conflicts flagged.
- Raw Excel wording and report-standardized wording remain separate and linked.
- Evidence notes with blank headers remain retrievable.
- Bootstrap reruns are idempotent and do not duplicate active knowledge.
- Candidate activation requires domain-appropriate human review and full lineage.
