# Engineering Guardrails

## Source of truth

Valora Design Book v1.2-final is the source of truth.

## Guardrails

- Do not implement domain behavior that is not in the Design Book.
- Do not allow AI to approve official data.
- Do not write official data without command/audit path.
- Do not bypass tenant boundary.
- Do not treat Word/Excel as source of truth.
- Do not overwrite immutable evidence or generated official documents.
- Do not make ReviewDecision mutable.
- Do not implement business feature in Sprint 0.

## Ambiguity handling

When implementation ambiguity appears:

```text
1. Check v1.2-final package.
2. Check relevant completed slice.
3. Check RC consolidation.
4. If still unclear, write ADR or Design Change Request.
```
