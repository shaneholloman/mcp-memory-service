#Requires -Version 5.1
<#
.SYNOPSIS
    Adds a repeating watchdog trigger to the MCP Memory HTTP Server task.

.DESCRIPTION
    Modifies the scheduled task to run every N minutes, ensuring the server
    automatically restarts if it crashes between logins.

.PARAMETER IntervalMinutes
    How often to check (default: 5 minutes).

.EXAMPLE
    .\add_watchdog_trigger.ps1
    Adds a 5-minute watchdog trigger.

.EXAMPLE
    .\add_watchdog_trigger.ps1 -IntervalMinutes 10
    Adds a 10-minute watchdog trigger.
#>

param(
    [int]$IntervalMinutes = 5
)

$ErrorActionPreference = "Stop"
$TaskName = "MCPMemoryHTTPServer"

Write-Host ""
Write-Host "Adding Watchdog Trigger to $TaskName" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if task exists
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $Task) {
    Write-Host "[ERROR] Task '$TaskName' not found. Run install_scheduled_task.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Current triggers:"
$Task.Triggers | ForEach-Object {
    Write-Host "  - $($_.CimClass.CimClassName)"
}

# Create new repeating trigger
Write-Host ""
Write-Host "[INFO] Adding repeating trigger (every $IntervalMinutes minutes)..." -ForegroundColor Yellow

# Note: RepetitionDuration must be finite but long (9999 days = ~27 years)
$RepetitionTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 9999)

# Get existing triggers and add new one
$ExistingTriggers = @($Task.Triggers)
$AllTriggers = $ExistingTriggers + @($RepetitionTrigger)

# Update task
Set-ScheduledTask -TaskName $TaskName -Trigger $AllTriggers | Out-Null

Write-Host "[SUCCESS] Watchdog trigger added!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  - Check interval: Every $IntervalMinutes minutes"
Write-Host "  - Behavior: If server already running, exits immediately"
Write-Host "  - Behavior: If server not running, starts it"
Write-Host ""

# Show updated triggers
$UpdatedTask = Get-ScheduledTask -TaskName $TaskName
Write-Host "Updated triggers:" -ForegroundColor Cyan
$UpdatedTask.Triggers | ForEach-Object {
    $Type = $_.CimClass.CimClassName -replace 'MSFT_Task', '' -replace 'Trigger', ''
    Write-Host "  - $Type"
}
Write-Host ""
