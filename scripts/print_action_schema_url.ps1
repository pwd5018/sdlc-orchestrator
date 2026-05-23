$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

$baseUrl = Get-ApiBaseUrl

Write-Section "Custom GPT Action URLs"
Write-Host "$baseUrl/openapi-action.yaml"
Write-Host "$baseUrl/docs"
Write-Host "$baseUrl/health"
