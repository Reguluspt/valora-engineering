param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Windows client builds require Windows and PowerShell 7.' }

function Invoke-Dotnet {
    param([string[]] $Arguments)
    & dotnet @Arguments
    if ($LASTEXITCODE -ne 0) { throw "dotnet failed with exit code $LASTEXITCODE" }
}

Push-Location $PSScriptRoot
try {
    $expectedSdk = (Get-Content -Raw global.json | ConvertFrom-Json).sdk.version
    if ((& dotnet --version) -ne $expectedSdk) { throw "Install .NET SDK $expectedSdk." }
    $artifactRoot = Join-Path $PSScriptRoot 'artifacts'
    # Only this script's fixed, task-owned output directory is cleaned.
    $resolvedRoot = [IO.Path]::GetFullPath($artifactRoot)
    if ($resolvedRoot -ne [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'artifacts'))) {
        throw 'Unexpected artifact path.'
    }
    if (Test-Path -LiteralPath $resolvedRoot) { Remove-Item -LiteralPath $resolvedRoot -Recurse -Force }
    New-Item -ItemType Directory -Path $resolvedRoot | Out-Null
    Invoke-Dotnet @('restore', 'Valora.Windows.sln', '--locked-mode', '-p:Platform=x64')
    Invoke-Dotnet @('build', 'Valora.Windows.sln', '--no-restore', '-c', 'Release', '-p:Platform=x64')
    Invoke-Dotnet @('test', 'Valora.Windows.Tests/Valora.Windows.Tests.csproj', '--no-build', '--no-restore', '-c', 'Release', '-p:Platform=x64', '--logger', 'trx;LogFileName=windows.trx', '--results-directory', "$resolvedRoot/test-results")
    $appOutput = Join-Path $resolvedRoot 'app'
    Invoke-Dotnet @('publish', 'Valora.Windows.App/Valora.Windows.App.csproj', '--no-build', '--no-restore', '-c', 'Release', '-p:Platform=x64', '-o', $appOutput)

    $exe = Join-Path $appOutput 'Valora.Windows.App.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw 'Missing app executable.' }
    foreach ($resource in @('Valora.Windows.App.pri', 'App.xbf')) {
        if (-not (Test-Path -LiteralPath (Join-Path $appOutput $resource))) {
            throw "Missing application XAML resource: $resource"
        }
    }
    if ((Get-AuthenticodeSignature -LiteralPath $exe).Status -ne 'NotSigned') {
        throw 'Engineering app must be unsigned.'
    }
    & (Join-Path $PSScriptRoot 'Valora.Windows.Tests/native-shell-smoke.ps1') -Executable $exe
    $commit = & git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify source commit.' }
    $files = @(Get-ChildItem -LiteralPath $appOutput -Recurse -File | Sort-Object FullName | ForEach-Object {
        [ordered]@{
            path = [IO.Path]::GetRelativePath($appOutput, $_.FullName).Replace('\', '/')
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
    [ordered]@{
        task = 'VALORA-TASK-WIN-1-WEBVIEW-TRUSTED-NAVIGATION'
        sourceCommit = $commit
        dotnetSdk = $expectedSdk
        target = 'Windows 11 x64'
        distribution = 'unsigned unpackaged engineering evidence only'
        files = $files
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$resolvedRoot/manifest.json" -Encoding utf8NoBOM

    # Stable entry order and timestamps make the archive reproducible for identical app bytes.
    $zipPath = Join-Path $resolvedRoot 'valora-win-x64-unsigned.zip'
    $zip = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($file in $files) {
            $entry = $zip.CreateEntry($file.path, [IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = [DateTimeOffset]::new(1980, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
            $inputStream = [IO.File]::OpenRead((Join-Path $appOutput $file.path))
            $outputStream = $entry.Open()
            try { $inputStream.CopyTo($outputStream) }
            finally { $outputStream.Dispose(); $inputStream.Dispose() }
        }
    }
    finally { $zip.Dispose() }
    (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant() + '  ' + [IO.Path]::GetFileName($zipPath) |
        Set-Content -LiteralPath "$resolvedRoot/SHA256SUMS" -Encoding utf8NoBOM
}
finally { Pop-Location }
