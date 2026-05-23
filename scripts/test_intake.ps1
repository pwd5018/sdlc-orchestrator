$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Intake Test"
$body = Read-JsonBody -RelativePath "..\examples\intake_only_request.json"
$response = Invoke-JsonPost -Path "/run-intake" -JsonBody $body

Write-IntakeSummary -Response $response
Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
