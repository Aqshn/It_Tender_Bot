$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$pythonExe = "C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe"
$monitorScript = Join-Path $scriptDir "etender_it_telegram_monitor.py"
$envFile = Join-Path $scriptDir "etender_monitor.env"
$logDir = Join-Path $scriptDir "logs"
$logFile = Join-Path $logDir "etender_monitor.log"

if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $name = $parts[0].Trim()
            $value = $parts[1].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

if ([string]::IsNullOrWhiteSpace($env:TELEGRAM_BOT_TOKEN) -or $env:TELEGRAM_BOT_TOKEN -eq "your_bot_token_here" -or
    [string]::IsNullOrWhiteSpace($env:TELEGRAM_CHAT_ID) -or $env:TELEGRAM_CHAT_ID -eq "your_chat_id_here") {
    throw "Missing Telegram config. Fill parcer/etender_monitor.env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, then rerun."
}

Push-Location $projectRoot
try {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$timestamp] Run started"

    $stdoutFile = Join-Path $logDir "etender_monitor.stdout.log"
    $stderrFile = Join-Path $logDir "etender_monitor.stderr.log"
    if (Test-Path $stdoutFile) { Remove-Item $stdoutFile -Force }
    if (Test-Path $stderrFile) { Remove-Item $stderrFile -Force }

    $argumentString = "`"$monitorScript`" --once --pages 3"
    $process = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList $argumentString `
        -WorkingDirectory $projectRoot `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdoutFile `
        -RedirectStandardError $stderrFile

    if (Test-Path $stdoutFile) {
        Get-Content $stdoutFile -Encoding UTF8 | Tee-Object -FilePath $logFile -Append
    }
    if (Test-Path $stderrFile) {
        Get-Content $stderrFile -Encoding UTF8 | Tee-Object -FilePath $logFile -Append
    }

    if ($process.ExitCode -ne 0) {
        throw "Monitor exited with code $($process.ExitCode)."
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$timestamp] Run finished"
}
finally {
    Pop-Location
}
