import logging

from fastapi import Depends, FastAPI, HTTPException, Response

from app.models.context_models import ContextRetrievalRequest, RetrievedContextPacket
from app.models.intake_models import HealthResponse, RunIntakeRequest, RunIntakeResponse
from app.models.workflow_models import RunWorkflowRequest, RunWorkflowResponse
from app.services.context_retrieval_service import ContextRetrievalService
from app.services.automation_design_service import AutomationDesignProcessingError
from app.services.dev_handoff_service import DevHandoffProcessingError
from app.services.intake_service import IntakeProcessingError, IntakeService
from app.services.action_schema import build_action_openapi_yaml
from app.services.api_auth import require_api_key
from app.services.llm.base_provider import LLMConfigurationError, LLMProviderError
from app.services.jira_story_service import JiraStoryProcessingError
from app.services.requirements_service import RequirementsProcessingError
from app.services.test_design_service import TestDesignProcessingError
from app.services.workflow_engine import WorkflowEngine, WorkflowExecutionError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SDLC Orchestrator",
    version="0.9.0",
    description="Milestone 9 workflow shell with real SDLC agents plus deterministic Context Retrieval for PolicySphere Lab.",
)

intake_service = IntakeService()
context_retrieval_service = ContextRetrievalService()
workflow_engine = WorkflowEngine(intake_service=intake_service)
app.state.intake_service = intake_service
app.state.context_retrieval_service = context_retrieval_service
app.state.workflow_engine = workflow_engine


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="intake-agent")


@app.get("/openapi-action.yaml")
def openapi_action_yaml() -> Response:
    return Response(content=build_action_openapi_yaml(app), media_type="application/yaml")


@app.post("/run-intake", response_model=RunIntakeResponse, dependencies=[Depends(require_api_key)])
def run_intake(request: RunIntakeRequest) -> RunIntakeResponse:
    logger.info("request received feature_description_length=%s", len(request.feature_description))

    try:
        return app.state.intake_service.run(request)
    except LLMConfigurationError as exc:
        logger.exception("run-intake failed due to llm configuration error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMProviderError as exc:
        logger.exception("run-intake failed during llm request")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except IntakeProcessingError as exc:
        logger.exception("run-intake failed during intake processing")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive error handling
        logger.exception("run-intake failed unexpectedly")
        raise HTTPException(status_code=500, detail="Unexpected server error.") from exc


@app.post("/retrieve-context", response_model=RetrievedContextPacket, dependencies=[Depends(require_api_key)])
def retrieve_context(request: ContextRetrievalRequest) -> RetrievedContextPacket:
    logger.info(
        "context retrieval request received feature_description_length=%s mode=%s",
        len(request.feature_description),
        request.mode,
    )

    try:
        return app.state.context_retrieval_service.run(request)
    except Exception as exc:  # pragma: no cover - defensive error handling
        logger.exception("retrieve-context failed unexpectedly")
        raise HTTPException(status_code=500, detail="Unexpected server error.") from exc


@app.post("/run-sdlc-workflow", response_model=RunWorkflowResponse, dependencies=[Depends(require_api_key)])
def run_sdlc_workflow(request: RunWorkflowRequest) -> RunWorkflowResponse:
    """
    Run the SDLC workflow shell.

    This action may return status='blocked' when the feature request lacks enough detail.
    Treat blocked as a normal clarification-needed response, not as a tool error.
    Show user_safe_message and clarification_questions to the user when blocked.
    """
    logger.info(
        "workflow request received feature_description_length=%s mode=%s",
        len(request.feature_description),
        request.mode,
    )

    try:
        return app.state.workflow_engine.run(request)
    except (
        LLMConfigurationError,
        LLMProviderError,
        IntakeProcessingError,
        RequirementsProcessingError,
        JiraStoryProcessingError,
        TestDesignProcessingError,
        AutomationDesignProcessingError,
        DevHandoffProcessingError,
        WorkflowExecutionError,
    ) as exc:
        logger.exception("run-sdlc-workflow failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive error handling
        logger.exception("run-sdlc-workflow failed unexpectedly")
        raise HTTPException(status_code=500, detail="Unexpected server error.") from exc
