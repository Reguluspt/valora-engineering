> **HISTORICAL DOCUMENT NOTICE — 2026-09-21**  
> Tài liệu này được giữ để bảo toàn lịch sử/evidence. Nó **không phải current authority hoặc roadmap**. Khi có mâu thuẫn, dùng `docs/DOCUMENTATION_STATUS_INDEX.md`, `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`, canonical UI/UX v2.3 authority và ADR hiện hành.

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
