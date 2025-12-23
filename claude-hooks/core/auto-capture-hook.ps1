<#
.SYNOPSIS
    Claude Code Auto-Capture Hook (PowerShell Version)

.DESCRIPTION
    Automatically captures valuable conversation content after tool operations.
    Uses pattern detection to identify decisions, errors, learnings, and implementations.

    Trigger: PostToolUse (Edit, Write, Bash)
    Input: JSON via stdin with transcript_path and tool info

.NOTES
    File Name      : auto-capture-hook.ps1
    Version        : 1.0.0
    Platform       : Windows
#>

param(
    [switch]$Debug
)

$ErrorActionPreference = "SilentlyContinue"

#region Configuration

$DEFAULT_ENDPOINT = "http://127.0.0.1:8000"
$DEFAULT_MIN_LENGTH = 300
$DEFAULT_MAX_LENGTH = 4000
$TIMEOUT_SECONDS = 5

#endregion

#region Pattern Definitions

$Patterns = @{
    "Decision" = @{
        Regex = "(decided|chose|will use|let's go with|i'll use|we'll use|settled on|going with|picked|selected|opting for|entschieden|gewählt|nehmen wir|verwenden wir|machen wir|nutzen wir|ausgewählt)"
        MemoryType = "Decision"
        Priority = 1
        Confidence = 0.9
    }
    "Error" = @{
        Regex = "(error|exception|failed|fixed|bug|issue|crash|broken|resolved|solved|debugging|debugged|patched|fehler|behoben|gefixt|problem|kaputt|gelöst|repariert|fehlerbehebung)"
        MemoryType = "Error"
        Priority = 2
        Confidence = 0.85
    }
    "Learning" = @{
        Regex = "(learned|discovered|realized|found out|turns out|interestingly|til|understanding now|now i see|aha|insight|gelernt|entdeckt|herausgefunden|stellte sich heraus|interessanterweise|jetzt verstehe ich)"
        MemoryType = "Learning"
        Priority = 3
        Confidence = 0.85
    }
    "Implementation" = @{
        Regex = "(implemented|created|built|added|refactored|set up|configured|deployed|developed|wrote|coding|programmed|implementiert|erstellt|gebaut|hinzugefügt|konfiguriert|eingerichtet|refaktoriert|entwickelt|programmiert)"
        MemoryType = "Learning"
        Priority = 4
        Confidence = 0.8
    }
    "Important" = @{
        Regex = "(critical|important|remember|note|key|essential|must|never|always|crucial|vital|significant|wichtig|merken|notiz|niemals|immer|kritisch|wesentlich|unbedingt|entscheidend)"
        MemoryType = "Context"
        Priority = 5
        Confidence = 0.75
    }
    "Code" = @{
        Regex = "(function|class|component|api|endpoint|database|schema|test|config|module|interface|method|funktion|klasse|komponente|datenbank|schnittstelle|konfiguration|modul)"
        MemoryType = "Context"
        Priority = 6
        Confidence = 0.7
        MinLength = 600
    }
}

$UserOverrides = @{
    ForceRemember = "#remember"
    ForceSkip = "#skip"
}

#endregion

#region Functions

function Write-DebugLog {
    param([string]$Message)
    if ($Debug) {
        Write-Host "[auto-capture] $Message" -ForegroundColor Cyan
    }
}

function Get-HookConfig {
    $configPath = Join-Path $PSScriptRoot "..\config.json"

    if (Test-Path $configPath) {
        try {
            $config = Get-Content $configPath -Raw | ConvertFrom-Json
            return @{
                Endpoint = if ($config.memoryService.http.endpoint) { $config.memoryService.http.endpoint } else { $DEFAULT_ENDPOINT }
                ApiKey = $config.memoryService.http.apiKey
                MinLength = if ($config.autoCapture.minLength) { $config.autoCapture.minLength } else { $DEFAULT_MIN_LENGTH }
                MaxLength = if ($config.autoCapture.maxLength) { $config.autoCapture.maxLength } else { $DEFAULT_MAX_LENGTH }
                Enabled = if ($null -ne $config.autoCapture.enabled) { $config.autoCapture.enabled } else { $true }
                DebugMode = if ($config.autoCapture.debugMode) { $config.autoCapture.debugMode } else { $false }
            }
        } catch {
            Write-DebugLog "Failed to load config: $_"
        }
    }

    return @{
        Endpoint = $DEFAULT_ENDPOINT
        ApiKey = ""
        MinLength = $DEFAULT_MIN_LENGTH
        MaxLength = $DEFAULT_MAX_LENGTH
        Enabled = $true
        DebugMode = $false
    }
}

