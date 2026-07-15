# ADR 0030 — Versioned Column Mapping Memory and Adaptive Workbook Intake

## Status

Accepted — owner-requested design authority, 2026-07-14.
**S13-PR-001 note:** Runtime implementation requires S13-PR-001 independent design audit + owner merge, then assigned Sprint 13 task IDs (starting candidate S13-PR-002). No runtime is authorized by this ADR alone.

## Context

S12 v1 securely parses `.xlsx`, preserves positional raw cells and maps known columns through deterministic aliases. The anonymized PD-001 acceptance fixture demonstrates that production input may be `.xls`, may contain title rows before the header, may use unfamiliar headers and may contain a meaningful blank-header evidence column. Section and total rows also cannot be treated as asset lines.

The mapping decision must be reviewable and reusable by organization/customer/template without permitting AI to auto-import or auto-apply official data.

## Decision

### 1. Separate structure/mapping from asset identity

Column Mapping Memory owns workbook/table structure and semantic column/row roles only. It outputs confirmed mappings and raw asset observations; it does not resolve CanonicalAsset or pricing decisions.

### 2. Use a format-adapter boundary

Adaptive Intake v2 shall support `.xlsx` and `.xls` through bounded, value-only workbook adapters that expose neutral sheet/cell/merged-region metadata.

All adapters must:

- preserve source file/checksum;
- enforce file/row/column/cell limits;
- never execute formula, macro, VBA or external-link content;
- fail closed on encrypted/malformed input;
- preserve blank/duplicate headers by column position.

The exact legacy `.xls` dependency requires a dependency/security spike. Office desktop automation is not the domain parser.

### 3. Replace first-non-empty-row header discovery in v2

The analyzer produces ranked sheet/table/header candidates using structural density, header vocabulary, subsequent-row consistency, types/patterns, merged title regions and prior profiles. A user confirms the proposed region when ambiguity exists.

### 4. Introduce a semantic role registry

Minimum roles:

```text
row_number, raw_asset_name, raw_description, unit, quantity,
customer_unit_price, customer_amount, reference_value,
appraiser_proposed_price, evidence_note, ignore
```

Roles are position-independent. Blank-header columns remain eligible.

### 5. Classify rows before materializing staging

Minimum row classes:

```text
asset, section, subtotal, total, note, empty, unresolved
```

Only confirmed asset rows become asset staging rows.

### 6. Persist versioned memory

Introduce the conceptual records:

- `ImportSourceArtifact`;
- `WorkbookStructureSnapshot`;
- `ColumnMappingProfile`;
- `ColumnMappingField`;
- `ColumnMappingDecision`;
- `ColumnMappingProfileUsage`.

Each import stores the exact profile version and mapping snapshot used. Correcting a profile creates a new version; prior imports are never remapped silently.

### 7. Scope memory safely

Retrieval priority:

```text
organization + customer + same template
→ organization + customer + similar template
→ approved organization template
→ new deterministic/AI proposal
```

No automatic cross-organization learning.

### 8. Require human confirmation

Rule/AI results are candidates. An authenticated user accepts, corrects or rejects mapping before staging materialization. Active profiles may prefill future imports but do not bypass confirmation, validation or Apply.

### 9. Keep S12 Apply v1 frozen

This ADR changes the future discovery/mapping path only. It does not add fields to `s12-pr-004-v1` Apply or authorize AI Apply.

## Commands/events

Conceptual commands:

```text
AnalyzeWorkbookStructure
ProposeColumnMapping
ConfirmColumnMapping
MaterializeConfirmedMappingToStaging
```

Conceptual events/decisions:

```text
WorkbookStructureAnalyzed
ColumnMappingProposed
ColumnMappingConfirmed
ColumnMappingRejected
ConfirmedMappingMaterialized
```

Audit payloads contain identifiers, versions and counts, not unrestricted raw cell contents.

## Consequences

### Positive

- Supports variable customer templates and legacy `.xls`.
- Prevents title/section/total rows from silently becoming assets.
- Makes mapping reproducible and reusable.
- Preserves raw evidence and human accountability.

### Cost

- Requires source-artifact retention and new batch lifecycle states.
- Requires migration, API, UX and adapter security work.
- S12 parser tests remain historical and need a distinct v2 acceptance suite.

## Supersession/compatibility

- S12 fixed alias mapping remains the implemented v1 behavior until v2 tasks land.
- `VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md` §§6/12 remain historical S12-v1 descriptions.
- This ADR and Design Book v1.4 govern new adaptive-intake implementation.

## Acceptance gates

- `.xls` and `.xlsx` adapters pass safety/limit tests.
- PD-001 sheet/header/column/row semantics pass the v1.4 fixture criteria.
- Mapping profile correction creates a new version.
- Reimport retrieves the correct customer/template profile.
- Cross-tenant profile access fails closed.
- No mapping proposal can materialize staging or Apply without explicit authorized commands.
