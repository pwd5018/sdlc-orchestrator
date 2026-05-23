$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Workflow Test: qa_review_only_request.json"
$body = Read-JsonBody -RelativePath "..\examples\qa_review_only_request.json"
$response = Invoke-JsonPost -Path "/run-sdlc-workflow" -JsonBody $body

Write-WorkflowSummary -Response $response
Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
