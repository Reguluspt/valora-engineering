[CmdletBinding()]
param(
    [string]$Executable = 'codex',
    [string[]]$LaunchArguments = @(),
    [switch]$CheckOnly
)

# Scope lifecycle switches to this process and its child, preserving MCP credentials.
$settings = @{
    OPENVIKING_MEMORY_ENABLED = '0'
    OPENVIKING_AUTO_RECALL = '0'
    OPENVIKING_AUTO_CAPTURE = '0'
    OPENVIKING_AUTO_COMMIT_ON_COMPACT = '0'
    OPENVIKING_NO_AUTO_INJECT = '1'
    OPENVIKING_RESUME_ARCHIVE_INJECT = '0'
    OPENVIKING_SKILL_CATALOG = '0'
    OPENVIKING_RECALL_COMPRESS_DETECT_ON_STARTUP = '0'
}
$saved = @{}
try {
    foreach ($key in $settings.Keys) {
        $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }
    if ($CheckOnly) {
        $settings.GetEnumerator() | Sort-Object Key | ForEach-Object { '{0}={1}' -f $_.Key, $_.Value }
    } else {
        & $Executable @LaunchArguments
        if ($LASTEXITCODE) { throw "Codex launch exited with code $LASTEXITCODE" }
    }
} finally {
    foreach ($key in $saved.Keys) {
        if ($null -eq $saved[$key]) {
            Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue
        } else {
            [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process')
        }
    }
}
