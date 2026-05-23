$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Auth Test: Missing API Key"
$baseUrl = Get-ApiBaseUrl
$url = "$baseUrl/run-sdlc-workflow"
$body = Read-JsonBody -RelativePath "..\examples\good_feature_request.json"

try {
    $response = Invoke-WebRequest -Method Post -Uri $url -ContentType "application/json" -Body $body -Headers @{ Accept = "application/json" }
    if ($env:ORCHESTRATOR_API_KEY -and $env:ORCHESTRATOR_API_KEY.Trim()) {
        throw "Expected 401 when ORCHESTRATOR_API_KEY is set, but request succeeded with status code $($response.StatusCode)."
    }

    Write-Host "Request succeeded without X-API-Key because ORCHESTRATOR_API_KEY is not configured." -ForegroundColor Green
    Write-Host "Status code: $($response.StatusCode)"
}
catch {
    if ($_.Exception.Response -and $env:ORCHESTRATOR_API_KEY -and $env:ORCHESTRATOR_API_KEY.Trim()) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        if ($statusCode -eq 401) {
            Write-Host "Received expected 401 because ORCHESTRATOR_API_KEY is configured." -ForegroundColor Green
            return
        }
    }

    throw "Auth missing test failed. $($_.Exception.Message)"
}
