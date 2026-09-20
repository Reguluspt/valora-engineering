# Valora documentation entry points

Navigation index; this file does not replace design authority or acceptance evidence. Links below cover the current engineering entry points, not an exhaustive inventory of historical sprint documents.

## Authority and implementation status

- [Coding-agent rules](../CODEX.md) and [engineering guardrails](../ENGINEERING_GUARDRAILS.md).
- [Project AI execution policy](../CODEX.md#10-project-ai-execution-policy) — canonical Codex,
  delegated mechanical-worker, independent-review and commit-ownership rules.
- [UI/UX v2.3 master](design/VALORA_UIUX_HANDOFF_v2.3.md) and [authority reading order](design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md).
- [PR-00 through PR-13 per-layer acceptance matrix](implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md).

## PR-07 — provider conformance and storage successor

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
- [Local provider task awaiting G6](plan/valora-storage-local-001.md) — Linux atomic create-only adapter passed T1-T14/L1-L17 and awaits two independent reviews; Exchange and Backup remain later separate gates.
- [Superseded provider-spike selection](research/valora-storage-provider-selection.md) — historical AWS/Azure comparison and AWS G1-G4 preparation rationale.
- [Storage policy decision](research/pr07-storage-fallback-options-2.md) — Model A and the accepted retention, deletion, encryption and recovery baseline; links the superseded initial fallback research.
- [Accepted ADR 0042](adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md) and [accepted sync/conflict contract](implementation/VALORA_UIUX_V2_3_PR07_SYNC_CONFLICT_CONTRACT.md).
- [Provider-conformance runbook](implementation/VALORA_UIUX_V2_3_PR07_PROVIDER_CONFORMANCE_RUNBOOK.md) — historical/current execution evidence; PR-07 runtime remains blocked.
- [Research handoff](research/pr07-onedrive-conformance-handoff.md) — C1 chronology plus the amended C2 observation and remaining provider questions.
