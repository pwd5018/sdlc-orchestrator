$ErrorActionPreference = "Stop"

$baseUrl = if ($env:SDLC_API_BASE_URL -and $env:SDLC_API_BASE_URL.Trim()) {
    $env:SDLC_API_BASE_URL.Trim()
}
else {
    "http://127.0.0.1:8000"
}

Write-Host "Starting SDLC Orchestrator locally..." -ForegroundColor Green
Write-Host "API URL: $baseUrl"
Write-Host "Docs URL: $baseUrl/docs"
Write-Host "Press Ctrl+C to stop."

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
