# Valora documentation entry points

Navigation index; this file does not replace design authority or acceptance evidence. Links below cover the current engineering entry points, not an exhaustive inventory of historical sprint documents.

## Authority and implementation status

- [UI/UX v2.3 master](design/VALORA_UIUX_HANDOFF_v2.3.md) + [authority reading order](design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md) — current product semantics, workflow, IA, interaction and Microsoft Fluent 2 light visual authority.
- [Unified Appraisal OS roadmap](VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md) — current development sequencing / architecture integration; it does not silently override UI/UX semantics.
- [VALORA AI Master Plan v1.0](architecture/VALORA_AI_MASTER_PLAN_V1.md) — current OS-G7 / AI-readiness architecture detail and AI-readable-by-design prerequisite; documentation authority only, not runtime authorization.
- [AI-PR-000…012 implementation contracts](implementation/VALORA-AI-PR-000_MASTER_PLAN_AUTHORITY_RECONCILIATION_CONTRACT.md) — future AI delivery sequence; runtime contracts remain gated until explicitly authorized.
- [Documentation status index](DOCUMENTATION_STATUS_INDEX.md) — canonical classification of current authority, living engineering docs, historical audits/sprints/handoffs and superseded provider research.
- [Design Authority Index](design/VALORA_DESIGN_AUTHORITY_INDEX.md) — current scoped read order and supersession map.
- [ADR 0048: guarded Apply / Asset Review](adr/0048-post-intake-guarded-apply-and-asset-review-authority.md) and [ADR 0049: line validation / human review](adr/0049-asset-line-human-review-and-validation-authority.md) — current accepted scoped authority and implementation-contract navigation.
- [DOC-R0 inventory](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.md) / [JSON path ledger](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_INVENTORY.json), [certified conflict matrix](audits/2026-10-03__DOCUMENTATION_AUTHORITY_CONFLICT_MATRIX.md), and [DOC-R6 final closeout](audits/2026-10-03__DOCUMENTATION_AUTHORITY_RECONCILIATION_CLOSEOUT.md) — current reconciliation chain, census and disposition; historical evidence remains preserved.
- [2026-09-24 final AI Master Plan / Unified Roadmap documentation reconciliation](audits/2026-09-24__AI_MASTER_PLAN_UNIFIED_ROADMAP_DOCUMENTATION_RECONCILIATION.md) — historical full-tree audit and dated 379/380 census, contradiction closeout, preserved-history classification and validation record.
- [2026-09-21 documentation reconciliation audit](audits/2026-09-21__DOCUMENTATION_RECONCILIATION_UNIFIED_ROADMAP_V2_3.md) — historical reconciliation snapshot; retain its exact branch/head/inventory evidence, but do not use its older counts/status labels as current authority.
- [2026-09-21 Handoff/Roadmap/Fluent 2 reconciliation audit](audits/2026-09-21__DOCUMENTATION_RECONCILIATION_HANDOFF_ROADMAP_FLUENT2.md) — historical reconciliation snapshot; useful for the 2026-09-21 decision trail, current census/status navigation is through the Documentation Status Index and DOC-R6 closeout; its dated evidence remains preserved.
- [Frontend Astryx → Fluent 2 code inventory](audits/2026-09-22__FRONTEND_ASTRYX_TO_FLUENT2_CODE_INVENTORY.md) — historical code-inventory baseline at `bc31acd…`; its dated 2026-09-23 disposition recorded F2-PR-001…003 completion and then-remaining F2-PR-004…008 debt. All eight were subsequently completed through PR #32 / OS-G0 closure.
- [VALORA-FLUENT2-REMEDIATION-001](implementation/VALORA-FLUENT2-REMEDIATION-001.md) — historical / completed OS-G0 implementation contract and F2-PR-001…008 delivery sequence (PR #32 / CI #485); retained historical packets are `VALORA-FLUENT2-F2-PR-001_IMPLEMENTATION_PLAN.md` through `...008...` in `docs/implementation/`.

- [Coding-agent rules](../CODEX.md) and [engineering guardrails](../ENGINEERING_GUARDRAILS.md).
- [Project AI execution policy](../CODEX.md#10-project-ai-execution-policy) — canonical Codex,
  delegated mechanical-worker, independent-review and commit-ownership rules.
- [Agent Operating Protocol v2](plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md) — single current general operating-process entrypoint for fresh Gate Owner/Architect and Dev/Codex sessions; Reference-first, Local-first, startup, verification/review and exact-SHA integration.
- [Compact Task Contract](plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md), [session bootstrap skill](../.agents/skills/valora-session-bootstrap/SKILL.md) and [OpenViking profile](plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) — supporting template/procedures and specialized optional MCP policy.
- [Lean Agent Protocol v1](plan/VALORA_LEAN_AGENT_PROTOCOL_V1.md) — SUPERSEDED / HISTORICAL; preserved body, current successor is V2.
- [PR-00 through PR-13 per-layer acceptance matrix](implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md) — historical PR-labelled acceptance evidence plus current candidate reconciliation; **not** current roadmap sequencing.

## Linux Server / Windows Client v1

- [ADR 0050](adr/0050-linux-server-windows-native-client.md) — accepted Product Owner deployment/client decision; Linux Server business authority, HTTPS LAN, WinUI 3/WebView2, server-hosted React/Fluent 2 light, typed native bridge, MSIX and no local LLM/GPU dependency.
- [Windows Client v1 plan](plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md) — WIN-0 through WIN-6; planned, runtime requires explicit tasks.
- [Linux Server v1 plan](plan/VALORA_LINUX_SERVER_V1_PLAN.md) — private Compose/TLS, persistence, readiness, encrypted backup/restore and operations; no deployment authorization.
- [SRV-0 Linux Server foundation](../infra/server/README.md) — Issue #101 release/image manifest, separate Compose/TLS/private-network contracts and deterministic proof; deployment and operational choices remain gated.
- [Windows Preview brief](implementation/VALORA_WINDOWS_PREVIEW_TASK_BRIEF.md) — formal UAT after Software Completion; Linux Deployment Pilot separate.

## Document storage, OneDrive Exchange and document-change direction

- [OAuth diagnostics and C2 implementation plan](plan/pr07-oauth-c2-implementation.md) — G1 and the first bounded G2 attempt are historical; G4 remains closed.
- [C2 partial-response semantics research](research/pr07-c2-partial-response-semantics.md) — the v1 predicate correction plus the amended single v2 live observation.
- [C2_AUTO_V2 local correction plan and closeout](plan/pr07-c2-auto-v2-local-correction.md) — schema-v3 correction locally implemented, verified and independently reviewed before its consumed live authority.
- [Stale-session `404` architecture evaluation](research/pr07-stale-session-404-decision.md) — G3 evidence; recommended Option A was accepted.
- [Completed G3 architecture decision](plan/done/pr07-g3-architecture-decision.md) — Product Owner approved retaining D6 and closing C2 research.
- [Completed read-only provider clarification plan](plan/done/pr07-provider-clarification-read-only.md) — public sources remain undocumented; no provider mutation occurred.
- [Provider clarification public-source result](research/pr07-provider-clarification-public-sources.md) — six-question status table and unmet reopen trigger.
- [Sanitized Microsoft clarification packet](ref/pr07-provider-clarification-question-packet.md) — submitted to public Microsoft Q&A on 2026-09-19; response pending.
- [Accepted ADR 0043 storage successor](adr/0043-app-owned-immutable-document-storage.md) — DB/CurrentHead authority, immutable blob invariants and the current local-VPS pilot amendment; long-term production encryption/recovery targets remain unproven.
- [Document Blob Storage contract](implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md) — accepted narrow provider port, normalized persistence, DB CAS and T1–T14 recovery matrix for the local fake task.
- [Completed storage architecture task](plan/done/valora-storage-arch-001.md) — accepted policy baseline and the bounded next gate.
- [Completed storage fake task](plan/done/valora-storage-fake-001.md) — provider-neutral persistence, deterministic fake, PostgreSQL DB CAS and T1–T14 proof accepted with no cloud calls.
- [Deferred isolated S3 spike](plan/valora-storage-s3-spike-001.md) — G1-G4 static evidence is retained; G5 live AWS and G6 provider selection were not run after the Product Owner changed the current deployment path.
- [Current pilot storage/OneDrive decision](research/valora-storage-provider-selection-2.md) — local authoritative immutable blobs plus independent non-authoritative OneDrive Exchange and encrypted Backup roles.
- [Completed Local provider task](plan/valora-storage-local-001.md) — G6 accepted on exact reviewed snapshot `d71a42e…`; T1-T14/L1-L17, PostgreSQL CAS/migration and two independent reviews passed. Durable evidence: `VALORA_STORAGE_LOCAL_G6_CLOSEOUT_MANIFEST.json`.
- [Superseded provider-spike selection](research/valora-storage-provider-selection.md) — historical AWS/Azure comparison and AWS G1-G4 preparation rationale.
- [Storage policy decision](research/pr07-storage-fallback-options-2.md) — Model A and the accepted retention, deletion, encryption and recovery baseline; links the superseded initial fallback research.
- [Accepted ADR 0044 Exchange v1](adr/0044-onedrive-personal-exchange-v1.md) — explicit
  DOCX/XLSX import/re-import, AppFolder capability, create-new Working/Export and provider-unknown
  reconciliation while OneDrive remains non-authoritative.
- [Working Change Observation / DocumentChangeCandidate / Human Commit Design Authority](design/VALORA_UIUX_HANDOFF_v2.3_WORKING_CHANGE_OBSERVATION_REVIEW_CONTRACT_ADDENDUM.md) — automatic Working-copy detection/revalidation and recommendation with no automatic business commit or Revision creation.
- [Accepted ADR 0045](adr/0045-working-copy-change-observation-and-human-confirmed-document-revision.md) — folder-level change signal + delta/exact revalidation + non-authoritative DocumentChangeCandidate + explicit human-confirmed Revision N+1 boundary.
- **Next implementation gate for document change observation:** freeze `VALORA-DOCUMENT-CHANGE-OBSERVATION-001` runtime contract (subscription lifecycle, webhook validation, delta cursor, durable job, DocumentChangeCandidate schema/read model, stale rules, review/confirmation API and acceptance matrix) before coding.
- [OneDrive Exchange v1 implementation contract](implementation/VALORA_ONEDRIVE_EXCHANGE_V1_CONTRACT.md)
  and [completed G8 offline plan](plan/valora-onedrive-exchange-001.md) — offline schema/port/state-machine,
  UI boundary and E1–E30 acceptance completed at code milestone `f896f15…`; live Microsoft AppFolder conformance remains a separate Product Owner gate.
- [Accepted ADR 0042](adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md) and [accepted sync/conflict contract](implementation/VALORA_UIUX_V2_3_PR07_SYNC_CONFLICT_CONTRACT.md).
- [Provider-conformance runbook](implementation/VALORA_UIUX_V2_3_PR07_PROVIDER_CONFORMANCE_RUNBOOK.md) — historical evidence for the rejected direct OneDrive replacement path; ADR 0042/D6 remains relevant only if direct replacement is proposed again.
- [Research handoff](research/pr07-onedrive-conformance-handoff.md) — C1 chronology plus the amended C2 observation and remaining provider questions.
