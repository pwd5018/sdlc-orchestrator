from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.config import get_settings
from app.models.automation_design_models import AutomationDesignAgentResult
from app.models.context_models import RetrievedContextPacket
from app.models.dev_handoff_models import DevHandoffAgentResult
from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentResult as DesignResultModel
from app.services.workflow_engine import WorkflowEngine


def _field(value: str, confidence: str = "high", source: str = "provided", needs_clarification: bool = False) -> PacketField:
    return PacketField(
        value=value,
        confidence=confidence,
        source=source,
        needs_clarification=needs_clarification,
    )


def _intake_response(readiness_score: int, can_continue: bool, clarification_questions: list[str] | None = None) -> RunIntakeResponse:
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
        open_questions=_field("Questions", confidence="medium", source="inferred", needs_clarification=True),
        assumptions=_field("Assumptions", confidence="medium", source="inferred", needs_clarification=True),
    )
    return RunIntakeResponse(
        feature_intake_packet=packet,
        readiness_score=readiness_score,
        can_continue=can_continue,
        blocking_gaps=["Need permission rules"] if readiness_score < 70 else [],
        clarification_questions=clarification_questions or [],
        safe_to_generate=["draft_sdlc_package"] if can_continue else ["clarification_questions"],
        not_safe_to_generate=[],
    )


class FakeIntakeService:
    def __init__(self, response: RunIntakeResponse) -> None:
        self.response = response

    def run(self, request):  # noqa: ANN001
        return self.response


class FakeRequirementsService:
    def __init__(self, response: RequirementsAgentResult) -> None:
        self.response = response
        self.calls = 0

    def run(self, request):  # noqa: ANN001
        self.calls += 1
        return self.response


class FakeJiraStoryService:
    def __init__(self, response: JiraStoryAgentResult) -> None:
        self.response = response
        self.calls = 0

    def run(self, request):  # noqa: ANN001
        self.calls += 1
        return self.response


class FakeTestDesignService:
    def __init__(self, response: DesignResultModel) -> None:
        self.response = response
        self.calls = 0

    def run(self, request):  # noqa: ANN001
        self.calls += 1
        return self.response


class FakeAutomationDesignService:
    def __init__(self, response: AutomationDesignAgentResult) -> None:
        self.response = response
        self.calls = 0

    def run(self, request):  # noqa: ANN001
        self.calls += 1
        return self.response


class FakeContextRetrievalService:
    def __init__(self, response: RetrievedContextPacket | None = None, *, configured: bool = True, error: Exception | None = None) -> None:
        self.response = response
        self.configured = configured
        self.error = error
        self.calls = 0

    def is_configured(self) -> bool:
        return self.configured

    def run(self, request):  # noqa: ANN001
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.response or _retrieved_context_packet()


class FakeDevHandoffService:
    def __init__(self, response: DevHandoffAgentResult) -> None:
        self.response = response
        self.calls = 0

    def run(self, request):  # noqa: ANN001
        self.calls += 1
        return self.response


