$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Workflow Test: test_only_request.json"
$body = Read-JsonBody -RelativePath "..\examples\test_only_request.json"
$response = Invoke-JsonPost -Path "/run-sdlc-workflow" -JsonBody $body

Write-WorkflowSummary -Response $response

$requirementsScore = $null
$testDesignScore = $null
$testScenarioCount = 0

foreach ($step in @($response.steps)) {
    if ($step.step_name -eq "requirements" -and $step.output.requirements_readiness_score -ne $null) {
        $requirementsScore = $step.output.requirements_readiness_score
    }
    if ($step.step_name -eq "test_design") {
        if ($step.output.test_design_readiness_score -ne $null) {
            $testDesignScore = $step.output.test_design_readiness_score
        }
        if ($step.output.test_scenarios) {
            $testScenarioCount = @($step.output.test_scenarios).Count
        }
    }
}

Write-Host "requirements_readiness_score: $requirementsScore"
Write-Host "test_design_readiness_score: $testDesignScore"
Write-Host "test_scenario_count: $testScenarioCount"

Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
