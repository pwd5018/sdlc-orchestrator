$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Workflow Test: weak_feature_request.json"
$body = Read-JsonBody -RelativePath "..\examples\weak_feature_request.json"
$response = Invoke-JsonPost -Path "/run-sdlc-workflow" -JsonBody $body

if ($response.status -ne "blocked") {
    throw "Expected weak workflow request to return status='blocked', but got '$($response.status)'."
}

Write-Host "Blocked workflow returned as expected." -ForegroundColor Green
if ($response.user_safe_message) {
    Write-Host "user_safe_message: $($response.user_safe_message)"
}

Write-WorkflowSummary -Response $response
Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
