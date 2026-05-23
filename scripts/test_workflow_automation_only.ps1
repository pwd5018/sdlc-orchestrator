$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Workflow Test: automation_only_request.json"
$body = Read-JsonBody -RelativePath "..\examples\automation_only_request.json"
$response = Invoke-JsonPost -Path "/run-sdlc-workflow" -JsonBody $body

Write-Host "run_id: $($response.run_id)"
Write-Host "mode: $($response.mode)"
Write-Host "status: $($response.status)"
Write-Host "workflow_readiness_score: $($response.readiness_score)"

$requirementsScore = $null
$testDesignScore = $null
$automationScore = $null
$automationCandidateCount = 0
$flakyRiskCount = 0

foreach ($step in @($response.steps)) {
    switch ($step.step_name) {
        "requirements" {
            $requirementsScore = $step.output.requirements_readiness_score
        }
        "test_design" {
            $testDesignScore = $step.output.test_design_readiness_score
        }
        "automation_design" {
            $automationScore = $step.output.automation_design_readiness_score
            if ($step.output.automation_candidates) {
                $automationCandidateCount = @($step.output.automation_candidates).Count
            }
            if ($step.output.flaky_risk_areas) {
                $flakyRiskCount = @($step.output.flaky_risk_areas).Count
            }
        }
    }
}

Write-Host "requirements_readiness_score: $requirementsScore"
Write-Host "test_design_readiness_score: $testDesignScore"
Write-Host "automation_design_readiness_score: $automationScore"
Write-Host "automation_candidate_count: $automationCandidateCount"
Write-Host "flaky_risk_count: $flakyRiskCount"
Write-Host "step_statuses:"
foreach ($step in @($response.steps)) {
    Write-Host "  - $($step.step_name): $($step.status)"
}

Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