@pytest.fixture(autouse=True)
def clear_auth_settings(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_API_KEY", raising=False)
    monkeypatch.delenv("POLICYSPHERE_LAB_PATH", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def restore_app_state():
    original_intake_service = app.state.intake_service
    original_workflow_engine = app.state.workflow_engine
    yield
    app.state.intake_service = original_intake_service
    app.state.workflow_engine = original_workflow_engine


def _requirements_response(score: int) -> RequirementsAgentResult:
    return RequirementsAgentResult.model_validate(
        {
            "functional_requirements": [
                {
                    "id": "FR-001",
                    "requirement": "Authorized users can export the filtered view.",
                    "source": "provided",
                    "confidence": "high",
                    "acceptance_hint": "Export contains the visible filtered rows only.",
                    "related_business_rules": ["BR-001"],
                    "open_questions": []
                }
            ],
            "non_functional_requirements": [],
            "business_rules": [
                {
                    "id": "BR-001",
                    "rule": "Export must respect active filters.",
                    "source": "provided",
                    "confidence": "high",
                    "impacted_requirements": ["FR-001"],
                    "open_questions": [],
                }
            ],
            "data_requirements": [],
            "integration_requirements": [],
            "role_permission_requirements": [],
            "assumptions": ["Assume current permissions can be reused."],
            "open_questions": ["Confirm export file size expectations."] if score < 70 else [],
            "risks": ["Large exports may be slow."],
            "requirements_readiness_score": score,
            "safe_for_jira_story_generation": score >= 70,
            "safe_for_test_design": score >= 70,
            "not_safe_to_generate": ["jira_story_generation", "test_design", "automation_design"] if score < 70 else []
        }
    )


def _jira_story_response(score: int) -> JiraStoryAgentResult:
    return JiraStoryAgentResult.model_validate(
        {
            "summary": "Add CSV export for filtered release readiness view",
            "story_type": "story",
            "description": "Enable authorized users to export the current filtered dashboard view as CSV with audit logging.",
            "user_story": {
                "as_a": "program manager",
                "i_want": "to export the currently filtered release readiness view as CSV",
                "so_that": "I can share accurate updates without copying rows manually",
            },
            "acceptance_criteria": [
                {
                    "id": "AC-001",
                    "criterion": "Authorized users can export only the currently visible filtered rows.",
                    "given_when_then": {
                        "given": "an authorized user is viewing filtered results",
                        "when": "the user selects Export CSV",
                        "then": "the exported file contains only the visible filtered rows",
                    },
                    "source_requirement_ids": ["FR-001", "BR-001"],
                    "confidence": "high",
                }
            ] if score >= 70 else [],
            "business_rules_referenced": ["BR-001"],
            "dependencies": ["reporting-service", "audit-logging-service"],
            "assumptions": ["Assume current permissions can be reused."] if score < 90 else [],
            "open_questions": ["Confirm export size limits."] if score < 70 else [],
            "labels": ["reporting", "csv-export"],
            "components": ["dashboard-ui", "reporting-service"],
            "definition_of_done": ["Story reviewed and clarified."],
            "out_of_scope": ["Scheduled exports", "PDF export"],
            "story_readiness_score": score,
            "safe_for_test_design": score >= 70,
            "safe_for_automation_design": score >= 70,
            "not_safe_to_generate": [] if score >= 70 else ["test_design", "automation_design", "dev_handoff"],
        }
    )


def _test_design_response(score: int) -> DesignResultModel:
    return DesignResultModel.model_validate(
        {
            "test_design_summary": "Cover export behavior across happy path, permissions, failures, and data variation.",
            "coverage_strategy": {
                "primary_risks": ["Incorrect export contents", "Permission drift", "Poor failure handling"],
                "critical_business_rules": ["BR-001"],
                "recommended_test_levels": ["api", "ui", "integration", "regression"],
            },
            "test_scenarios": [
                {
                    "id": "TS-001",
                    "title": "Authorized user exports filtered rows",
                    "type": "happy_path",
                    "priority": "critical",
                    "description": "Verify export returns only the visible filtered rows.",
                    "preconditions": ["Authorized user is on the dashboard."],
                    "test_data": ["Filtered dashboard results."],
                    "steps": ["Apply filters.", "Click Export CSV."],
                    "expected_results": ["CSV is generated.", "Rows match the visible filtered results."],
                    "source_requirement_ids": ["FR-001"],
                    "source_acceptance_criteria_ids": ["AC-001"] if score >= 70 else [],
                    "assumptions": [],
                    "open_questions": [],
                    "automation_candidate": True,
                    "confidence": "high",
                }
            ] if score >= 70 else [],
            "role_permission_tests": [
                {
                    "id": "RPT-001",
                    "role": "program manager",
                    "allowed_actions": ["Export visible readiness rows"],
                    "restricted_actions": ["Export rows outside assigned visibility scope"],
                    "test_notes": ["Authorization should match existing dashboard visibility rules."],
                    "source": "provided",
                    "confidence": "high",
                }
            ],
            "data_variation_tests": [
                {
                    "id": "DVT-001",
                    "data_condition": "Empty filtered result set",
                    "expected_behavior": "The user receives a clear export result with no incorrect data rows.",
                    "risk": "Blank files may be misleading.",
                    "confidence": "medium",
                }
            ],
            "negative_tests": ["Unauthorized export attempt", "Export generation failure"],
            "edge_cases": ["Large result sets", "Permission change during export"],
            "regression_impact_areas": ["Dashboard filtering", "Audit logging"],
            "untestable_or_unclear_items": ["Performance threshold is not fully specified."] if score < 70 else [],
            "assumptions": ["Assume current permissions can be reused."] if score < 90 else [],
            "open_questions": ["What large-export limit is acceptable?"] if score < 70 else [],
            "test_design_readiness_score": score,
            "safe_for_automation_design": score >= 70,
            "not_safe_to_generate": [] if score >= 70 else ["automation_design"],
        }
    )


def _automation_design_response(score: int) -> AutomationDesignAgentResult:
    return AutomationDesignAgentResult.model_validate(
        {
            "automation_strategy_summary": "Prioritize stable API and contract coverage first, then add focused UI automation around export initiation and authorization-sensitive behavior.",
            "recommended_test_layers": [
                {
                    "layer": "api",
                    "recommendation": "Cover filter propagation, authorization, and export request validation at the service boundary.",
                    "reasoning": "These checks are more stable below the UI layer and directly address the highest business risk.",
                    "confidence": "high",
                },
                {
                    "layer": "ui",
                    "recommendation": "Keep UI automation thin and focused on export entry-point behavior plus visible feedback.",
                    "reasoning": "File-download plumbing and dynamic table assertions can become brittle when over-asserted through UI tests.",
                    "confidence": "medium",
                },
            ],
            "automation_candidates": [
                {
                    "id": "AT-001",
                    "title": "Authorized user exports filtered rows",
                    "recommended_layer": "api",
                    "priority": "critical",
                    "business_risk": "Incorrect exports could produce misleading operational reporting.",
                    "recommended_approach": "Validate filter handling and permission behavior primarily through API or service automation, then confirm the UI trigger path with a smaller end-to-end check.",
                    "source_test_scenario_ids": ["TS-001"],
                    "estimated_stability": "high",
                    "confidence": "high",
                }
            ],
            "api_test_recommendations": [
                {
                    "id": "API-001",
                    "recommendation": "Validate export requests preserve active filters and authorization context.",
                    "reasoning": "A request-contract mismatch could break the feature even when UI behavior looks correct.",
                    "contract_or_endpoint": "POST /reports/readiness/export",
                    "confidence": "high",
                }
            ],
            "ui_test_recommendations": [
                {
                    "id": "UI-001",
                    "recommendation": "Automate the core export trigger path and user-visible success or failure messaging only.",
                    "selector_or_hook_needs": ["Stable Export CSV hook", "Stable export status message hook"],
                    "stability_risks": ["Asynchronous export timing", "Browser download handling"],
                    "confidence": "medium",
                }
            ],
            "contract_test_recommendations": [
                {
                    "id": "CT-001",
                    "recommendation": "Add a contract check between dashboard requests and reporting export expectations.",
                    "systems_involved": ["dashboard-ui", "reporting-service"],
                    "risk_if_missing": "Contract drift could silently break exports late in the cycle.",
                    "confidence": "high",
                }
            ],
            "test_data_requirements": [
                {
                    "id": "TD-001",
                    "data_need": "Permission-scoped filtered datasets",
                    "purpose": "Verify export rows match visibility rules and filter scope.",
                    "risk": "Weak datasets can hide authorization or filtering mismatches.",
                    "confidence": "high",
                }
            ],
            "flaky_risk_areas": [
                {
                    "id": "FR-001",
                    "risk_area": "Browser download timing and asynchronous export feedback",
                    "why_risky": "UI checks may race against background export generation or status updates.",
                    "mitigation_recommendation": "Prefer API assertions for content and keep UI checks focused on stable signals.",
                    "confidence": "high",
                }
            ],
            "recommended_test_hooks": ["Stable Export CSV trigger hook", "Traceable export request identifier"],
            "recommended_logging_or_observability": ["Audit export attempts with actor and filter summary"],
            "assumptions": ["Assume current permission rules should be reused."],
            "open_questions": ["What response indicates export queued versus completed?"] if score < 70 else [],
            "automation_design_readiness_score": score,
            "safe_for_implementation_planning": score >= 70,
            "not_safe_to_generate": [] if score >= 70 else ["implementation_planning"],
        }
    )


def _retrieved_context_packet() -> RetrievedContextPacket:
    return RetrievedContextPacket.model_validate(
        {
            "matched_features": [
                {
                    "id": "FEAT-001",
                    "name": "failed_email_resend",
                    "reason_matched": "Matched request keywords: export, resend.",
                    "source_file": "knowledge/features.json",
                    "confidence": "high",
                }
            ],
            "matched_ui_screens": [
                {
                    "id": "UI-001",
                    "name": "EmailHistoryPage",
                    "reason_matched": "Linked from a matched feature artifact.",
                    "source_file": "knowledge/ui_screens.json",
                    "confidence": "medium",
                }
            ],
            "matched_api_endpoints": [
                {
                    "id": "API-001",
                    "name": "POST /emails/{email_id}/resend",
                    "reason_matched": "Linked from a matched feature artifact.",
                    "source_file": "knowledge/api_endpoints.json",
                    "confidence": "medium",
                }
            ],
            "matched_database_tables": [],
            "matched_business_rules": [],
            "matched_automation_tests": [],
            "matched_known_defects": [],
            "matched_test_history": [],
            "risk_areas": ["Resend retries can duplicate outbound delivery."],
            "source_files_loaded": ["knowledge/system-manifest.json", "knowledge/features.json"],
            "retrieval_confidence": "medium",
            "open_context_questions": [],
        }
    )


def _dev_handoff_response(score: int, safe_for_dev_planning: bool | None = None) -> DevHandoffAgentResult:
    safe_flag = safe_for_dev_planning if safe_for_dev_planning is not None else score >= 70
    return DevHandoffAgentResult.model_validate(
        {
            "developer_summary": "Implement the export feature across UI, API, data persistence, audit logging, and permission checks without introducing scheduled-export behavior.",
            "implementation_scope": {
                "in_scope": [
                    "On-demand export initiation from the dashboard UI",
                    "Server-side export request handling with permission enforcement",
                    "Audit logging for export attempts and outcomes",
                ],
                "out_of_scope": [
                    "Scheduled exports",
                    "PDF export",
                ],
                "assumptions": ["Current visibility rules can be reused for export authorization."],
            },
            "ui_impacts": [
                {
                    "id": "UI-001",
                    "area": "dashboard export controls",
                    "change": "Add an Export CSV action with permission-aware visibility and user feedback states.",
                    "user_roles_impacted": ["program manager"],
                    "validation_or_state_notes": ["Disable or hide export control for unauthorized users."],
                    "confidence": "high",
                }
            ],
            "api_impacts": [
                {
                    "id": "API-001",
                    "endpoint_or_contract": "POST /reports/readiness/export",
                    "change": "Accept active filters plus caller context and return an export result contract.",
                    "request_response_notes": ["Filters must map consistently from the UI to the export request."],
                    "error_handling_notes": ["Return actionable authorization and generation failure outcomes."],
                    "confidence": "high",
                }
            ],
            "data_model_impacts": [
                {
                    "id": "DATA-001",
                    "entity_or_table": "export audit event",
                    "change": "Capture export attempts, outcomes, and filter summary for traceability.",
                    "fields_or_attributes": ["actor", "timestamp", "filter summary", "result status"],
                    "migration_needed": "unknown",
                    "confidence": "medium",
                }
            ],
            "integration_impacts": [
                {
                    "id": "INT-001",
                    "system": "reporting-service",
                    "interaction": "Generate CSV output using filters and caller identity context.",
                    "risk": "Contract drift could break export content or permissions.",
                    "confidence": "high",
                }
            ],
            "configuration_impacts": [
                {
                    "id": "CFG-001",
                    "setting": "export_result_size_limit",
                    "purpose": "Constrain large exports if operational limits are required.",
                    "default_value": "unknown",
                    "admin_configurable": True,
                    "confidence": "low",
                }
            ],
            "audit_logging_requirements": [
                {
                    "id": "LOG-001",
                    "event": "export requested",
                    "fields_to_capture": ["actor", "role", "timestamp", "filter summary"],
                    "reason": "Support traceability and access auditing.",
                    "confidence": "high",
                }
            ],
            "error_handling_requirements": [
                {
                    "id": "ERR-001",
                    "condition": "Export request fails or the user lacks permission.",
                    "expected_behavior": "Do not expose incorrect data, and show a clear failure outcome.",
                    "user_message_needed": True,
                    "confidence": "high",
                }
            ],
            "developer_tasks": [
                {
                    "id": "DEV-001",
                    "title": "Define export request and response contract",
                    "description": "Align UI, API, and reporting service expectations for filters, caller context, and result handling.",
                    "area": "api",
                    "depends_on": [],
                    "confidence": "high",
                },
                {
                    "id": "DEV-002",
                    "title": "Implement permission-aware export UI flow",
                    "description": "Add the export trigger, role-aware visibility, and success or failure messaging.",
                    "area": "ui",
                    "depends_on": ["DEV-001"],
                    "confidence": "high",
                }
            ],
            "definition_of_done": [
                "Authorized users can start an export from the dashboard.",
                "Unauthorized users cannot access export behavior.",
                "Audit events capture export attempts and outcomes.",
            ],
            "implementation_risks": ["Large exports may be slow without clear operational limits."],
            "open_questions": ["Confirm expected response contract for queued versus completed exports."] if score < 90 else [],
            "handoff_readiness_score": score,
            "safe_for_dev_planning": safe_flag,
            "not_safe_to_generate": [] if safe_flag else ["implementation_planning"],
        }
    )


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "intake-agent"}


def test_run_workflow_blocked_case() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(
            _intake_response(
                readiness_score=65,
                can_continue=False,
                clarification_questions=["Who should be allowed to export?"],
            )
        ),
        requirements_service=FakeRequirementsService(_requirements_response(80)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason_code"] == "insufficient_feature_detail"
    assert body["user_safe_message"] == "I need a little more detail before I can generate the SDLC workflow package."
    assert body["readiness_score"] == 65
    assert body["steps"] == []
    assert body["clarification_questions"] == ["Who should be allowed to export?"]
    assert body["status"] != "failed"


def test_run_workflow_success_case_with_placeholder_steps() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(
            _intake_response(
                readiness_score=82,
                can_continue=True,
                clarification_questions=["Confirm export audit fields."],
            )
        ),
        requirements_service=FakeRequirementsService(_requirements_response(82)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(84)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(82)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    step_names = [step["step_name"] for step in body["steps"]]

    assert response.status_code == 200
    assert body["status"] == "completed"
    assert step_names == ["intake", "requirements", "jira_story", "qa_review", "finalizer"]
    assert body["steps"][1]["output"]["requirements_readiness_score"] == 82
    assert body["steps"][2]["output"]["story_readiness_score"] == 84


def test_full_mode_includes_real_requirements_step() -> None:
    client = TestClient(app)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(88))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=84, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(88)),
        test_design_service=FakeTestDesignService(_test_design_response(86)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(87)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert step_names == [
        "intake",
        "requirements",
        "jira_story",
        "test_design",
        "automation_design",
        "dev_handoff",
        "qa_review",
        "finalizer",
    ]
    assert fake_dev_handoff.calls == 1


def test_test_only_mode_includes_real_requirements_step() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=80, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(80)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(80)),
        test_design_service=FakeTestDesignService(_test_design_response(81)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(81)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "test_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert step_names == ["intake", "requirements", "test_design", "qa_review", "finalizer"]


def test_automation_only_mode_includes_real_requirements_step() -> None:
    client = TestClient(app)
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(80))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=80, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(80)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(80)),
        test_design_service=FakeTestDesignService(_test_design_response(80)),
        automation_design_service=fake_automation_design,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "automation_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert step_names == ["intake", "requirements", "test_design", "automation_design", "qa_review", "finalizer"]
    assert fake_automation_design.calls == 1


