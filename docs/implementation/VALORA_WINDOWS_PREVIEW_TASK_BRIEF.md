# VALORA — Windows Preview Task Brief

**Task:** `VALORA-WIN-PREVIEW-001`
**Status:** ROADMAP ONLY — RUNTIME BLOCKED UNTIL SOFTWARE COMPLETION
**Date:** 2026-09-12
**Roadmap baseline:** `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`
**Runtime baseline:** not assigned until the Software Completion gate passes

## Objective

Package the complete Valora product for acceptance on the Product Owner's Windows machine before
cloud staging. Windows Preview must not be used to discover, design or fill missing product runtime.

## Roadmap position

```text
PR-00 through PR-06 merged
→ Unified Appraisal OS roadmap OS-G0 through OS-G6
→ Pre-case + Appraisal Core product closure
→ Document Runtime + Release/Publishing
→ traceability/state/fidelity + North-star exact-SHA E2E
→ Software Completion acceptance on an exact merged SHA
→ Windows Preview
→ production architecture decision
→ cloud staging
→ production hardening and pilot
```

SharePoint and OneDrive for Business remain deferred.

## Software Completion entry gate

Windows Preview implementation may begin only when:

1. Unified Roadmap OS-G0 through OS-G6 required product/acceptance gaps are closed; the historical PR-00–PR-13 matrix may be used as evidence but is not the sequencing gate.
2. Login, session restoration, logout, account/organization context and real project selection work
   through the product UI.
3. Document Workspace and Working-change review follow current ADR 0045 authority; provider observation may be automatic but authoritative document mutation remains human-confirmed.
4. Every production-scope screen uses real APIs or a truthful unavailable state; no placeholder or
   demonstration data stands in for product behavior.
5. Backend/frontend tests, lint, build, migration, tenant, security and exact-SHA integration gates
   pass.
6. OS-G6 proves the supported North-star journey end to end on the exact candidate SHA, including required failure/retry/tenant/immutability and visual-authority checks.

## Deferred implementation boundary

After the entry gate, a separate accepted contract may authorize only isolated Windows/Docker
Desktop packaging, bounded PowerShell lifecycle commands, migration/health checks, local secret
handling, durable trial data, backup/restore and exact-image-revision verification. It may not add
business features or weaken session, CSRF, tenant, RBAC, audit or M365 safety controls.

## Non-goals

- no launcher, Compose override, bootstrap runtime or packaging implementation before Software
  Completion;
- no production/cloud deployment, public ingress, DNS, publication or release;
- no production credentials or production data;
- no new product semantics, SharePoint/OneDrive Business expansion, unauthorized Graph mutation, silent overwrite or authority change during Windows packaging;
- no MSI, Windows service or auto-update channel in the first preview;
- no interference with containers, ports or processes outside the future isolated preview project.

## Acceptance boundary

The eventual preview must start through one documented PowerShell command, isolate its resources,
reach the single Alembic head before readiness, preserve trial data across restart, prove
backup/restore, keep secrets out of logs/evidence and pass desktop/laptop UAT against the exact
candidate SHA. Detailed runtime acceptance must be revalidated against the future candidate and
host environment; historical environment-survey observations are not evergreen authorization.

## Provider plan

Codex remains the sole writer and orchestrator. Gemini `gemini-3.1-pro-high` is the required
architecture/security challenge when available. DeepSeek `opencode-go/deepseek-v4.1-flash` performs
the independent repository/diff review. Claude and Kimi models are prohibited for this task.
