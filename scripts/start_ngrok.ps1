$ErrorActionPreference = "Stop"

Write-Host "Starting ngrok for local SDLC Orchestrator API on port 8000..." -ForegroundColor Green
Write-Host "After ngrok starts, copy the HTTPS forwarding URL."
Write-Host "Set PUBLIC_BASE_URL to that HTTPS URL, restart the API, and then use /openapi-action.yaml in your Custom GPT Action."

ngrok http 8000