def test_workflow_includes_context_retrieval_step_when_configured() -> None:
    client = TestClient(app)
    fake_context = FakeContextRetrievalService(_retrieved_context_packet(), configured=True)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(88))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=84, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(85)),
        test_design_service=FakeTestDesignService(_test_design_response(84)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(84)),
        dev_handoff_service=fake_dev_handoff,
        context_retrieval_service=fake_context,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["steps"][0]["step_name"] == "context_retrieval"
    assert body["steps"][0]["status"] == "completed"
    assert body["steps"][1]["step_name"] == "intake"
    assert "retrieved_context" in body["steps"][1]["input"]
    assert body["final_output"]["context_retrieval_summary"]["status"] == "completed"
    assert body["final_output"]["context_retrieval_summary"]["matched_feature_names"] == ["failed_email_resend"]
    assert body["final_output"]["context_retrieval_summary"]["source_file_count"] == 2
    assert "PolicySphere context retrieved from 2 files" in body["final_output"]["message"]
    assert fake_context.calls == 1


def test_qa_review_only_mode_does_not_require_requirements_step() -> None:
    client = TestClient(app)
    fake_requirements = FakeRequirementsService(_requirements_response(80))
    fake_jira_story = FakeJiraStoryService(_jira_story_response(80))
    fake_test_design = FakeTestDesignService(_test_design_response(80))
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(80))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=80, can_continue=True)),
        requirements_service=fake_requirements,
        jira_story_service=fake_jira_story,
        test_design_service=fake_test_design,
        automation_design_service=fake_automation_design,
    )

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

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert step_names == ["intake", "qa_review", "finalizer"]
    assert fake_requirements.calls == 0
    assert fake_jira_story.calls == 0
    assert fake_test_design.calls == 0
    assert fake_automation_design.calls == 0


