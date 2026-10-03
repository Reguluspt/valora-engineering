# VALORA — Windows Preview Task Brief

**Task:** `VALORA-WIN-PREVIEW-001`
**Status:** FORMAL PREVIEW/UAT PLANNED — BLOCKED UNTIL SOFTWARE COMPLETION
**Reconciled:** 2026-10-03 under Issue #89 / `VALORA-TASK-ARCH-WINDOWS-CLIENT-SERVER-001`
**Architecture:** [ADR 0050](../adr/0050-linux-server-windows-native-client.md), accepted Product Owner deployment/client v1 decision; repository certification pending
**Runtime baseline:** assigned only by a separate accepted task contract after Software Completion

## Objective

Accept the complete Valora product on the Product Owner's Windows desktop/laptop through the WinUI 3 + WebView2 client connecting to the Linux Server over HTTPS LAN. React / Microsoft Fluent 2 light remains server-hosted. Windows Preview cannot discover, design or fill missing product runtime, broaden domain semantics or replace exact-SHA Software Completion evidence.

## Three distinct workstreams

| Workstream | Authority / entry gate |
|---|---|
| Windows Client architecture/foundation | [Windows Client plan](../plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md); architecture/skeleton before Software Completion only under explicit Product Owner task. Issue #89 implements docs only. |
| Windows Client formal Preview/UAT | This brief / WIN-6; after certified Software Completion and a separately accepted Preview contract. |
| Linux Server Deployment Pilot | [Linux Server plan](../plan/VALORA_LINUX_SERVER_V1_PLAN.md); separately authorized operations/deployment gate with TLS, persistence, migrations, encrypted backup/restore and runbook evidence. Windows UAT does not certify it. |

## Roadmap position

```text
Architecture decision: Linux Server + Windows Native Client v1 (Issue #89 / ADR 0050)
→ separately authorized architecture/foundation tasks as appropriate

Unified Roadmap OS-G0 through OS-G6 required product closure
→ Pre-case + Appraisal Core + Document Runtime + Release/Publishing
→ traceability/state/fidelity + North-star exact-SHA E2E
→ Software Completion acceptance on an exact merged SHA
→ Windows Client formal Preview/UAT (WIN-6)
→ separately authorized Linux Server Deployment Pilot
```

The earlier Windows/Docker Desktop local stack and architecture-selection-after-Preview ordering are superseded. Cloud staging is not an automatic next step; any cloud/production gate requires a separate owner decision. SharePoint and OneDrive for Business remain deferred. OS-G7/provider AI gating is unchanged, with no local LLM or GPU dependency in server v1.

## Software Completion entry gate

Formal Windows Preview/UAT may begin only when:

1. Unified Roadmap OS-G0 through OS-G6 required product/acceptance gaps are closed; historical PR-00–PR-13 labels are evidence, not current sequencing.
2. Login, session restoration, logout, account/organization context and real project selection work through the product UI under server authority.
3. Document Workspace and Working-change review follow ADR 0045; observation/revalidation is non-authoritative and accepted revisions remain human-confirmed.
4. Every production-scope screen uses real APIs or truthful unavailable state; no placeholder/demo data substitutes for behavior.
5. Required backend/frontend tests, lint, build, migration, tenant, security and exact-SHA integration gates pass.
6. OS-G6 proves the supported North-star journey on the exact candidate SHA with failure/retry/tenant/immutability and visual-authority checks.

## Deferred implementation boundary

A later accepted contract may authorize bounded WinUI/WebView2 client integration, MSIX install/update/signing, trusted-origin configuration, session/reconnect UX and typed native capabilities. It must preserve server authentication/session, CSRF, tenant, RBAC, audit, state/version and M365/document safety controls. No backend/database/worker is bundled in the client and no business authority moves into C# or React.

A separate Linux operations contract owns Compose, lifecycle, migrations, health/readiness, persistent data, secrets and backup/restore. These are not client PowerShell launch responsibilities. Plans and architecture documents alone authorize none of this runtime.

## Acceptance boundary

Use an exact compatibility manifest for server SHA/image set, React build, Windows package version/hash, native bridge protocol and WebView2 runtime. Prove HTTPS/certificate/trusted-origin enforcement, install/uninstall/upgrade, login/logout/expiry, safe reconnect, permitted file/Office/notification/deep-link flows, unavailable Office, permission denial, version mismatch/conflict and unknown-write recovery. Desktop/laptop, DPI/multiple monitors, sleep/resume, LAN failure, Vietnamese filenames and bounded large-file behavior require evidence. Preserve Fluent 2 light golden surfaces and truthful failure UX.

Linux persistence/backup/restore requires independent server-pilot evidence; MSIX launch success does not prove it. Secrets stay out of diagnostics, JavaScript and public evidence. Detailed UAT acceptance is frozen against the future exact candidate/host, not inferred from historical environment surveys.

## Non-goals and review

No missing business feature, domain expansion, local authoritative database, offline sync engine, generic process/file/PowerShell bridge, React-to-WinUI rewrite, production/cloud deploy, live provider reconsent or real production data is authorized. Word/Excel Save and bridge success never commit authoritative revisions or business facts.

The first formal Preview does not introduce MSI, a Windows service or an automatic update channel; MSIX is the accepted packaging direction. Client/pilot work must not interfere with unrelated host processes, ports or containers.

Codex is the writer/orchestrator under live CODEX. Claude and Kimi remain prohibited for the Preview task unless the Product Owner revises its contract. Future task risk and review gates are assigned in the accepted contract; this brief does not automatically require two reviewers for every foundation task. Issue #89 requires one independent DeepSeek review on a frozen HEAD, exact-head CI and Draft PR only; Gemini is conditional on material architecture/security ambiguity. No Ready or merge is authorized by Issue #89.
