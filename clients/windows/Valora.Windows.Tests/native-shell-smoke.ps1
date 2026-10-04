param([Parameter(Mandatory)][string] $Executable)

$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Valora\WindowsClient') {
    throw 'Native no-configuration smoke requires an unconfigured machine; existing configuration is preserved.'
}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$appProcess = Start-Process -FilePath $Executable -PassThru -WindowStyle Hidden
try {
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    $verified = $false
    do {
        $processCondition = [System.Windows.Automation.PropertyCondition]::new(
            [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $appProcess.Id)
        $window = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst(
            [System.Windows.Automation.TreeScope]::Children, $processCondition)
        if ($null -ne $window) {
            $textCondition = [System.Windows.Automation.PropertyCondition]::new(
                [System.Windows.Automation.AutomationElement]::NameProperty,
                'Chưa cấu hình máy chủ. Liên hệ quản trị viên rồi thử lại.')
            $label = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $textCondition)
            if ($null -ne $label) {
                $retryCondition = [System.Windows.Automation.PropertyCondition]::new(
                    [System.Windows.Automation.AutomationElement]::NameProperty, 'Thử lại')
                $retry = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $retryCondition)
                if ($null -eq $retry -or -not $retry.Current.IsEnabled) { throw 'Retry unavailable.' }
                $retry.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
                $verified = $true
                break
            }
        }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline -and -not $appProcess.HasExited)
    if (-not $verified) { throw 'Published native shell did not reach the Vietnamese no-configuration state.' }
    if (-not $appProcess.CloseMainWindow() -or -not $appProcess.WaitForExit(3000) -or $appProcess.ExitCode -ne 0) {
        throw 'Native window did not close cleanly.'
    }
    Write-Output 'Native shell smoke PASS: published app, Vietnamese no-configuration, Retry, clean closure.'
}
finally {
    if (-not $appProcess.HasExited) { Stop-Process -Id $appProcess.Id }
    $appProcess.Dispose()
}