def test_workflow_continues_if_context_retrieval_fails() -> None:
    client = TestClient(app)
    fake_context = FakeContextRetrievalService(configured=True, error=RuntimeError("manifest parse failed"))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=82, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(82)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(84)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(82)),
        context_retrieval_service=fake_context,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["steps"][0]["step_name"] == "context_retrieval"
    assert body["steps"][0]["status"] == "skipped"
    assert body["final_output"]["warnings"]
    assert body["final_output"]["context_retrieval_summary"]["status"] == "failed_non_blocking"
    assert body["final_output"]["context_retrieval_summary"]["matched_feature_names"] == []
    assert "PolicySphere context retrieval did not produce reusable artifact matches." in body["final_output"]["message"]
    assert fake_context.calls == 1


def test_workflow_context_summary_is_visible_without_nested_step_inspection() -> None:
    client = TestClient(app)
    fake_context = FakeContextRetrievalService(_retrieved_context_packet(), configured=True)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=82, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(82)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(84)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(82)),
        context_retrieval_service=fake_context,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    summary = body["final_output"]["context_retrieval_summary"]
    assert response.status_code == 200
    assert summary["status"] == "completed"
    assert summary["retrieval_confidence"] == "medium"
    assert summary["matched_feature_count"] == 1
    assert summary["matched_api_endpoint_count"] == 1
    assert summary["matched_ui_screen_count"] == 1
    assert summary["source_file_count"] == 2
    assert summary["total_match_count"] >= 3


