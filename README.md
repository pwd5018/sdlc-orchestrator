# SDLC Orchestrator

## Milestone 1: Feature Intake Packet

Milestone 1 defines the master intake structure that downstream SDLC workflows will consume. This repository currently includes the packet design, a JSON Schema, readiness scoring guidance, and an example packet in [docs](/C:/Users/wolf-ai/Workspace/sdlc-orchestrator/docs).

This milestone is intentionally documentation-focused. It does not yet implement backend services, external integrations, authentication, persistence, or OpenAI API usage.

## Milestone 2: Intake Agent MVP

Milestone 2 adds a small FastAPI-based Intake Agent that analyzes a raw feature request and returns:

- a structured Feature Intake Packet
- a readiness score
- blocking gaps
- prioritized clarification questions
- safe and unsafe downstream generation boundaries

This milestone remains intentionally narrow. It does not include Jira, GitLab, Teams, authentication, persistence, downstream agents, or orchestration workflows.

## Provider Abstraction

The Intake Agent now uses a provider-agnostic LLM layer. The public API stays the same:

- `GET /health`
- `POST /run-intake`

The Intake Agent does not call OpenAI directly anymore. It selects an LLM provider from configuration and uses the same JSON generation and repair flow through that abstraction layer.

## Project Structure

```text
app/
  main.py
  config.py
  models/
    intake_models.py
  services/
    intake_service.py
    prompt_loader.py
    llm/
      base_provider.py
      provider_factory.py
      openai_provider.py
      groq_provider.py
prompts/
  intake_agent.md
docs/
README.md
.env.example
requirements.txt
```

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Copy the example environment file and add your API key:

```powershell
Copy-Item .env.example .env
```

Set:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL_NAME=gpt-4.1-mini
GROQ_API_KEY=
GROQ_MODEL_NAME=llama-3.1-8b-instant
```

## Provider Selection

Select the model provider with `LLM_PROVIDER`.

- `openai`
- `groq`

If an unsupported provider is configured, the app raises a clear configuration error at request time.

### OpenAI example

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL_NAME=gpt-4.1-mini
GROQ_API_KEY=
GROQ_MODEL_NAME=llama-3.1-8b-instant
```

### Groq example

```env
LLM_PROVIDER=groq
OPENAI_API_KEY=
OPENAI_MODEL_NAME=gpt-4.1-mini
GROQ_API_KEY=your_groq_key
GROQ_MODEL_NAME=llama-3.1-8b-instant
```

### Example .env setups

Use `.env.example` as the starting template, then fill only the key for the provider you want to use.

## Run Locally

Start the FastAPI app with:

```powershell
python -m uvicorn app.main:app --reload
```

The service exposes:

- `GET /health`
- `POST /run-intake`

## Curl Example

```bash
curl -X POST "http://127.0.0.1:8000/run-intake" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_description": "We need a way for project managers to export a filtered release readiness summary to CSV instead of copying the data manually.",
    "context": {
      "product_area": "release reporting"
    },
    "attachments": [],
    "notes": [
      "Security may care about export permissions.",
      "A previous request asked for PDF too, but that is not part of this feature."
    ]
  }'
```

## Readiness Scoring

The Intake Agent extracts structured fields, identifies uncertainty, and scores readiness from `0` to `100`.

- `90-100`: full SDLC generation is considered safe
- `70-89`: draft generation is safe if assumptions remain clearly marked
- `50-69`: only discovery output and clarification questions are safe
- `0-49`: the workflow should stop and request better input

The service keeps the threshold behavior deterministic in code, while the model focuses on requirement extraction and gap detection.

## Clarification Questions

Clarification questions are generated only for high-value missing information.

- questions should target blocking gaps first
- duplicates are removed before the response is returned
- the list is kept focused on information that materially improves readiness

## JSON Reliability

The Intake Agent prompt requires valid JSON output only. The service then validates the model response with Pydantic.

