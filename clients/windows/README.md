# Windows client: trusted navigation

WIN-1 is the bounded Windows shell slice in [Issue #106](https://github.com/Reguluspt/valora-engineering/issues/106), governed by [ADR 0050](../../docs/adr/0050-linux-server-windows-native-client.md) and the [Windows plan](../../docs/plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md). WIN-0 foundation remains certified. This is unsigned engineering evidence; Preview/UAT and production distribution require later gates.

## Administrator configuration

An administrator provisions one `REG_SZ` value `ServerOrigin` at `HKLM\SOFTWARE\Valora\WindowsClient` in the 64-bit registry view. Keep standard machine-key permissions: administrators/SYSTEM write, ordinary users read only. The app runs as the current user, opens this key read-only, and never writes configuration or accepts a web/user URL override. Configuration provisioning and permission enrollment are outside this shell task.

The value is one absolute HTTPS origin, such as `https://<server-host>:8443`, optionally followed by `/`. Host case and default port 443 canonicalize deterministically; scheme, host and effective port define exact trust. Paths, query/fragment, userinfo, whitespace/control characters, backslashes, percent-encoded or Unicode hosts, trailing-dot hosts, noncanonical IPv4, ambiguous ports and non-HTTPS schemes are rejected. ASCII IDNA names and canonical IPv4/IPv6 are supported. No hostname/IP is hard-coded. Do not put credentials or tokens in this value.

No configuration shows a Vietnamese administrator instruction without creating a WebView. Invalid/inaccessible configuration fails closed. Retry rereads and revalidates the machine setting and creates a fresh session/control. Browser data is isolated under the current Windows user's LocalAppData with a SHA-256 directory derived from the canonical origin. That profile is browser-managed; it does not establish server authentication. WIN-2 owns session/account cleanup and reconnect semantics.

## Navigation and lifecycle

`MainWindow` deliberately initializes installed stable Evergreen WebView2 with a per-origin profile; no fixed browser runtime is bundled. WIN-1 supports serviced Windows 11 x64 and Evergreen Runtime 154 or newer with the pinned SDK below. Missing runtime/API or initialization failure leaves native Retry available. Security handlers/settings are installed before the first application navigation.

Only exact-origin HTTPS top-level navigation is allowed. Every redirect is rechecked. Popups/new windows, external URI schemes, downloads and all child frames (including same-origin, blank and srcdoc frames) are denied in WIN-1. Blocking a frame revokes the entire session and stops navigation; the shell hides the control immediately and closes it outside the browser callback. This conservative frame policy avoids granting trust through nested or opaque frames. No external-opening native capability exists.

Platform certificate validation remains enabled. Observable certificate errors explicitly cancel; there is no proceed/ignore handler, trust-store change or HTTP fallback. Native states cover initialization, loading, loaded, network/certificate/navigation failure, blocked navigation and Retry. Stale navigation completion cannot overwrite a later navigation or a revoked session; window closure prevents late initialization from reopening it. Only loaded trusted content is displayed. Messages are Vietnamese-first and never echo raw configuration, URLs, exceptions or secrets.

`FoundationCapabilityCatalog` remains immutable and empty. Web messages and host objects are disabled; no script injection, native dispatch, file/process/PowerShell, Office, notifications or deep-link handler is exposed. Browser permission requests and HTTP basic-auth prompts are denied. React/Fluent 2 remains server-hosted. Linux retains auth/session, tenant/RBAC, domain commands/validation, Case State, audit/CAS, documents, jobs and providers; ADR 0026 cookies/origin/CSRF behavior is unchanged.

## Layout and verification

- `Valora.Windows.App`: native WinUI lifecycle, read-only machine configuration, origin/session policy and WebView2 event boundary.
- `Valora.Windows.Bridge`: unchanged empty capability catalog; no WIN-3 protocol.
- `Valora.Windows.Tests`: production policy/boundary source compiled into tests, plus a hidden STA WinForms WebView2 host for actual browser-event tests. WinUI-specific lifecycle is compiled by the application build.
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

The WIN-1 entry requires fresh Windows workflow SUCCESS on the exact live main baseline. Before freezing, fetch main, stop on drift, inspect the complete bounded diff, run focused checks and `git diff --check`, and commit a clean candidate. DeepSeek and Gemini independently review the same frozen HEAD. Then create a Draft PR and require repository and Windows CI SUCCESS on that exact SHA. Any HEAD change renews required evidence. Ready/merge belongs to the Gate Owner.