function Get-TranscriptContent {
    param([string]$TranscriptPath)

    if (-not (Test-Path $TranscriptPath)) {
        Write-DebugLog "Transcript not found: $TranscriptPath"
        return $null
    }

    try {
        $transcript = Get-Content $TranscriptPath -Raw | ConvertFrom-Json

        $lastUser = ""
        $lastAssistant = ""

        for ($i = $transcript.Count - 1; $i -ge 0; $i--) {
            $msg = $transcript[$i]
            $role = if ($msg.role) { $msg.role } else { $msg.type }

            if (-not $lastAssistant -and $role -eq "assistant") {
                $lastAssistant = Get-TextContent $msg.content
            }
            if (-not $lastUser -and $role -eq "user") {
                $lastUser = Get-TextContent $msg.content
            }

            if ($lastUser -and $lastAssistant) { break }
        }

        return @{
            UserMessage = $lastUser
            AssistantMessage = $lastAssistant
            Combined = "User: $lastUser`n`nAssistant: $lastAssistant"
        }
    } catch {
        Write-DebugLog "Failed to parse transcript: $_"
        return $null
    }
}

function Get-TextContent {
    param($Content)

    if ($Content -is [string]) {
        return $Content
    }

    if ($Content -is [array]) {
        $texts = $Content | Where-Object { $_.type -eq "text" } | ForEach-Object { $_.text }
        return $texts -join "`n"
    }

    return ""
}

function Test-UserOverride {
    param([string]$UserMessage)

    return @{
        ForceRemember = $UserMessage -match $UserOverrides.ForceRemember
        ForceSkip = $UserMessage -match $UserOverrides.ForceSkip
    }
}

function Find-Pattern {
    param(
        [string]$Content,
        [int]$MinLength
    )

    if ($Content.Length -lt $MinLength) {
        return @{
            IsValuable = $false
            Reason = "Content too short ($($Content.Length) < $MinLength chars)"
        }
    }

    $contentLower = $Content.ToLower()

    # Sort patterns by priority
    $sortedPatterns = $Patterns.GetEnumerator() | Sort-Object { $_.Value.Priority }

    foreach ($pattern in $sortedPatterns) {
        $patternDef = $pattern.Value

        # Check minimum length for this pattern
        if ($patternDef.MinLength -and $Content.Length -lt $patternDef.MinLength) {
            continue
        }

        if ($contentLower -match $patternDef.Regex) {
            Write-DebugLog "Matched pattern: $($pattern.Key)"
            return @{
                IsValuable = $true
                MemoryType = $patternDef.MemoryType
                MatchedPattern = $pattern.Key
                Confidence = $patternDef.Confidence
            }
        }
    }

    return @{
        IsValuable = $false
        Reason = "No pattern matched"
    }
}

function Get-ProjectName {
    param([string]$Cwd)

    if (-not $Cwd) { return $null }

    $parts = $Cwd -split "[/\\]" | Where-Object { $_ }
    $lastPart = $parts[-1]

    $skipDirs = @("home", "users", "documents", "desktop", "repositories", "projects", "src")
    if ($skipDirs -contains $lastPart.ToLower()) {
        return if ($parts.Count -gt 1) { $parts[-2] } else { $null }
    }

    return $lastPart
}

function Get-AutoTags {
    param(
        [hashtable]$Detection,
        [string]$ProjectName
    )

    $tags = @("auto-captured", "smart-ingest")

    if ($Detection.MemoryType) {
        $tags += $Detection.MemoryType.ToLower()
    }

    if ($Detection.MatchedPattern) {
        $tags += $Detection.MatchedPattern.ToLower()
    }

    if ($ProjectName) {
        $tags += $ProjectName
    }

    return $tags
}