- if the first response is invalid, the service retries once with a repair prompt
- repair attempts are logged cleanly
- if repair still fails, the request returns an error instead of passing along broken structure

The repair flow uses the same selected provider, so OpenAI and Groq follow the same external behavior.

## Milestone 3: FastAPI Workflow Shell

Milestone 3 adds a backend workflow shell for SDLC orchestration. It always runs the Intake Agent first, then either blocks the workflow for clarification or continues through placeholder downstream steps based on the selected workflow mode.

This milestone is intentionally orchestration-focused. Downstream agents such as requirements generation, Jira story generation, test design, automation design, dev handoff, and QA review are placeholders only for now.

## Workflow Modes

Supported workflow modes:

- `full`
- `story_only`
- `test_only`
- `automation_only`
- `qa_review_only`

## Workflow Endpoint

The public API now exposes:

- `GET /health`
- `POST /run-intake`
- `POST /run-sdlc-workflow`

### Workflow curl example

```bash
curl -X POST "http://127.0.0.1:8000/run-sdlc-workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_description": "We need a way for project managers to export a filtered release readiness summary to CSV instead of copying the data manually.",
    "mode": "full",
    "context": {
      "product_area": "release reporting"
    },
    "attachments": [],
    "notes": [
      "Security may care about export permissions."
    ]
  }'
```

## Blocked Workflow Behavior

The workflow shell always runs intake first.

- if `readiness_score < 70`, the workflow stops immediately
- the response status is `blocked`
- clarification questions are returned
- downstream placeholder steps are not executed

If `readiness_score >= 70`, the workflow continues through the mode-specific placeholder steps and returns a `completed` status.

## Placeholder Downstream Steps

For now, downstream steps are shell-only placeholders:

- `requirements`
- `jira_story`
- `test_design`
- `automation_design`
- `dev_handoff`
- `qa_review`
- `finalizer`

Each placeholder returns the same shape:

```json
{
  "message": "Placeholder only. Real agent will be implemented in a future milestone.",
  "received_previous_outputs": true
}
```

## Local Smoke Testing

Use the sample request payloads in [examples](/C:/Users/wolf-ai/Workspace/sdlc-orchestrator/examples) and the Windows-friendly PowerShell scripts in [scripts](/C:/Users/wolf-ai/Workspace/sdlc-orchestrator/scripts) to validate the API locally before continuing.

Start the API:

```powershell
./scripts/run_local.ps1
```

Run one test:

```powershell
./scripts/test_workflow_good.ps1
```

Run all tests:

```powershell
./scripts/test_all.ps1
```

Override the base URL:

```powershell
$env:SDLC_API_BASE_URL="http://127.0.0.1:8000"
```

Behavior notes:

- `good_feature_request.json` is intentionally detailed and should usually drive readiness high enough for the workflow shell to continue into placeholder downstream steps.
- `weak_feature_request.json` is intentionally vague and is meant to exercise blocked workflow behavior with clarification questions.
- `intake_only_request.json` matches the `/run-intake` request shape, while the other example files match `/run-sdlc-workflow`.

## Milestone 4: Real Requirements Agent

Milestone 4 replaces the placeholder `requirements` step with a real AI-powered Requirements Agent.

What it does:

- consumes the original feature description
- consumes the Feature Intake Packet from the Intake Agent
- consumes previous workflow outputs
- produces structured functional, non-functional, business rule, data, integration, and role/permission requirements
- separates provided facts from inferred assumptions
- surfaces risks and open questions
- assigns a `requirements_readiness_score`

What it does not do:

- it does not generate Jira stories
- it does not generate test cases
- it does not generate automation code
- it does not replace the later agents yet

Requirements readiness scoring:

- `90-100`: strong enough for Jira story generation, test design, and automation planning
- `70-89`: good enough for draft downstream generation with assumptions clearly marked
- `50-69`: only draft requirements and questions are safe
- `0-49`: downstream story/test/automation generation should be blocked

Workflow behavior:

- the real Requirements Agent runs in modes that include `requirements`
- if requirements readiness falls below `70`, downstream story/test/automation placeholder steps are blocked or skipped
- later agents are still placeholders in this milestone

Example smoke test command:

```powershell
./scripts/test_workflow_good.ps1
```

## Milestone 5: Real Jira Story Agent

Milestone 5 replaces the placeholder `jira_story` step with a real AI-powered Jira Story Agent.

What it does:

- consumes the original feature description
- consumes the Feature Intake Packet from the Intake Agent
- consumes the Requirements Agent output
- produces a Jira-ready story package with summary, description, user story, dependencies, labels, components, out-of-scope items, and readiness metadata
- clearly separates assumptions and open questions from grounded story facts
- creates acceptance criteria only when the requirements are strong enough to support them

What it does not do:

- it does not integrate with Jira yet
- it does not create Jira tickets
- it does not generate test cases
- it does not generate automation code
- it does not implement test design, automation design, dev handoff, QA review, or finalizer agents yet

Story readiness scoring:

- `90-100`: strong enough for test design and automation planning
- `70-89`: usable as a draft, but assumptions must stay visible
- `50-69`: incomplete draft story
- `0-49`: downstream test and automation generation should be blocked

Workflow behavior in this milestone:

- `full` and `story_only` now run the real Jira Story Agent
- if `requirements_readiness_score < 70`, Jira story generation is skipped or blocked
- if `story_readiness_score < 70` in `full` mode, downstream test and automation placeholder steps are blocked
- `test_design`, `automation_design`, `dev_handoff`, `qa_review`, and `finalizer` remain placeholders

Story-only smoke test:

```powershell
./scripts/test_workflow_story_only.ps1
```

Future-work note:

- real Jira API integration is intentionally deferred to a later milestone

## Milestone 6: Real Test Design Agent

Milestone 6 replaces the placeholder `test_design` step with a real AI-powered Test Design Agent.

What it does:

- consumes the original feature description
- consumes the Feature Intake Packet from the Intake Agent
- consumes the Requirements Agent output
- consumes the Jira Story Agent output when available
- produces QA-ready test coverage with practical scenarios tied back to requirements and acceptance criteria
- separates facts, assumptions, and open questions instead of hiding ambiguity
- identifies role/permission coverage, data variation coverage, negative tests, edge cases, and regression impact areas

What it does not do:

- it does not generate automation code
- it does not recommend a specific automation framework or implementation approach yet
- it does not implement the real Automation Design, Dev Handoff, QA Review, or Finalizer agents
- it does not integrate with external systems

Test design readiness scoring:

- `90-100`: strong enough for automation planning
- `70-89`: usable draft test design, but assumptions must stay visible
- `50-69`: partial test design only; automation planning should be blocked
- `0-49`: block automation planning and request clarification

Workflow behavior in this milestone:

- `full` and `test_only` now run the real Test Design Agent
- `story_only` does not run test design
- `automation_only` still skips test design and keeps automation design as a placeholder
- if upstream readiness is below threshold, test design is skipped or blocked
- if `test_design_readiness_score < 70` in `full` mode, the downstream `automation_design` placeholder is blocked

Test-only smoke test:

```powershell
./scripts/test_workflow_test_only.ps1
```

Future-work note:

- automation design is still a placeholder in this milestone

## Milestone 7: Real Automation Design Agent

Milestone 7 replaces the placeholder `automation_design` step with a real AI-powered Automation Design Agent.

What it does:

- consumes the original feature description
- consumes the Feature Intake Packet from the Intake Agent
- consumes the Requirements Agent output
- consumes the Jira Story Agent output when available
- consumes the Test Design Agent output
- recommends practical automation strategy for real QA teams
- identifies automation candidates, flaky or risky areas, recommended test layers, test hooks, selector needs, API or contract focus areas, and observability needs
- keeps facts, assumptions, recommendations, and open questions visibly separate

What it does not do:

- it does not generate Selenium, Cypress, Playwright, TestNG, or other framework code
- it does not implement Dev Handoff, QA Review, or Finalizer agents yet
- it does not integrate with Jira, GitLab, Teams, databases, or async queues
- it does not invent architecture that was not provided in the request
- implementation planning and code generation are intentionally out of scope for this milestone

Automation readiness scoring:

- `90-100`: safe for implementation planning
- `70-89`: usable draft automation design
- `50-69`: partial automation recommendations only
- `0-49`: block downstream implementation planning

Workflow behavior in this milestone:

- `full` now runs real `requirements`, `jira_story`, `test_design`, and `automation_design`
- `automation_only` now runs real `requirements`, `test_design`, and `automation_design`
- `story_only` and `test_only` do not run automation design
- if `test_design_readiness_score < 70`, automation design is blocked and the response returns open questions plus missing information
- `dev_handoff`, `qa_review`, and `finalizer` remain placeholders

Automation-only smoke test:

```powershell
./scripts/test_workflow_automation_only.ps1
```

The smoke test prints:

- run id, mode, and status
- workflow, requirements, test design, and automation design readiness scores
- automation candidate count
- flaky risk count
- step statuses
- the full JSON response

## Milestone 8: Real Dev Handoff Agent

Milestone 8 replaces the placeholder `dev_handoff` step with a real AI-powered Dev Handoff Agent.

What it does:

- consumes the original feature description
- consumes the Feature Intake Packet from the Intake Agent
- consumes the Requirements Agent output
- consumes the Jira Story Agent output when available
- consumes the Test Design Agent output when available
- consumes the Automation Design Agent output when available
- produces a developer-ready implementation handoff package for sprint planning
- identifies likely UI, API, data, integration, logging, error-handling, and configuration impacts
- identifies implementation risks, assumptions, and open questions while keeping them visibly separate
- produces developer planning tasks, definition of done, and a handoff readiness score

What it does not do:

- it does not generate production application code
- it does not create real Jira tickets
- it does not integrate with Jira, GitLab, Teams, databases, or async queues
- it does not implement QA Review or Finalizer agents yet
- it does not invent architecture that was not provided in the request

Handoff readiness scoring:

- `90-100`: safe for developer planning
- `70-89`: usable draft handoff with assumptions clearly marked
- `50-69`: partial handoff only; clarification needed before implementation
- `0-49`: implementation planning should be blocked

Workflow behavior in this milestone:

- `full` now runs real `requirements`, `jira_story`, `test_design`, `automation_design`, and `dev_handoff`
- `story_only`, `test_only`, and `automation_only` do not run dev handoff
- if `automation_design_readiness_score < 70`, dev handoff may still run but carries forward planning risk and uncertainty
- `qa_review` and `finalizer` remain placeholders

Full dev-handoff smoke test:

```powershell
./scripts/test_workflow_full_dev_handoff.ps1
```

The smoke test prints:

- run id, mode, and status
- workflow, requirements, story, test design, automation design, and handoff readiness scores
- developer task count
- UI impact count
- API impact count
- data impact count
- step statuses
- the full JSON response

## Milestone 9: Context Retrieval Agent

Milestone 9 adds a deterministic Context Retrieval Agent so the orchestrator can look up existing PolicySphere Lab artifacts before downstream SDLC planning.

What it does:

- reads `POLICYSPHERE_LAB_PATH` from local configuration
- loads `knowledge/system-manifest.json` from the separate PolicySphere Lab project
- loads supporting files referenced by that manifest when available
- matches feature requests against existing features, UI screens, API endpoints, database tables, business rules, automation tests, known defects, and test history
- returns a structured context packet with source-file traces, confidence, and open context questions
- runs before intake in workflow mode when a PolicySphere path is configured
- passes retrieved context into intake, requirements, jira story, test design, automation design, and dev handoff inputs

What it does not do:

- it does not move PolicySphere files into this repo
- it does not use embeddings, vector databases, or external search
- it does not make context retrieval a hard dependency for workflow execution
- it does not add Jira, GitLab, Teams, database persistence, or async queues

