from fastapi.testclient import TestClient

import pytest

import app.main as main_module
from app.config import get_settings
from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.requirements_models import RequirementsAgentResult
from app.services.workflow_engine import WorkflowEngine


class FakeIntakeService:
    def __init__(self, response: RunIntakeResponse) -> None:
        self.response = response

    def run(self, request):  # noqa: ANN001
        return self.response


class FakeRequirementsService:
    def __init__(self, response: RequirementsAgentResult) -> None:
        self.response = response

    def run(self, request):  # noqa: ANN001
        return self.response


def _field(value: str, confidence: str = "high", source: str = "provided", needs_clarification: bool = False) -> PacketField:
    return PacketField(
        value=value,
        confidence=confidence,
        source=source,
        needs_clarification=needs_clarification,
    )


def _intake_response() -> RunIntakeResponse:
    packet = FeatureIntakePacket(
        feature_name=_field("Feature"),
        problem_statement=_field("Problem"),
        business_goal=_field("Goal"),
        target_users=_field("Users"),
        current_behavior=_field("Current"),
        desired_behavior=_field("Desired"),
        in_scope=_field("In scope"),
        out_of_scope=_field("Out of scope"),
        business_rules=_field("Rules"),
        data_inputs=_field("Inputs"),
        data_outputs=_field("Outputs"),
        user_roles_permissions=_field("Roles"),
        systems_impacted=_field("Systems"),
        api_or_contract_impacts=_field("API"),
        ui_impacts=_field("UI"),
        reporting_or_audit_needs=_field("Audit"),
        error_handling_expectations=_field("Errors"),
        edge_cases=_field("Edge"),
        non_functional_requirements=_field("NFR"),
        dependencies=_field("Deps"),
        known_risks=_field("Risks"),
        open_questions=_field("Questions"),
        assumptions=_field("Assumptions"),
    )
    return RunIntakeResponse(
        feature_intake_packet=packet,
        readiness_score=82,
        can_continue=True,
        blocking_gaps=[],
        clarification_questions=[],
        safe_to_generate=["draft_sdlc_package"],
        not_safe_to_generate=[],
    )


def _requirements_response() -> RequirementsAgentResult:
    return RequirementsAgentResult.model_validate(
        {
            "functional_requirements": [],
            "non_functional_requirements": [],
            "business_rules": [],
            "data_requirements": [],
            "integration_requirements": [],
            "role_permission_requirements": [],
            "assumptions": [],
            "open_questions": [],
            "risks": [],
            "requirements_readiness_score": 80,
            "safe_for_jira_story_generation": True,
            "safe_for_test_design": True,
            "not_safe_to_generate": [],
        }
    )


def _configure_app_services() -> TestClient:
    main_module.app.state.intake_service = FakeIntakeService(_intake_response())
    main_module.app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response()),
        requirements_service=FakeRequirementsService(_requirements_response()),
    )
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_protected_endpoints_allow_requests_without_configured_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_API_KEY", raising=False)
    get_settings.cache_clear()
    client = _configure_app_services()

    intake_response = client.post(
        "/run-intake",
        json={
            "feature_description": "Add export",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )
    workflow_response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "qa_review_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )
    retrieve_context_response = client.post(
        "/retrieve-context",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
        },
    )

    assert intake_response.status_code == 200
    assert workflow_response.status_code == 200
    assert retrieve_context_response.status_code == 200


def test_protected_endpoints_reject_missing_key_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", "test-key")
    get_settings.cache_clear()
    client = _configure_app_services()

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "qa_review_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid X-API-Key header."

    retrieve_context_response = client.post(
        "/retrieve-context",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
        },
    )

    assert retrieve_context_response.status_code == 401


def test_protected_endpoints_reject_wrong_key(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", "test-key")
    get_settings.cache_clear()
    client = _configure_app_services()

    response = client.post(
        "/run-intake",
        headers={"X-API-Key": "wrong-key"},
        json={
            "feature_description": "Add export",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    assert response.status_code == 401


def test_protected_endpoints_accept_correct_key(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", "test-key")
    get_settings.cache_clear()
    client = _configure_app_services()

    response = client.post(
        "/run-sdlc-workflow",
        headers={"X-API-Key": "test-key"},
        json={
            "feature_description": "Add export",
            "mode": "qa_review_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    assert response.status_code == 200


def test_weak_workflow_request_returns_blocked_with_http_200(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", "test-key")
    get_settings.cache_clear()

    weak_intake = RunIntakeResponse(
        feature_intake_packet=_intake_response().feature_intake_packet,
        readiness_score=45,
        can_continue=False,
        blocking_gaps=["Desired behavior is unclear."],
        clarification_questions=["What should the feature do differently from the current workflow?"],
        safe_to_generate=["clarification_questions"],
        not_safe_to_generate=["full_sdlc_package"],
    )

    main_module.app.state.intake_service = FakeIntakeService(weak_intake)
    main_module.app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(weak_intake),
        requirements_service=FakeRequirementsService(_requirements_response()),
    )
    client = TestClient(main_module.app)

    response = client.post(
        "/run-sdlc-workflow",
        headers={"X-API-Key": "test-key"},
        json={
            "feature_description": "Make reporting better somehow.",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["user_safe_message"] == "I need a little more detail before I can generate the SDLC workflow package."
    assert body["clarification_questions"] == ["What should the feature do differently from the current workflow?"]
    assert body["status"] != "failed"


def test_openapi_action_yaml_returns_yaml_and_uses_public_base_url(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.ngrok-free.app")
    get_settings.cache_clear()
    client = _configure_app_services()

    response = client.get("/openapi-action.yaml")

    assert response.status_code == 200
    assert "openapi:" in response.text
    assert "https://example.ngrok-free.app" in response.text


def test_action_schema_includes_api_key_security_scheme(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.ngrok-free.app")
    get_settings.cache_clear()
    client = _configure_app_services()

    response = client.get("/openapi-action.yaml")

    assert response.status_code == 200
    assert "X-API-Key" in response.text
    assert "type: apiKey" in response.text
    assert "x-openai-isConsequential: false" in response.text
    assert "/retrieve-context:" in response.text
    assert "Run intake-only readiness analysis" in response.text
    assert "Run the full SDLC workflow when the user wants downstream planning" in response.text
    assert "context_retrieval before intake" in response.text
    assert "Retrieve existing PolicySphere system context for a feature request" in response.text
