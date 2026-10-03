# WIN-0 Windows client foundation

Scope: [Issue #100](https://github.com/Reguluspt/valora-engineering/issues/100), based on main `fb0c5449b13b91934356975564959129abdfe97c`, CODEX blob `31dd96a11148f42a28ae0adbaa825cd0c944435d` and exact-main CI #567. [ADR 0050](../../docs/adr/0050-linux-server-windows-native-client.md) and the [Windows plan](../../docs/plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md) govern the foundation. This is engineering evidence, not Preview/UAT or production distribution.

## Layout and boundaries

- `Valora.Windows.sln`: Debug/Release x64 only.
- `Valora.Windows.App`: WinUI 3 application/window lifecycle and an unconfigured WebView2 control. Minimal App XAML supplies the generated entry point, type metadata and resource index; window controls are programmatic. No Source, CoreWebView2 initialization, script injection, message handling or host objects.
- `Valora.Windows.Bridge`: `INativeCapabilityCatalog` plus an immutable empty foundation catalog. No dispatch, IO, credentials or business semantics; no WIN-3 protocol is frozen here.
- `Valora.Windows.Tests`: Windows x64 tests enforce the empty native capability surface and bridge dependency separation. They do not certify navigation, authentication or a product journey.
- `build.ps1`: locked restore, solution build, Windows tests, self-contained unpackaged publish, unsigned-app check, file hashes and deterministic ZIP entry order/timestamps.
- [Windows CI](../../.github/workflows/windows-client.yml): fresh Windows runner, same script, exact PR head checkout, artifact and TRX upload. Existing repository CI gains this task branch's push trigger so the frozen HEAD can pass all existing jobs before Draft PR creation.

Linux owns authentication/session, tenant/RBAC, domain validation/commands, Case State, audit/CAS, documents and jobs. React remains server-hosted. No backend, database, worker, object store, React build, AI/ML package, local inference runtime or model weights are included. No provider activation, signing material, LAN discovery or ASSET_WORKBENCH+ authorization is added. An administrator-configured HTTPS URL, protected configuration, trust/navigation/certificate UX belong to WIN-1; this foundation accepts no URL. MSIX identity/install/update/signing belong to WIN-5.

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

## Engineering artifact and reproducibility

`artifacts/valora-win0-win-x64-unsigned.zip` contains the App, Bridge and required .NET/Windows App SDK native runtime files. Extract all files together on a serviced Windows 11 x64 machine. `Valora.Windows.App.exe` is unsigned; vendor runtime binaries may retain Microsoft signatures. The shell shows a Vietnamese foundation label and blank WebView2 area; it cannot connect to Valora. Evergreen WebView2 is required for later initialization, which this task does not perform.

`manifest.json` binds the Git source commit, exact SDK, target and SHA-256 of every application file. `SHA256SUMS` identifies the ZIP; TRX records test results. CI uploads these plus lockfiles, with 14-day retention. There is no signing certificate, signing secret, MSIX installer or distribution/update promise.

Managed compilation uses deterministic output and a normalized source path. Archive ordering and timestamps are fixed. To verify repeatability, run the script twice at the same clean HEAD with the pinned SDK and compare `SHA256SUMS` and manifest file hashes. ZIP bytes are guaranteed only for identical published bytes and compression tooling; Windows runner image servicing and Evergreen updates remain external variables. Fresh-checkout restore/build/test is the required reproducible engineering procedure, not a production release certification.

## Execution and candidate gates

1. Verify certified baseline and all named authority before creating the task worktree.
2. Create App/Bridge/Tests, lock stable dependencies and test the native capability boundary.
3. Run focused Windows restore/build/test/publish and inspect artifact contents/signature; verify a fresh source checkout and repeat hashes.
4. Review every changed path against Issue #100; fetch again before candidate freeze and stop for Gate Owner on baseline drift.
5. Commit one candidate, verify clean worktree and `git diff --check`, obtain read-only independent review on that HEAD, and require exact-head Windows and repository CI. Create only a Draft PR; Ready/merge remains Gate Owner work. A changed HEAD invalidates review/CI.
