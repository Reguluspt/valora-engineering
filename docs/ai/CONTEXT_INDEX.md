# VALORA AI Context Index

**Status:** Navigation aid only — not authority  
**Goal:** Help agents retrieve the smallest sufficient context for a task.

## 1. Minimal-context protocol

Use progressive disclosure:

```text
Layer 0 — Task Packet only
Layer 1 — exact authority refs named in Task Packet
Layer 2 — directly relevant code + tests
Layer 3 — adjacent contract/ADR/module docs only if needed
Layer 4 — historical audits/remediation only to resolve evidence/history questions
```

Never begin by ingesting the full repository or full docs tree.

## 2. Core repository controls

| Need | Read |
|---|---|
| Agent live gate / hard task rules | `CODEX.md` |
| Permanent engineering/security/mutation invariants | `ENGINEERING_GUARDRAILS.md` |
| Authority precedence / supersession | `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md` |
| Canonical implementation handoff | `docs/VALORA_PROJECT_HANDOFF.md` |
| PR scope / review / merge rules | `PR_RULES.md` |
| AI coordination operating rules | `docs/ai/AGENT_RULES.md` |
| Model/risk routing | `docs/ai/ROUTING_RULES.md` |

**Important:** status prose in these files may lag merged code. For any task whose authorization depends on current status, verify live `origin/main`, recent relevant commits, and task-specific evidence. If authority appears stale, stop/escalate rather than silently reinterpreting it.

## 3. Product/UI navigation

| Topic | Primary context |
|---|---|
| Product goal / implementation state | `docs/VALORA_PROJECT_HANDOFF.md` |
| UI/design authority relationship | `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md` |
| Vietnamese labels | `docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md`, `frontend/src/i18n/` |
| Non-IT error wording | `docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md`, `frontend/src/errors/` |
| Astryx mapping/design system | `docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md` |
| Live Workbench | `frontend/src/components/workbench/`, `frontend/src/App.tsx` |

Do not invent a new role, approval chain, KSCL workflow, or business process from UI conventions. Follow the exact task authority.

## 4. Domain/module navigation

### Project / master data / official asset-line mutation

```text
backend/app/modules/project_master_data/
backend/app/modules/project_master_data/commands/commit_asset_line_draft.py
backend/app/api/
docs/adr/0028-*
```

Use when the task touches restricted Workbench fields, official writes, project state, version checks, authorization, or atomic audit.

### Excel import / staging / Apply / Column Mapping Memory

```text
backend/app/modules/excel_import/
docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md
docs/adr/0029-*
docs/adr/0030-*
docs/remediation/2026-08-26__S13-S16__LOCAL-REMEDIATION-DESIGN.md
```

Key semantic boundary: upload/validate/staging are distinct from official Apply/promotion. Do not infer replacement Apply semantics without new authority.

### Taxonomy / Asset Identity Memory

```text
backend/app/modules/taxonomy_asset_identity/
docs/adr/0031-*
docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md
```

Use for raw asset observations, canonical/alias identity, candidate matching, identity decisions, and human-confirmed feedback.

### Knowledge / evidence / quotes

```text
backend/app/modules/knowledge_evidence/
docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md
```

Preserve evidence/knowledge activation boundaries and keep quote semantics separate from appraised-price decisions.

### Workflow / Workbench

```text
backend/app/modules/workflow_workbench/
frontend/src/components/workbench/
docs/adr/0028-*
```

Use for draft/commit behavior, review surfaces, workflow commands/outcomes, and Workbench state.

### Dossier / document extraction / row alignment

```text
backend/app/modules/document_engine_intelligence/
worker/
docs/adr/0032-*
docs/audits/2026-08-26__S15-R-002__SOURCE-BACKED-EXTRACTION-AND-ALIGNMENT.md
```

Use for DossierBundle/source roles, DOCX extraction, source-backed table candidates, alignment, historical bootstrap, and document-processing evidence.

### AI governance / provenance / execution policy

```text
backend/app/modules/ai_governance_security/
docs/adr/0033-*
docs/adr/0034-*
```

Use for AITaskRun/context/provider provenance, DecisionEpisode lineage, risk-tiered ExecutionPolicy, and any proposal for write-capable automation.

### Reliable jobs / worker runtime

```text
worker/
backend/app/modules/document_engine_intelligence/
docs/adr/0033-*
docs/adr/0034-*
```

Use for outbox/job/attempt/lease/retry/timeout/cancellation/stale-generation behavior.

### Schema / migration parity

```text
backend/alembic/
backend/app/modules/*/models.py
docs/adr/0035-alembic-schema-drift-reconciliation.md
docs/audits/2026-08-27__SCHEMA-ALEMBIC-DRIFT-RECONCILIATION.md
```

Any new schema change is risk-sensitive. Verify Alembic head, ORM parity, constraints, tenant keys, rollback/data impact, and PostgreSQL evidence.

## 5. Tests and gates

### Backend

```text
backend/tests/
cd backend && python -m ruff check app tests
cd backend && python -m pytest -q
cd backend && python tests/check_security.py
cd backend && python -m alembic heads
```

### Worker

```text
worker/tests/
cd worker && python -m ruff check worker tests
cd worker && python -m pytest -q
```

### Frontend

```text
frontend/
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm test
cd frontend && npm audit --audit-level=high
```

Use the Task Packet to narrow these. Do not run expensive/unrelated suites purely by habit if the task contract defines a smaller valid gate, but never omit a gate required by repository authority.

## 6. Evidence retrieval strategy

When determining whether something already exists:

1. search symbols/routes/model names/tests first;
2. inspect recent commits affecting the relevant paths;
3. read current implementation;
4. use historical audit prose only as supporting evidence;
5. never treat an old audit PASS as proof of current behavior without matching SHA/code.

## 7. Search-first hints

Prefer targeted searches such as:

```text
Task domain term + module path
API route + test name
model/table name + migration
ADR number + implementation symbol
error/label key + frontend path
```

Avoid vague searches like `VALORA`, `workflow`, or `AI` across the whole repository unless narrowing fails.

## 8. Context budget guideline

For a normal worker task, aim to operate with:

```text
1 Task Packet
1 compact agent rules file
1–3 exact authority sections/files
relevant implementation files
targeted tests
```

Expand only when the repository evidence proves additional context is necessary.

## 9. Conflict handling

If two sources conflict:

1. do not choose based on convenience;
2. apply the canonical authority/supersession rules;
3. distinguish live code state from authorized desired behavior;
4. record the conflict in `TASK_RESULT.md`;
5. return `BLOCKED` when the conflict changes domain/security/architecture behavior or authorization.
