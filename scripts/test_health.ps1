$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Health Check"
$response = Invoke-JsonGet -Path "/health"
Write-PrettyJson -Value $response | Write-Host