function Limit-Content {
    param(
        [string]$Content,
        [int]$MaxLength
    )

    if ($Content.Length -le $MaxLength) {
        return $Content
    }

    $truncated = $Content.Substring(0, $MaxLength)
    $lastSentence = $truncated.LastIndexOf(". ")

    if ($lastSentence -gt ($MaxLength * 0.8)) {
        return $truncated.Substring(0, $lastSentence + 1) + "`n[truncated]"
    }

    return $truncated + "`n[truncated]"
}

function Send-Memory {
    param(
        [hashtable]$Config,
        [string]$Content,
        [string]$MemoryType,
        [string[]]$Tags
    )

    $uri = "$($Config.Endpoint)/api/memories"

    $body = @{
        content = $Content
        memory_type = $MemoryType
        tags = $Tags
        metadata = @{
            source = "auto-capture"
            hook = "PostToolUse"
            captured_at = (Get-Date).ToString("o")
        }
    } | ConvertTo-Json -Depth 3

    $headers = @{
        "Content-Type" = "application/json"
    }

    if ($Config.ApiKey) {
        $headers["X-API-Key"] = $Config.ApiKey
    }

    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -Body $body -Headers $headers -TimeoutSec $TIMEOUT_SECONDS
        return $response
    } catch {
        Write-DebugLog "Failed to store memory: $_"
        return $null
    }
}

#endregion

#region Main Execution

$startTime = Get-Date

try {
    # Load configuration
    $config = Get-HookConfig
    $Debug = $Debug -or $config.DebugMode

    if (-not $config.Enabled) {
        Write-DebugLog "Auto-capture disabled in configuration"
        exit 0
    }

    # Read stdin
    $stdinData = ""
    if ([Console]::In.Peek() -ne -1) {
        $stdinData = [Console]::In.ReadToEnd()
    }

    if (-not $stdinData) {
        Write-DebugLog "No stdin input"
        exit 0
    }

    try {
        $input = $stdinData | ConvertFrom-Json
    } catch {
        Write-DebugLog "Invalid JSON input"
        exit 0
    }

    $transcriptPath = if ($input.transcript_path) { $input.transcript_path } else { $input.transcriptPath }
    $cwd = if ($input.cwd) { $input.cwd } else { (Get-Location).Path }

    if (-not $transcriptPath) {
        Write-DebugLog "No transcript path provided"
        exit 0
    }

    # Parse transcript
    $transcript = Get-TranscriptContent -TranscriptPath $transcriptPath
    if (-not $transcript) {
        exit 0
    }

    # Check user overrides
    $overrides = Test-UserOverride -UserMessage $transcript.UserMessage

    if ($overrides.ForceSkip) {
        Write-DebugLog "Skipped by user override (#skip)"
        exit 0
    }

    $content = $transcript.Combined

    # Detect patterns
    if ($overrides.ForceRemember) {
        $detection = @{
            IsValuable = $true
            MemoryType = "Context"
            MatchedPattern = "user-override"
            Confidence = 1.0
        }
        Write-DebugLog "Force remember by user override (#remember)"
    } else {
        $detection = Find-Pattern -Content $content -MinLength $config.MinLength
    }

    if (-not $detection.IsValuable) {
        Write-DebugLog "Not valuable: $($detection.Reason)"
        exit 0
    }

    # Prepare and store
    $truncatedContent = Limit-Content -Content $content -MaxLength $config.MaxLength
    $projectName = Get-ProjectName -Cwd $cwd
    $tags = Get-AutoTags -Detection $detection -ProjectName $projectName

    Write-DebugLog "Storing $($detection.MemoryType) memory..."
    Write-DebugLog "Pattern: $($detection.MatchedPattern)"
    Write-DebugLog "Tags: $($tags -join ', ')"

    $result = Send-Memory -Config $config -Content $truncatedContent -MemoryType $detection.MemoryType -Tags $tags

    $elapsed = ((Get-Date) - $startTime).TotalMilliseconds

    if ($result) {
        Write-DebugLog "Stored successfully in ${elapsed}ms"
    }

    exit 0

} catch {
    $elapsed = ((Get-Date) - $startTime).TotalMilliseconds
    Write-Host "[auto-capture] Error after ${elapsed}ms: $_" -ForegroundColor Red
    exit 0
}

#endregion
