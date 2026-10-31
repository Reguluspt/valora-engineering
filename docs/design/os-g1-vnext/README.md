# VALORA — OS-G1 vNext: UX design package (2026-10-31)

**Status:** PO decisions recorded; consolidated design and Fluent 2 audit prepared for review. **NOT implementation authorization / NOT UAT certification.**

This package records the design discussion and the Product Owner's choices for a more seamless preliminary appraisal journey. It is proposed as a **scoped successor for OS-G1 UX** after authority reconciliation. It must not be used to silently change existing runtime/API/domain contracts, reopen UAT #203, or alter OS-G2/OS-G6 gates.

## Reading order

1. [Decision register](DECISION_REGISTER.md) — approved UX choices, changes and open questions.
2. [Workflow and Workbench UX contract](WORKFLOW_AND_WORKBENCH.md) — canonical proposed operator journey, screen/field states, export and navigation.
3. [Knowledge matching and governance](KNOWLEDGE_MATCHING_AND_GOVERNANCE.md) — identity matching, confidence gates, source selection, evidence, candidate proposals and review.
4. [Authority reconciliation](AUTHORITY_RECONCILIATION.md) — mismatches with existing G1.1, Issue #222, single-user knowledge baseline, price-source authority and technical dependencies.
5. [Fluent 2 mapping and mockup v02 acceptance](FLUENT2_COMPONENT_MAPPING.md) — component adoption and visual/interaction review checklist.
6. [Fluent 2 static audit](../../audits/VALORA_FLUENT2_UIUX_STATIC_AUDIT_2026-10-31.md) — repository evidence for current uneven adoption.

## Design authority & preservation

- Existing current authority: [UI/UX v2.3 master](../VALORA_UIUX_HANDOFF_v2.3.md), [authority index](../VALORA_UIUX_V2_3_AUTHORITY_INDEX.md), [frontend architecture](../../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md), applicable current addenda and domain/ADR contracts.
- Approved post-UAT 2026-10-26 preliminary-analysis mockup is retained **unchanged** in the archived branch cited by [Issue #222](https://github.com/Reguluspt/valora-engineering/issues/222). Do not overwrite its file or mislabel the newer design as already approved.
- [v2.3 visual reference index](../visual-reference/v2.3/README.md) supplies approved Fluent 2 light grammar and S12/S13 exact baselines; S05 has visual-grammar-only status within that bundle.
- New workflow may supersede older *interaction semantics in OS-G1 only* where the PO explicitly decided so. Detailed domain contract replacements, permissions and API/storage changes require separate gates.
- Current OS-G1 vNext Workbench mockup v01 was an **offline exploratory HTML prototype**, not native Fluent UI React and not approved as a final Fluent 2 baseline. Its proposed v02 is pending.
- Dates and sample prices in this package are design-only examples, not actual appraisal conclusions, sources or observed application data.

## Frozen scope of this documentation PR

**Allowed:** new Markdown docs, review mapping, risk/AC statements, references to existing authority.

**Not allowed:** changing production React, backend, schemas, migrations, CI/CD, roadmap gates, existing approved mockup artifacts, protected test systems or live/synthetic UAT data; promoting candidate knowledge or changing final appraisal price rules.

This is a **docs-only draft** to enable PO and architecture review before a future independently authorized implementation task.
