# Module Ownership Map

**Reconciled:** 2026-07-16 (Gate 0c design extension) — adds future Adaptive Intake / Memory / bounded-AI ownership without creating duplicate bounded contexts.

## Backend modules

| Module | Slice source | Sprint (historical) | Future ownership (design; not yet runtime) |
|---|---|---|---|
| project_master_data | v1.2-alpha-completed | Sprint 1 | Org/project hub (unchanged) |
| taxonomy_asset_identity | v1.2-beta-completed | Sprint 2 | Raw Asset Observation integration, contextual aliases, identity candidates/decisions (ADR 0031) |
| knowledge_evidence | v1.2-gamma-completed | Sprint 3 | Reviewed quote/spec/knowledge candidates and activation after human promotion |
| workflow_workbench | v1.2-delta-completed | Sprint 4 | Workflow/session; future pattern candidates derive from domain commands/outcomes, never UI clickstream |
| document_engine_intelligence | v1.2-epsilon-completed | Sprint 5 | Dossier source roles, DOCX/PDF extraction, table roles, row alignment (ADR 0032) |
| ai_governance_security | v1.2-zeta-completed | Sprint 6 | Task/context/attempt provenance, provider gateway and deterministic ExecutionPolicy boundary (ADR 0033–0034 / S16) |
| excel_import | S12 contracts | Sprint 12 | Adaptive Intake, workbook adapters, Column Mapping Memory (ADR 0030) |

Cross-module calls use application services / contracts. Direct active-knowledge injection is forbidden. No second asset catalog alongside CanonicalAsset/Variant.

Worker/runtime infrastructure owns durable outbox/job/attempt execution, lease/retry/timeout/cancellation and stale-generation rejection. It does not own domain policy or official mutation semantics.

## Frontend modules

| Area | Slice source | Sprint | Future ownership (design) |
|---|---|---|---|
| app_shell | Sprint 0 | Sprint 0 | Unchanged |
| project_pages | v1.2-alpha-completed | Sprint 1 | Unchanged |
| taxonomy_pages | v1.2-beta-completed | Sprint 2 | Identity review surfaces (Vietnamese Astryx) |
| evidence_knowledge_pages | v1.2-gamma-completed | Sprint 3 | Candidate knowledge review |
| workbench | v1.2-delta-completed | Sprint 4 | Mapping-confirmation and intake review UX |
| document_pages | v1.2-epsilon-completed | Sprint 5 | Dossier alignment review |
| security_ai_admin | v1.2-zeta-completed | Sprint 6 | AI task/capability monitoring, policy reason and kill-switch administration; no provider-specific ordinary-user UX |
