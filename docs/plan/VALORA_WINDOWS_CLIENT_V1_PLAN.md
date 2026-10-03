# VALORA Windows Client v1 Plan

**Status:** PLANNED / NOT AUTHORIZED FOR RUNTIME
**Date:** 2026-10-03
**Task:** `VALORA-TASK-ARCH-WINDOWS-CLIENT-SERVER-001` / Issue #89
**Spec:** [ADR 0050](../adr/0050-linux-server-windows-native-client.md)

## Goal and constraints

Deliver a WinUI 3 + WebView2 native shell for server-hosted React / Microsoft Fluent 2 light, Windows 11 x64 first, Evergreen Runtime and MSIX. Admin config supplies the HTTPS Valora URL; no automatic LAN discovery. Linux domain/API remains business authority; no backend/database/worker or React bundle by default in MSIX.

Each phase needs a separately authorized Product Owner task, exact green baseline and bounded contract. Only explicit architecture/skeleton tasks may start before Software Completion; formal WIN-6 Preview/UAT cannot. Phase completion never opens the next product stage, deploys a server or grants live provider activity. Current UI/UX, tenant/RBAC, auth/CSRF, mutation and document authority remain unchanged.

## Owned work and acceptance

| Phase | Planned deliverable | Entry / focused acceptance evidence |
|---|---|---|
| WIN-0 | Windows solution and Windows CI; native app, bridge and tests separated; pin SDK/.NET/WebView2 versions in the task | Explicit foundation assignment; restore/build x64 on Windows runner, reproducible unsigned CI artifact, no signing secret in repo |
| WIN-1 | WinUI lifecycle + WebView2, protected server URL configuration, loading/error/retry and trusted-origin navigation | WIN-0 exact green baseline; real HTTPS UI smoke; reject invalid certificates, HTTP, foreign origin/frame messages, redirects/popups inheriting bridge; no broad host object |
| WIN-2 | Server auth/session, profile lifecycle, logout, expiry, account/org switch, sleep/resume and reconnect | WIN-1; preserve ADR 0026 cookies/CSRF/origin behavior; expired/revoked session and 401/403 fail closed; reconnect revalidates before freshness-dependent commands; unknown writes use existing recovery |
| WIN-3 | Typed/versioned native bridge and narrow React adapter | WIN-2; freeze per-capability schemas/limits; test file picker/cancel, bounded download/Save As, eligible Word/Excel launch, drag/drop, notification, deep-link and controlled external URL; reject arbitrary process/file/PowerShell and malformed/untrusted calls |
| WIN-4 | Product integration into authorized Excel intake, result download, Working document/Office and contextual deep-link surfaces | Required product/API contracts exist; compatibility handshake gates native features; preserve staging/Apply and ADR 0043/0045; denied/stale/conflict/unknown outcomes never become fake success; no missing product capability added through shell |
| WIN-5 | MSIX identity/version, install/uninstall/upgrade, protocol registration and controlled signing/distribution preparation | WIN-4; exact package/build/compatibility evidence, clean upgrade/profile policy and rollback; signing certificate/secret handling separately approved, unsigned artifacts are not production certification |
| WIN-6 | Formal Windows Preview/UAT and hardening | Software Completion certified on exact SHA plus separate Preview contract; pin client/server/web/bridge/runtime matrix; complete supported journey and negative paths on desktop/laptop |

Suggested future ownership paths are `clients/windows/Valora.Windows.sln`, `Valora.Windows.App/`, `Valora.Windows.Bridge/` and `Valora.Windows.Tests/` beneath `clients/windows/`; they are planning targets, not artifacts created by Issue #89. Exact code/test/workflow paths and signatures are frozen by each implementing contract.

## Bridge and compatibility review focus

Allowed categories: `pickExcelFile`, `pickDocumentFile`, `saveDownloadedArtifact`, `openInWord`, `openInExcel`, drag/drop mediation, `showNotification`, deep links and controlled external URL. Schema validation, trusted sender/frame, user gesture where required, scoped file handles, bounded payload/type/size, correlation, cancellation and sanitized errors belong in WIN-3 acceptance. Generic `execute_process(any)`, `read_file(any)`, `write_file(any)` and `run_powershell(any)` are forbidden.

WIN-4 binds server/API, web build, bridge version and minimum/recommended client version before enabling affected actions. Missing/incompatible contracts require clear unavailable/update UX, not silent fallback. Native configuration/diagnostics contain no injected authentication/provider secrets; server-approved operations remain subject to server authorization.

## WIN-6 UAT matrix

Validate supported Windows 11 versions; 100/125/150% scaling; desktop/laptop and multiple monitors; sleep/resume; LAN disconnect/reconnect; server restart; invalid/expired certificates; session expiry/revocation; permission denial; Vietnamese filenames/long paths; large bounded Excel input; file-picker cancellation; Office installed/missing; Defender interaction; version conflicts/unknown commit; client/server/bridge mismatch; MSIX upgrade/rollback and server restore followed by safe reconnect. Office Save never creates accepted revisions automatically. Preserve Vietnamese-first Fluent 2 light golden surfaces.

Evidence records exact server SHA/image set, React revision, client package/version/hash, bridge contract, WebView2 runtime, focused tests and applicable exact-head CI. Full suites are candidate gates when required, not repeated edit-loop work. Review and formal acceptance are assigned in each later task contract.

## Separate server gate and open decisions

[Linux Deployment Pilot](VALORA_LINUX_SERVER_V1_PLAN.md) needs its own operations/deployment authority. [Windows Preview brief](../implementation/VALORA_WINDOWS_PREVIEW_TASK_BRIEF.md) owns formal UAT after Software Completion; neither plan substitutes for product completion or automatically opens cloud staging.

Later tasks pin SDK/runtime support versions, signing certificate, distribution/update method and support policy. Remote access/concurrency SLA remain open; no offline-first sync or local LLM is introduced. Follow the [Unified Roadmap](../VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md) and [CODEX](../../CODEX.md) before assigning runtime.