def test_low_requirements_readiness_blocks_downstream_generation() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=82, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(62)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(80)),
        test_design_service=FakeTestDesignService(_test_design_response(80)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(80)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    step_map = {step["step_name"]: step for step in body["steps"]}
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason_code"] == "insufficient_requirements_detail"
    assert body["user_safe_message"] == "I need a little more detail before I can generate the downstream SDLC planning outputs."
    assert step_map["requirements"]["status"] == "completed"
    assert step_map["jira_story"]["status"] == "blocked"
    assert step_map["test_design"]["status"] == "blocked"
    assert step_map["automation_design"]["status"] == "blocked"
    assert step_map["qa_review"]["status"] == "skipped"
    assert "Confirm export file size expectations." in body["clarification_questions"]


def test_full_mode_runs_real_jira_story_step() -> None:
    client = TestClient(app)
    fake_jira_story = FakeJiraStoryService(_jira_story_response(86))
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(86))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=85, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=fake_jira_story,
        test_design_service=FakeTestDesignService(_test_design_response(86)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(86)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["steps"][2]["step_name"] == "jira_story"
    assert body["steps"][2]["output"]["story_readiness_score"] == 86
    assert fake_jira_story.calls == 1


def test_story_only_mode_runs_real_jira_story_step() -> None:
    client = TestClient(app)
    fake_jira_story = FakeJiraStoryService(_jira_story_response(81))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=83, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(83)),
        jira_story_service=fake_jira_story,
        test_design_service=FakeTestDesignService(_test_design_response(81)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(81)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["steps"][2]["step_name"] == "jira_story"
    assert body["steps"][2]["output"]["story_readiness_score"] == 81
    assert fake_jira_story.calls == 1


def test_low_story_readiness_blocks_downstream_test_and_automation_steps() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=84, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(84)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(61)),
        test_design_service=FakeTestDesignService(_test_design_response(80)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(80)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    step_map = {step["step_name"]: step for step in body["steps"]}
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason_code"] == "insufficient_story_detail"
    assert step_map["jira_story"]["status"] == "completed"
    assert step_map["test_design"]["status"] == "blocked"
    assert step_map["automation_design"]["status"] == "blocked"
    assert step_map["dev_handoff"]["status"] == "blocked"
    assert step_map["qa_review"]["status"] == "skipped"


def test_full_mode_runs_real_test_design_step() -> None:
    client = TestClient(app)
    fake_test_design = FakeTestDesignService(_test_design_response(84))
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(84))
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(84))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=85, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(85)),
        test_design_service=fake_test_design,
        automation_design_service=fake_automation_design,
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["steps"][3]["step_name"] == "test_design"
    assert body["steps"][3]["output"]["test_design_readiness_score"] == 84
    assert fake_test_design.calls == 1
    assert fake_automation_design.calls == 1


