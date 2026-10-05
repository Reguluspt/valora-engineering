# Windows client: trusted native bridge

WIN-3 / [Issue #112](https://github.com/Reguluspt/valora-engineering/issues/112) adds typed native bridge infrastructure under [ADR 0050](../../docs/adr/0050-linux-server-windows-native-client.md), the [Windows plan](../../docs/plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md), and the [Frontend Architecture Rule](../../docs/architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md). WIN-0/1/2 remain certified prerequisites. The generic adapter is outside presentation composition; no feature screen consumes it. WIN-4 product integration, Preview/UAT, MSIX distribution and deployment remain separate gates. This is unsigned engineering evidence.

## Administrator configuration

An administrator provisions one `REG_SZ` value `ServerOrigin` at `HKLM\SOFTWARE\Valora\WindowsClient` in the 64-bit registry view. Keep standard machine-key permissions: administrators/SYSTEM write, ordinary users read only. The app runs as the current user, opens this key read-only, and never writes configuration or accepts a web/user URL override. Configuration provisioning and permission enrollment are outside this shell task.

The value is one absolute HTTPS origin, such as `https://<server-host>:8443`, optionally followed by `/`. Host case and default port 443 canonicalize deterministically; scheme, host and effective port define exact trust. Paths, query/fragment, userinfo, whitespace/control characters, backslashes, percent-encoded or Unicode hosts, trailing-dot hosts, noncanonical IPv4, ambiguous ports and non-HTTPS schemes are rejected. ASCII IDNA names and canonical IPv4/IPv6 are supported. No hostname/IP is hard-coded. Do not put credentials or tokens in this value.

No configuration shows a Vietnamese administrator instruction without creating a WebView. Invalid/inaccessible configuration fails closed. Retry rereads and revalidates the machine setting and creates a fresh session/control. Browser data is isolated under the current Windows user's LocalAppData with a SHA-256 directory derived only from the canonical HTTPS origin. Host case and explicit port 443 resolve to the same profile; different hosts or effective ports resolve to different profiles. A configuration change selects that origin's separate profile. Browser-managed cookies may persist across normal app restarts at the same origin; the profile contains no native identity proof.

## Server session and recovery

The existing server-hosted `SessionProvider` restores through `/api/v1/auth/me` and the web API client's existing refresh behavior. Login, logout, cookie clearing, expiry/revocation, CSRF, organization identity and RBAC remain web/server-owned under ADR 0026. Account/organization switching remains logout or expiry, then web login with `organization_slug`. The shell has no native login, identity cache, endpoint calls or cookie/token extraction; it neither auto-authenticates from profile presence nor recreates cleared cookies. Browser API 401/403 responses are unchanged and remain available to the hosted login/denial UI. Native `Loaded` means trusted document transport, never authenticated or authorized identity.

`WindowsLifecycleEvents` adapts Windows App SDK suspend/resume and .NET network-availability events into `ShellLifecycle`. Suspend or disconnect closes the current policy session synchronously on the event thread, before queued UI callbacks; the UI hides and destroys the old control on its dispatcher. Resume/reconnect enters revalidation and, once both awake and network-available, rereads machine configuration, validates the exact HTTPS origin, creates a fresh control/session, installs all WIN-1 security handlers and navigates only to the configured origin's `/` using a top-level GET. Old initialization completions, navigation callbacks, failures and queued recovery actions cannot revive or change the new session. Closing the window is terminal and unregisters platform handlers.

Recovery never uses Reload, browser history, form resubmission or reconstructed requests. An interrupted POST/PUT/PATCH/DELETE has an unknown outcome; existing web/server idempotency and recovery remain authoritative. Network availability is an OS connectivity hint, not proof that the LAN server is reachable: TLS/navigation failures still show native Retry. There is no offline mode, timer-driven mutation retry or native auth revalidation request.

## Navigation and lifecycle

`MainWindow` deliberately initializes installed stable Evergreen WebView2 with a per-origin profile; no fixed browser runtime is bundled. WIN-1 supports serviced Windows 11 x64 and Evergreen Runtime 154 or newer with the pinned SDK below. Missing runtime/API or initialization failure leaves native Retry available. Security handlers/settings are installed before the first application navigation.

Only exact-origin HTTPS top-level navigation is allowed. Every redirect is rechecked. Popups/new windows, external URI schemes, downloads and all child frames (including same-origin, blank and srcdoc frames) are denied in WIN-1. Blocking a frame revokes the entire session and stops navigation; the shell hides the control immediately and closes it outside the browser callback. This conservative frame policy avoids granting trust through nested or opaque frames. External URL opening remains unavailable because the production native destination catalog is empty.

Platform certificate validation remains enabled. Observable certificate errors explicitly cancel; there is no proceed/ignore handler, trust-store change or HTTP fallback. Native states cover initialization, loading, loaded, network/certificate/navigation failure, blocked navigation and Retry. Stale navigation completion cannot overwrite a later navigation or a revoked session; window closure prevents late initialization from reopening it. Only loaded trusted content is displayed. Messages are Vietnamese-first and never echo raw configuration, URLs, exceptions or secrets.

`FoundationCapabilityCatalog` remains an immutable empty baseline for foundation-only tests. Production installs `WebViewNativeBridge` with the bounded WIN-3 catalog. Web messages stay off until successful trusted top-level completion and current `ShellSession == Loaded`. Every request rechecks the current control/session, exact HTTPS origin and current document source. Navigation disables messages before dispatch; synchronous session revocation invalidates pending work and handles before queued browser/UI continuations. Host objects and native script injection remain disabled. Browser permissions and HTTP basic-auth prompts remain denied. React/Fluent 2 stays server-hosted; Linux retains auth/session, tenant/RBAC, domain commands, Case State, audit/CAS, documents, jobs and providers.

## WIN-3 protocol and capability boundary

Protocol is `valora.native/1`; transport is WebView2 web messages, never a host object. `hello` is a control request using the ordinary request envelope and empty payload:

```json
{"protocol":"valora.native/1","type":"request","requestId":"<canonical lower-case UUID>","capability":"hello","payload":{}}
```

Its response uses the frozen success envelope with `result: {protocol, capabilities}`. It exposes only enabled capability names; no authentication, identity or business state. Capability requests require successful negotiation in the current bridge generation. Envelopes/payloads are strict objects with no extra or duplicate fields. Messages are bounded to 64 KiB UTF-8; at most eight requests and one picker/save/Office/external confirmation operation are in flight. Office association launches use `TreatAsUntrusted`, so they share that interaction lock until OS completion. Request IDs cannot replay in a generation; a 4096-ID memory ceiling returns BUSY until generation renewal, without evicting IDs that could repeat an OS action.

| Capability | Production WIN-3 state / payload and result |
| --- | --- |
| `pickExcelFile` | Enabled; `{}`; single `.xls/.xlsx` selection or normal `{selected:false}` cancellation. |
| `pickDocumentFile` | Enabled; `{}`; single `.docx` selection or cancellation. |
| `openInExcel` / `openInWord` | Enabled; `{handle}`; current eligible handle and refreshed type/size; fixed `StorageFile` association launcher, no executable/arguments. Native result `{opened:true}` means only OS launch accepted. |
| `dragDrop` | Enabled event source on the existing native connection bar; single eligible native file only. `filesDropped` carries bounded handle metadata, never upload/import/Apply. No feature/screen wiring. |
| `saveDownloadedArtifact` | Unadvertised; strict `{artifactHandle,suggestedFilename}` and bounded Save As service/test seam exist, but no production artifact mint or server download binding. No network fetch, source/destination path or file bytes in the envelope. |
| `showNotification` | Unadvertised/unavailable; title ≤80 and body ≤256 Unicode scalars, no action/URL. Unpackaged identity/registration is not fabricated. |
| `deepLink` | Unadvertised production source; validator and event seam only. App-relative route ≤2048 UTF-16 characters, no authority/scheme/control/backslash/traversal ambiguity; query/fragment navigation context remains available. No OS registration or business command. |
| `openExternalUrl` | Unadvertised/unavailable with an empty native allowlist. Policy tests prove absolute HTTPS exact-origin matching with no wildcard, suffix, userinfo or scheme coercion. No provider/OAuth exception. |

Selected/drop metadata is `{handle,name,extension,sizeBytes}` (plus `selected:true` for picker success). Handles have 192 bits of cryptographic randomness, are in-memory only, belong to one bridge generation and are limited to 32 live entries. No raw path is returned. The hard native ceiling is 64 MiB; WIN-4 must apply any stricter server/product limit. Ordinary selection handles cannot serve as artifact handles. Save As, when exercised through a trusted native artifact test seam, requires a user destination, matching extension and bounded chunked copying with generation checks; partial OS I/O/cancellation is never business success.

Revocation closes admission and clears handles, replay memory and interaction state; pending requests resolve with `BRIDGE_REVOKED`. Old metadata/picker completions cannot register handles or start a later launch/save in a new generation. Dispatch continuations retain their original generation; dropped files also retain the generation captured before asynchronous OS data retrieval. Native event envelopes are `{protocol,type:"event",event,payload}`; names are `bridgeRevoked`, `filesDropped`, and `deepLink`. They carry only revocation, file metadata or navigation context and never authoritative product state.

`frontend/src/native/bridge.ts` feature-detects `window.chrome?.webview`, negotiates hello, validates bounded responses/errors/events and correlates at most eight pending calls. Normal browsers explicitly return unavailable. Revoke/dispose rejects pending calls and removes listeners. A 120-second local deadline fails closed and never retries; an OS action already started may have an uncertain outcome. No API/session bootstrap, React feature, page, token, style or visual system is changed. Any later feature integration must preserve server business authority and the canonical five presentation layers.

## Layout and verification

- `Valora.Windows.App`: native WinUI lifecycle, read-only machine configuration, origin/session policy and WebView2 event boundary.
- `Valora.Windows.Bridge`: strict protocol/parser, generation-scoped opaque handles and dispatch through the `INativePlatform` boundary; no WebView, WinUI or domain dependency.
- `Valora.Windows.Tests`: production profile/session/lifecycle policy compiled into tests, deterministic suspend/network/race/terminal-close checks, source scans for forbidden native auth/identity/replay primitives, and a hidden STA WinForms WebView2 host for actual browser-event tests. The lifecycle browser fixture submits a form POST, discards the control, reuses its browser profile, and proves recovery sends one root GET on a fresh control; browser API 401/403 fixtures preserve server responses. WinUI-specific hosting and the platform adapter are compiled by the application build.
- `build.ps1`: locked restore, Release x64 build/tests/publish, unsigned executable/XAML resource checks, published native no-config/Retry/closure smoke, file hashes and deterministic ZIP order/timestamps. The native smoke requires an unconfigured machine and preserves existing registry configuration by failing if it exists.
- [Windows workflow](../../.github/workflows/windows-client.yml): exact PR head, identical build script and artifact/TRX upload; main/path-filtered PR and manual dispatch triggers.

Browser tests intercept controlled document fixtures to exercise redirects/popups/frames/external schemes without certificates or script injection by the native host. A separate real network smoke uses `https://example.com`; expired, wrong-host and self-signed negatives use the public badssl endpoints. These need network access, an installed Evergreen runtime and an interactive Windows desktop. They do not install certificates or bypass TLS. Public fixture availability is an external test dependency; failure remains failure, never a skipped PASS. They certify shell/browser trust behavior, not a deployed Valora LAN instance or a product journey.

## Pinned compatible toolchain

Verified against Microsoft release information and NuGet metadata on 2026-10-03. All pins are stable, non-preview; transitive versions and content hashes are committed in each project's `packages.lock.json`.

| Component | Pin | Compatibility reason |
| --- | --- | --- |
| .NET SDK / bundled runtime | `10.0.401` / `10.0.12` | Supported .NET 10 LTS; exact SDK selection with prerelease and roll-forward disabled. CLI build uses bundled MSBuild `18.9.11`; no Visual Studio installation needed. |
| Windows target / .NET projection | `10.0.26100.0` / `10.0.26100.87` | Supported Windows 11 SDK family; explicit projection avoids an SDK-selected API version change. Minimum OS contract is Windows 11 `10.0.22000.0`, with support limited to serviced Windows 11 x64 editions. |
| Windows SDK BuildTools | `10.0.26100.9169` | Stable 26100 build tooling, restored by NuGet; no preview SDK or machine-installed SDK dependency. |
| Windows App SDK WinUI | `2.3.9` | Stable WinUI component shipped in Windows App SDK `2.5.1`; selected component avoids aggregate AI/ML dependencies. Compatible Base `2.0.4`, Foundation `2.3.12`, InteractiveExperiences `2.1.9` locked from the stable release. |
| WebView2 SDK | `1.0.4258.31` | Stable release aligned to Runtime 154; exceeds WinUI's package minimum `1.0.3719.77`. Runtime direction remains serviced Evergreen; no fixed browser runtime is bundled. |
| Windows tests | Test SDK `18.10.1`, xUnit `2.9.3`, VS runner `3.1.5` | Stable test tooling; Windows .NET 10 x64 execution uses VSTest. |

Microsoft dependencies use their published Microsoft license terms; xUnit packages use Apache-2.0. These dependencies supply shell/build/test functions only; no new domain/platform ADR is needed. No database migrations or server dependencies change.

Primary references: [Microsoft .NET 10 downloads](https://dotnet.microsoft.com/en-us/download/dotnet/10.0), [Windows App SDK stable release](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/release-notes/windows-app-sdk-2-0), [WinUI package metadata](https://www.nuget.org/packages/Microsoft.WindowsAppSDK.WinUI/2.3.9), [Windows SDK support](https://learn.microsoft.com/en-us/windows/apps/windows-sdk/), [WebView2 SDK releases](https://learn.microsoft.com/en-us/microsoft-edge/webview2/release-notes/sdk/), [self-contained deployment](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/self-contained-deploy/deploy-self-contained-apps).

## Build from a fresh checkout

Prerequisites: Windows x64, PowerShell 7, Git, the exact .NET SDK above, and access to nuget.org. Place that SDK first on PATH. Run from `clients/windows` so `global.json` governs SDK selection:

```powershell
dotnet --version # must be 10.0.401
./build.ps1
```

The script executes these commands and stops on any nonzero exit:

```powershell
dotnet restore Valora.Windows.sln --locked-mode -p:Platform=x64
dotnet build Valora.Windows.sln --no-restore -c Release -p:Platform=x64
dotnet test Valora.Windows.Tests/Valora.Windows.Tests.csproj --no-build --no-restore -c Release -p:Platform=x64 --logger 'trx;LogFileName=windows.trx' --results-directory artifacts/test-results
dotnet publish Valora.Windows.App/Valora.Windows.App.csproj --no-build --no-restore -c Release -p:Platform=x64 -o artifacts/app
```

For Debug, restore with the same platform and build with `-c Debug`. Lockfile updates are deliberate dependency changes; normal builds never use `--force-evaluate`. Projects and artifacts are isolated from the server/frontend dependency graph.

## Engineering artifact and gates

`artifacts/valora-win-x64-unsigned.zip` contains the unpackaged self-contained App, Bridge and required .NET/Windows App SDK files. Extract all files together on serviced Windows 11 x64 with Evergreen WebView2 installed. `Valora.Windows.App.exe` is unsigned; vendor binaries may retain Microsoft signatures. No MSIX, signing secret, enrollment, installer or update/distribution policy is added.

`manifest.json` records the task, Git source commit, exact SDK, target and SHA-256 of every application file. `SHA256SUMS` identifies the ZIP; TRX records tests. CI uploads these and committed lockfiles with 14-day retention. Managed output uses deterministic compilation and normalized source paths; archive entries have fixed ordering/timestamps. Byte repeatability requires identical app bytes and compression tooling; runner servicing and Evergreen remain external variables.

WIN-3 starts from the Gate Owner's named certified main baseline and prerequisite evidence. Before freezing, fetch main, stop on drift, inspect the complete bounded diff, run candidate checks and `git diff --check`, and commit a clean candidate. DeepSeek and Gemini independently review the same frozen HEAD. Then create a Draft PR and require repository and Windows CI SUCCESS on that exact SHA. Any HEAD change renews required evidence. Real machine suspend/network manipulation is supplementary; deterministic tests require no privileged machine changes. Actual Valora LAN login/logout/expiry acceptance and Preview/UAT remain separate product evidence. Ready/merge belongs to the Gate Owner.
