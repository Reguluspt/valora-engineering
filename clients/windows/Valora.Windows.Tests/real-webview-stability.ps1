param(
    [ValidateSet('RealWebView', 'All', 'Isolated')] [string] $Scope = 'RealWebView',
    [ValidateRange(1, 100)] [int] $Runs = 1,
    [ValidateRange(0, 32)] [int] $CpuCount = 0,
    [Parameter(Mandatory)] [string] $EvidenceDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Real WebView fixtures require Windows.' }
$evidence = [IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$project = Join-Path $PSScriptRoot 'Valora.Windows.Tests.csproj'
$taskProcess = [Diagnostics.Process]::GetCurrentProcess()
$originalAffinity = $taskProcess.ProcessorAffinity
$originalProcessorCount = $env:DOTNET_PROCESSOR_COUNT
$originalTracePath = $env:VALORA_WEBVIEW_TRACE_PATH
$filters = switch ($Scope) {
    'RealWebView' { 'FullyQualifiedName~WebViewBoundaryTests|FullyQualifiedName~WebViewLifecycleTests|FullyQualifiedName~WebViewNativeBridgeTests' }
    'All' { '' }
    'Isolated' {
        @('FixtureNavigationCannotEscapeTheBoundary', 'ServerHostedLoginAndDeniedResponsesRemainBrowserOwned',
          'LifecycleThreadRevokesBeforeQueuedBrowserContinuation', 'ChildFrameRevokesPreviouslyLoadedNativeCapabilitySurface',
          'ReplacedControlCannotDispatchOrReenableEvenWithSameLoadedOrigin', 'RequestCallbackFailureReachesOwningTest',
          'RebootstrapAfterFormMutationUsesFreshControlAndOnlyRootGet') | ForEach-Object { "FullyQualifiedName~$_" }
    }
}

Push-Location (Split-Path $PSScriptRoot)
try {
    if ($CpuCount -gt 0) {
        $selectedAffinity = 0L
        $selectedCount = 0
        for ($bit = 0; $bit -lt 63 -and $selectedCount -lt $CpuCount; $bit++) {
            $mask = 1L -shl $bit
            if (($originalAffinity.ToInt64() -band $mask) -ne 0) {
                $selectedAffinity = $selectedAffinity -bor $mask
                $selectedCount++
            }
        }
        if ($selectedCount -ne $CpuCount) { throw 'Requested CPU count is unavailable in the process affinity mask.' }
        $taskProcess.ProcessorAffinity = [IntPtr]$selectedAffinity
        # Keep three xUnit workers visible while constraining actual child-process CPU resources.
        $env:DOTNET_PROCESSOR_COUNT = '3'
    }
    [ordered]@{
        sourceCommit = (& git rev-parse HEAD)
        sourceStatus = @(& git status --short)
        scope = $Scope
        runs = $Runs
        cpuCount = $CpuCount
        affinity = $taskProcess.ProcessorAffinity.ToInt64()
        visibleProcessorCount = $env:DOTNET_PROCESSOR_COUNT
        sdk = (& dotnet --version)
        startedUtc = [DateTimeOffset]::UtcNow
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidence 'execution.json') -Encoding utf8NoBOM
    for ($run = 1; $run -le $Runs; $run++) {
        $case = 0
        foreach ($filter in $filters) {
            $case++
            $name = '{0}-{1:D2}-{2:D2}' -f $Scope, $run, $case
            $env:VALORA_WEBVIEW_TRACE_PATH = Join-Path $evidence "$name.jsonl"
            if (Test-Path -LiteralPath $env:VALORA_WEBVIEW_TRACE_PATH) { throw "Evidence already exists: $name" }
            $arguments = @('test', $project, '--no-build', '--no-restore', '-c', 'Release', '-p:Platform=x64',
                '--logger', "trx;LogFileName=$name.trx", '--results-directory', $evidence)
            if ($filter) { $arguments += @('--filter', $filter) }
            & dotnet @arguments *> (Join-Path $evidence "$name.log")
            $exitCode = $LASTEXITCODE
            Get-Content -LiteralPath (Join-Path $evidence "$name.log") | Select-Object -Last 3
            if ($exitCode -ne 0) { throw "Execution failed: $name; exit=$exitCode. Sequence stopped; no retry." }
        }
        Write-Output "Completed consecutive execution $run/$Runs ($Scope)."
    }
}
finally {
    $taskProcess.ProcessorAffinity = $originalAffinity
    $env:DOTNET_PROCESSOR_COUNT = $originalProcessorCount
    $env:VALORA_WEBVIEW_TRACE_PATH = $originalTracePath
    Pop-Location
}