def test_test_only_mode_runs_real_test_design_step() -> None:
    client = TestClient(app)
    fake_test_design = FakeTestDesignService(_test_design_response(79))
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(79))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=82, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(82)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(82)),
        test_design_service=fake_test_design,
        automation_design_service=fake_automation_design,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "test_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["steps"][2]["step_name"] == "test_design"
    assert body["steps"][2]["output"]["test_design_readiness_score"] == 79
    assert fake_test_design.calls == 1
    assert fake_automation_design.calls == 0


def test_story_only_mode_does_not_run_test_design() -> None:
    client = TestClient(app)
    fake_test_design = FakeTestDesignService(_test_design_response(82))
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(82))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=83, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(83)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(83)),
        test_design_service=fake_test_design,
        automation_design_service=fake_automation_design,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert "test_design" not in step_names
    assert fake_test_design.calls == 0
    assert fake_automation_design.calls == 0


def test_low_story_readiness_blocks_test_design_when_step_is_reached() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=84, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(84)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(65)),
        test_design_service=FakeTestDesignService(_test_design_response(80)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(80)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    step_map = {step["step_name"]: step for step in body["steps"]}
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert step_map["test_design"]["status"] == "blocked"


def test_low_test_design_readiness_blocks_automation_design() -> None:
    client = TestClient(app)
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=85, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(85)),
        test_design_service=FakeTestDesignService(_test_design_response(62)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(80)),
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    step_map = {step["step_name"]: step for step in body["steps"]}
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason_code"] == "insufficient_test_design_detail"
    assert step_map["test_design"]["status"] == "completed"
    assert step_map["automation_design"]["status"] == "blocked"
    assert step_map["dev_handoff"]["status"] == "skipped"
    assert step_map["qa_review"]["status"] == "skipped"
    assert body["final_output"]["missing_information"] == ["Performance threshold is not fully specified."]


