$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

Write-Section "Configured Provider Smoke Test"

$provider = if (Get-ConfiguredValue -Name "LLM_PROVIDER") {
    Get-ConfiguredValue -Name "LLM_PROVIDER"
}
else {
    "openai"
}

$model = switch ($provider.ToLowerInvariant()) {
    "groq" {
        if (Get-ConfiguredValue -Name "GROQ_MODEL_NAME") {
            Get-ConfiguredValue -Name "GROQ_MODEL_NAME"
        }
        else {
            "llama-3.1-8b-instant"
        }
        break
    }
    default {
        if (Get-ConfiguredValue -Name "OPENAI_MODEL_NAME") {
            Get-ConfiguredValue -Name "OPENAI_MODEL_NAME"
        }
        else {
            "gpt-4.1-mini"
        }
        break
    }
}

Write-Host "Configured provider: $provider"
Write-Host "Configured model: $model"

$body = Read-JsonBody -RelativePath "..\examples\intake_only_request.json"
Assert-ApiAvailable
$baseUrl = Get-ApiBaseUrl
$url = "$baseUrl/run-intake"

$headers = @{ Accept = "application/json" }
$apiKey = Get-ConfiguredValue -Name "ORCHESTRATOR_API_KEY"
if ($apiKey) {
    $headers["X-API-Key"] = $apiKey
}

try {
    $response = Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $body -Headers $headers
}
catch {
    throw "Configured provider test failed. Check that the API is running with the same environment configuration. $($_.Exception.Message)"
}

Write-IntakeSummary -Response $response
Write-Section "Full Response"
Write-PrettyJson -Value $response | Write-Host