Why deterministic first:

- the matched artifacts are easy to inspect in logs and workflow output
- source files remain explicit instead of hidden behind retrieval infrastructure
- it keeps milestone scope focused while still giving downstream agents real system context

How to configure:

```env
POLICYSPHERE_LAB_PATH=C:/dev/policysphere-lab
```

PolicySphere Lab remains a separate local project. The orchestrator reads from that path and continues normally if the path is missing or invalid.

How to test `/retrieve-context`:

```powershell
./scripts/test_context_email_resend.ps1
./scripts/test_context_policy_comparison.ps1
./scripts/test_context_document_upload.ps1
```

Those scripts:

- call `POST /retrieve-context`
- honor `SDLC_API_BASE_URL`
- include `X-API-Key` automatically when `ORCHESTRATOR_API_KEY` is set
- pretty print matched features, APIs, UI screens, database tables, automation tests, and known defects

Custom GPT visibility notes:

- the Custom GPT action schema now exposes `/retrieve-context` directly for explicit artifact lookup requests
- `run-sdlc-workflow` now includes `final_output.context_retrieval_summary` so PolicySphere evidence is visible without digging through nested step payloads
- the full retrieved packet still remains available in `final_output.retrieved_context` and in the `context_retrieval` workflow step output

How context flows into SDLC agents:

- workflow mode adds a `context_retrieval` step before intake when configured
- retrieved context is attached to downstream step inputs
- the real agents receive that packet in their input payloads as existing system knowledge
- if retrieval cannot load context, the workflow continues and records a warning instead of blocking

## Connecting to a Custom GPT Action

Use the local FastAPI app with ngrok plus the action-specific schema endpoint to connect this API to a Custom GPT Action.

1. Start the API locally:

```powershell
./scripts/run_local.ps1
```

2. Start ngrok:

```powershell
./scripts/start_ngrok.ps1
```

3. Copy the HTTPS forwarding URL from ngrok.

4. Set `PUBLIC_BASE_URL` to that HTTPS URL and restart the API:

```powershell
$env:PUBLIC_BASE_URL="https://your-ngrok-url.ngrok-free.app"
```

5. Open the action schema:

```text
/openapi-action.yaml
```

You can print the exact local URLs with:

```powershell
./scripts/print_action_schema_url.ps1
```

6. Paste the schema into the Custom GPT Action editor.

7. Configure authentication as an API key:

- header name: `X-API-Key`
- value: the same value as `ORCHESTRATOR_API_KEY`

8. Test the action in GPT preview.

Notes:

- `GET /health`, `GET /openapi.json`, and `GET /openapi-action.yaml` stay public.
- `POST /run-intake` and `POST /run-sdlc-workflow` require `X-API-Key` only when `ORCHESTRATOR_API_KEY` is configured.
- if `ORCHESTRATOR_API_KEY` is empty, the API allows local/dev requests and logs a warning so existing smoke tests keep working.

## Blocked vs Failed Workflows

Blocked and failed are intentionally different states.

- `blocked` means an expected readiness or clarification gate was reached
- `failed` means a technical or system error occurred

How a Custom GPT should present blocked responses:

- show `user_safe_message`
- show `clarification_questions`
- treat the response as a normal next-step request for more detail
- do not say the workflow tool failed when `status="blocked"`

Example blocked response:

```json
{
  "status": "blocked",
  "reason_code": "insufficient_feature_detail",
  "user_safe_message": "I need a little more detail before I can generate the SDLC workflow package.",
  "blocking_gaps": [
    "Desired behavior is unclear."
  ],
  "clarification_questions": [
    "What should the feature do differently from the current workflow?"
  ],
  "readiness_score": 42,
  "can_continue": false,
  "steps": []
}
```

Example user-facing wording:

```text
I need a little more detail before I can generate the SDLC workflow package. Could you clarify the desired behavior, affected users, and any business rules or system impacts?
```