def test_full_mode_runs_real_automation_design_step() -> None:
    client = TestClient(app)
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(86))
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(86))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=85, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(85)),
        test_design_service=FakeTestDesignService(_test_design_response(84)),
        automation_design_service=fake_automation_design,
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["steps"][4]["step_name"] == "automation_design"
    assert body["steps"][4]["output"]["automation_design_readiness_score"] == 86
    assert fake_automation_design.calls == 1


def test_full_mode_runs_real_dev_handoff_step() -> None:
    client = TestClient(app)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(91, safe_for_dev_planning=True))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=86, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(87)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(88)),
        test_design_service=FakeTestDesignService(_test_design_response(86)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(89)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["steps"][5]["step_name"] == "dev_handoff"
    assert body["steps"][5]["output"]["handoff_readiness_score"] == 91
    assert body["final_output"]["dev_handoff"]["safe_for_dev_planning"] is True
    assert fake_dev_handoff.calls == 1


def test_story_only_mode_does_not_run_automation_design() -> None:
    client = TestClient(app)
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(82))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=83, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(83)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(83)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=fake_automation_design,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert "automation_design" not in step_names
    assert fake_automation_design.calls == 0


def test_story_only_mode_does_not_run_dev_handoff() -> None:
    client = TestClient(app)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(85))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=83, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(83)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(83)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(82)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "story_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert "dev_handoff" not in step_names
    assert fake_dev_handoff.calls == 0


