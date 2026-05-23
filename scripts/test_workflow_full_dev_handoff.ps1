$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Workflow Test: full_dev_handoff_request.json"
$body = Read-JsonBody -RelativePath "..\examples\full_dev_handoff_request.json"
$response = Invoke-JsonPost -Path "/run-sdlc-workflow" -JsonBody $body

Write-Host "run_id: $($response.run_id)"
Write-Host "mode: $($response.mode)"
Write-Host "status: $($response.status)"
Write-Host "workflow_readiness_score: $($response.readiness_score)"

$requirementsScore = $null
$storyScore = $null
$testDesignScore = $null
$automationScore = $null
$devHandoffScore = $null
$developerTaskCount = 0
$uiImpactCount = 0
$apiImpactCount = 0
$dataImpactCount = 0

foreach ($step in @($response.steps)) {
    switch ($step.step_name) {
        "requirements" {
            $requirementsScore = $step.output.requirements_readiness_score
        }
        "jira_story" {
            $storyScore = $step.output.story_readiness_score
        }
        "test_design" {
            $testDesignScore = $step.output.test_design_readiness_score
        }
        "automation_design" {
            $automationScore = $step.output.automation_design_readiness_score
        }
        "dev_handoff" {
            $devHandoffScore = $step.output.handoff_readiness_score
            if ($step.output.developer_tasks) {
                $developerTaskCount = @($step.output.developer_tasks).Count
            }
            if ($step.output.ui_impacts) {
                $uiImpactCount = @($step.output.ui_impacts).Count
            }
            if ($step.output.api_impacts) {
                $apiImpactCount = @($step.output.api_impacts).Count
            }
            if ($step.output.data_model_impacts) {
                $dataImpactCount = @($step.output.data_model_impacts).Count
            }
        }
    }
}

Write-Host "requirements_readiness_score: $requirementsScore"
Write-Host "story_readiness_score: $storyScore"
Write-Host "test_design_readiness_score: $testDesignScore"
Write-Host "automation_design_readiness_score: $automationScore"
Write-Host "handoff_readiness_score: $devHandoffScore"
Write-Host "developer_task_count: $developerTaskCount"
Write-Host "ui_impact_count: $uiImpactCount"
Write-Host "api_impact_count: $apiImpactCount"
Write-Host "data_impact_count: $dataImpactCount"
Write-Host "step_statuses:"
foreach ($step in @($response.steps)) {
    Write-Host "  - $($step.step_name): $($step.status)"
}

Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
