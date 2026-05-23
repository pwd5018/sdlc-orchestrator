$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

function Write-MatchNames {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        $Items
    )

    $names = @($Items | ForEach-Object { $_.name })
    Write-Host "${Label}: $($names -join '; ')"
}

Write-Section "Context Retrieval Test: context_document_upload_request.json"
$body = Read-JsonBody -RelativePath "..\examples\context_document_upload_request.json"
$response = Invoke-JsonPost -Path "/retrieve-context" -JsonBody $body

Write-Host "retrieval_confidence: $($response.retrieval_confidence)"
Write-MatchNames -Label "matched_features" -Items $response.matched_features
Write-MatchNames -Label "matched_api_endpoints" -Items $response.matched_api_endpoints
Write-MatchNames -Label "matched_ui_screens" -Items $response.matched_ui_screens
Write-MatchNames -Label "matched_database_tables" -Items $response.matched_database_tables
Write-MatchNames -Label "matched_automation_tests" -Items $response.matched_automation_tests
Write-MatchNames -Label "matched_known_defects" -Items $response.matched_known_defects

Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