def test_test_only_mode_does_not_run_automation_design() -> None:
    client = TestClient(app)
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(82))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=82, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(82)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(82)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=fake_automation_design,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "test_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert "automation_design" not in step_names
    assert fake_automation_design.calls == 0


def test_test_only_mode_does_not_run_dev_handoff() -> None:
    client = TestClient(app)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(85))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=82, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(82)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(82)),
        test_design_service=FakeTestDesignService(_test_design_response(82)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(82)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "test_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert "dev_handoff" not in step_names
    assert fake_dev_handoff.calls == 0


def test_automation_only_mode_blocks_automation_design_when_test_design_is_not_ready() -> None:
    client = TestClient(app)
    fake_automation_design = FakeAutomationDesignService(_automation_design_response(80))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=85, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(85)),
        test_design_service=FakeTestDesignService(_test_design_response(61)),
        automation_design_service=fake_automation_design,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "automation_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    step_map = {step["step_name"]: step for step in body["steps"]}
    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason_code"] == "insufficient_test_design_detail"
    assert step_map["test_design"]["status"] == "completed"
    assert step_map["automation_design"]["status"] == "blocked"
    assert step_map["qa_review"]["status"] == "skipped"
    assert step_map["finalizer"]["status"] == "skipped"
    assert fake_automation_design.calls == 0


def test_automation_only_mode_does_not_run_dev_handoff() -> None:
    client = TestClient(app)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(85))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=85, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(85)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(85)),
        test_design_service=FakeTestDesignService(_test_design_response(85)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(85)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "automation_only",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    step_names = [step["step_name"] for step in response.json()["steps"]]
    assert response.status_code == 200
    assert "dev_handoff" not in step_names
    assert fake_dev_handoff.calls == 0


def test_dev_handoff_handles_low_automation_readiness_without_crashing() -> None:
    client = TestClient(app)
    fake_dev_handoff = FakeDevHandoffService(_dev_handoff_response(85, safe_for_dev_planning=True))
    app.state.workflow_engine = WorkflowEngine(
        intake_service=FakeIntakeService(_intake_response(readiness_score=86, can_continue=True)),
        requirements_service=FakeRequirementsService(_requirements_response(86)),
        jira_story_service=FakeJiraStoryService(_jira_story_response(86)),
        test_design_service=FakeTestDesignService(_test_design_response(86)),
        automation_design_service=FakeAutomationDesignService(_automation_design_response(62)),
        dev_handoff_service=fake_dev_handoff,
    )

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "full",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    dev_handoff_output = body["steps"][5]["output"]
    assert response.status_code == 200
    assert body["status"] == "completed"
    assert dev_handoff_output["handoff_readiness_score"] == 85
    assert dev_handoff_output["safe_for_dev_planning"] is False
    assert "implementation_planning" in dev_handoff_output["not_safe_to_generate"]
    assert any("Automation design readiness is below 70" in item for item in dev_handoff_output["implementation_risks"])
    assert fake_dev_handoff.calls == 1


def test_run_intake_endpoint_remains_unaffected() -> None:
    client = TestClient(app)
    intake_response = _intake_response(
        readiness_score=80,
        can_continue=True,
        clarification_questions=["Confirm export audit fields."],
    )
    app.state.intake_service = FakeIntakeService(intake_response)

    response = client.post(
        "/run-intake",
        json={
            "feature_description": "Add export",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["readiness_score"] == 80
    assert body["feature_intake_packet"]["feature_name"]["value"] == "Feature"


def test_invalid_mode_rejection() -> None:
    client = TestClient(app)

    response = client.post(
        "/run-sdlc-workflow",
        json={
            "feature_description": "Add export",
            "mode": "invalid_mode",
            "context": {},
            "attachments": [],
            "notes": [],
        },
    )

    assert response.status_code == 422
