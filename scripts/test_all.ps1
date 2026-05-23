$ErrorActionPreference = "Stop"

$scriptPaths = @(
    "test_health.ps1",
    "test_intake.ps1",
    "test_workflow_good.ps1",
    "test_workflow_weak.ps1",
    "test_workflow_story_only.ps1",
    "test_workflow_test_only.ps1",
    # Milestone 7 automation-design smoke test
    "test_workflow_automation_only.ps1",
    # Milestone 8 full dev-handoff smoke test
    "test_workflow_full_dev_handoff.ps1",
    "test_workflow_qa_review_only.ps1"
)

foreach ($scriptName in $scriptPaths) {
    Write-Host ""
    Write-Host "Running $scriptName" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot $scriptName)
}

$policySpherePath = Get-ConfiguredValue -Name "POLICYSPHERE_LAB_PATH"
if ($policySpherePath) {
    $contextScripts = @(
        "test_context_email_resend.ps1",
        "test_context_policy_comparison.ps1",
        "test_context_document_upload.ps1"
    )

    foreach ($scriptName in $contextScripts) {
        Write-Host ""
        Write-Host "Running $scriptName" -ForegroundColor Yellow
        & (Join-Path $PSScriptRoot $scriptName)
    }
}
else {
    Write-Host ""
    Write-Host "Skipping context retrieval smoke tests because POLICYSPHERE_LAB_PATH is not configured." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "All local smoke tests passed." -ForegroundColor Green
