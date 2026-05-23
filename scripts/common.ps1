$ErrorActionPreference = "Stop"

function Get-ConfiguredValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $envValue = [System.Environment]::GetEnvironmentVariable($Name)
    if ($envValue -and $envValue.Trim()) {
        return $envValue.Trim()
    }

    $envFilePath = Join-Path (Split-Path -Parent $PSScriptRoot) ".env"
    if (-not (Test-Path -LiteralPath $envFilePath)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $envFilePath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $prefix = "$Name="
        if (-not $trimmed.StartsWith($prefix)) {
            continue
        }

        $value = $trimmed.Substring($prefix.Length).Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if ($value) {
            return $value
        }
    }

    return $null
}

function Get-ApiBaseUrl {
    $configured = Get-ConfiguredValue -Name "SDLC_API_BASE_URL"
    if ($configured) {
        return $configured.TrimEnd("/")
    }

    return "http://127.0.0.1:8000"
}

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Write-PrettyJson {
    param(
        [Parameter(Mandatory = $true)]
        $Value
    )

    $Value | ConvertTo-Json -Depth 20
}

function Read-JsonBody {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $path = Join-Path $PSScriptRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "JSON example file not found: $path"
    }

    return Get-Content -LiteralPath $path -Raw
}

function Assert-ApiAvailable {
    $baseUrl = Get-ApiBaseUrl
    $healthUrl = "$baseUrl/health"

    try {
        $null = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 5
    }
    catch {
        throw "API is not reachable at $baseUrl. Start it with ./scripts/run_local.ps1 and try again."
    }
}

function Invoke-JsonGet {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Assert-ApiAvailable
    $baseUrl = Get-ApiBaseUrl
    $url = "$baseUrl$Path"

    try {
        return Invoke-RestMethod -Method Get -Uri $url -Headers @{ Accept = "application/json" }
    }
    catch {
        throw "GET request failed for $url. $($_.Exception.Message)"
    }
}

function Invoke-JsonPost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$JsonBody
    )

    Assert-ApiAvailable
    $baseUrl = Get-ApiBaseUrl
    $url = "$baseUrl$Path"
    $headers = @{ Accept = "application/json" }
    $apiKey = Get-ConfiguredValue -Name "ORCHESTRATOR_API_KEY"
    if ($apiKey) {
        $headers["X-API-Key"] = $apiKey
    }

    try {
        return Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $JsonBody -Headers $headers
    }
    catch {
        throw "POST request failed for $url. $($_.Exception.Message)"
    }
}

function Write-IntakeSummary {
    param(
        [Parameter(Mandatory = $true)]
        $Response
    )

    Write-Host "readiness_score: $($Response.readiness_score)"
    Write-Host "can_continue: $($Response.can_continue)"
    Write-Host "blocking_gaps: $((@($Response.blocking_gaps)) -join '; ')"
    Write-Host "clarification_questions: $((@($Response.clarification_questions)) -join '; ')"
}

function Write-WorkflowSummary {
    param(
        [Parameter(Mandatory = $true)]
        $Response
    )

    Write-Host "run_id: $($Response.run_id)"
    Write-Host "mode: $($Response.mode)"
    Write-Host "status: $($Response.status)"
    Write-Host "readiness_score: $($Response.readiness_score)"
    Write-Host "can_continue: $($Response.can_continue)"
    Write-Host "blocking_gaps: $((@($Response.blocking_gaps)) -join '; ')"
    Write-Host "clarification_questions: $((@($Response.clarification_questions)) -join '; ')"
    Write-Host "steps:"
    foreach ($step in @($Response.steps)) {
        Write-Host "  - $($step.step_name): $($step.status)"
    }
}
