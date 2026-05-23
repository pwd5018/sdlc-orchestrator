import copy
import logging

import yaml
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.config import get_settings


logger = logging.getLogger(__name__)


def build_action_openapi_yaml(app: FastAPI) -> str:
    settings = get_settings()
    public_base_url = settings.public_base_url

    if not public_base_url or public_base_url == "http://127.0.0.1:8000":
        logger.warning("PUBLIC_BASE_URL is not configured; defaulting action schema server URL to http://127.0.0.1:8000")
        public_base_url = "http://127.0.0.1:8000"

    openapi_schema = get_openapi(
        title="SDLC Orchestrator API",
        version=app.version,
        routes=app.routes,
        description=app.description,
    )
    action_schema = copy.deepcopy(openapi_schema)

    allowed_paths = {"/run-intake", "/run-sdlc-workflow", "/retrieve-context"}
    action_schema["paths"] = {
        path: value
        for path, value in action_schema.get("paths", {}).items()
        if path in allowed_paths
    }
    action_schema["servers"] = [{"url": public_base_url}]

    for path in allowed_paths:
        operation = action_schema["paths"].get(path, {}).get("post")
        if operation is not None:
            operation["x-openai-isConsequential"] = False
            if path == "/run-sdlc-workflow":
                operation["description"] = (
                    "Run the full SDLC workflow when the user wants downstream planning or existing-system context. "
                    "When PolicySphere context retrieval is configured, this action runs context_retrieval before intake "
                    "and includes retrieval evidence in both steps and final_output. This action may return status='blocked' "
                    "when the feature request lacks enough detail. Treat blocked as a normal clarification-needed response, "
                    "not as a tool error. Show user_safe_message and clarification_questions to the user when blocked."
                )
            if path == "/run-intake":
                operation["description"] = (
                    "Run intake-only readiness analysis for a feature request. Use this when the user wants intake or "
                    "clarification feedback only, not the full downstream SDLC workflow."
                )
            if path == "/retrieve-context":
                operation["description"] = (
                    "Retrieve existing PolicySphere system context for a feature request. Use this when the user explicitly "
                    "asks to look up existing artifacts such as features, APIs, UI screens, tables, tests, or defects."
                )

    workflow_response_schema = action_schema.get("components", {}).get("schemas", {}).get("RunWorkflowResponse")
    if workflow_response_schema:
        properties = workflow_response_schema.get("properties", {})
        status_property = properties.get("status")
        if status_property:
            status_property["description"] = (
                "Workflow outcome. completed means successful workflow execution. blocked means an expected "
                "clarification-needed state and should not be treated as a tool error. failed means a technical "
                "or system failure."
            )
            status_property["x-enumDescriptions"] = [
                "successful workflow",
                "expected clarification-needed state",
                "technical or system failure",
            ]

    return yaml.safe_dump(action_schema, sort_keys=False)
