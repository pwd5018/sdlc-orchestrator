$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Auth Test: Valid API Key"

if (-not $env:ORCHESTRATOR_API_KEY -or -not $env:ORCHESTRATOR_API_KEY.Trim()) {
    throw "ORCHESTRATOR_API_KEY must be set in the environment to run test_auth_success.ps1."
}

Assert-ApiAvailable
$baseUrl = Get-ApiBaseUrl
$url = "$baseUrl/run-sdlc-workflow"
$body = Read-JsonBody -RelativePath "..\examples\good_feature_request.json"

try {
    $response = Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $body -Headers @{
        Accept = "application/json"
        "X-API-Key" = $env:ORCHESTRATOR_API_KEY
    }
}
catch {
    throw "Authenticated workflow request failed. $($_.Exception.Message)"
}

Write-WorkflowSummary -Response $response
Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
