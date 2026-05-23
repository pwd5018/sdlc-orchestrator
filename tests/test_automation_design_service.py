import json

from app.models.automation_design_models import AutomationDesignAgentRequest
from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentResult as DesignResultModel
from app.services.automation_design_service import AutomationDesignService
from app.services.llm.base_provider import BaseLLMProvider, LLMResponse


VALID_AUTOMATION_DESIGN_RESULT = {
    "automation_strategy_summary": "Prioritize stable API and contract coverage first, then add focused UI automation around export initiation and authorization-sensitive behavior.",
    "recommended_test_layers": [
        {
            "layer": "api",
            "recommendation": "Cover export request validation, filter handling, and authorization at the service boundary.",
            "reasoning": "The export behavior depends on inputs and permissions that are more stable to verify through service-level checks than through UI-only automation.",
            "confidence": "high",
        },
        {
            "layer": "ui",
            "recommendation": "Add a thin UI layer for export entry-point behavior and visible success or failure feedback.",
            "reasoning": "The button placement and user feedback are important user-facing risks, but deep file-content validation should stay below the UI layer.",
            "confidence": "medium",
        },
    ],
    "automation_candidates": [
        {
            "id": "AT-001",
            "title": "Authorized user exports filtered readiness results",
            "recommended_layer": "api",
            "priority": "critical",
            "business_risk": "A mismatch between visible rows and exported rows could create incorrect reporting.",
            "recommended_approach": "Validate filter propagation, permission handling, and export payload behavior through repeatable service-level checks before adding a thin end-to-end confirmation path.",
            "source_test_scenario_ids": ["TS-001"],
            "estimated_stability": "high",
            "confidence": "high",
        }
    ],
    "api_test_recommendations": [
        {
            "id": "API-001",
            "recommendation": "Validate that the export request preserves active filters and user identity context.",
            "reasoning": "Incorrect request translation would produce misleading files even if UI behavior appears correct.",
            "contract_or_endpoint": "POST /reports/readiness/export",
            "confidence": "high",
        }
    ],
    "ui_test_recommendations": [
        {
            "id": "UI-001",
            "recommendation": "Automate only the core export trigger path plus visible success and error feedback.",
            "selector_or_hook_needs": ["Stable hook for Export CSV trigger", "Stable hook for export status toast or inline message"],
            "stability_risks": ["Dynamic table rendering may make row-level UI assertions brittle", "File-download timing can be environment-sensitive"],
            "confidence": "medium",
        }
    ],
    "contract_test_recommendations": [
        {
            "id": "CT-001",
            "recommendation": "Add a contract check between dashboard requests and reporting-service export input expectations.",
            "systems_involved": ["dashboard-ui", "reporting-service"],
            "risk_if_missing": "A quiet contract drift could break exports without obvious UI regressions until late testing.",
            "confidence": "high",
        }
    ],
    "test_data_requirements": [
        {
            "id": "TD-001",
            "data_need": "Permission-scoped datasets with overlapping filter combinations",
            "purpose": "Verify that exports respect both filters and visibility rules.",
            "risk": "Weak datasets may hide authorization or filtering mismatches.",
            "confidence": "high",
        }
    ],
    "flaky_risk_areas": [
        {
            "id": "FR-001",
            "risk_area": "Browser download timing and asynchronous export status updates",
            "why_risky": "UI checks may race against background export creation or toast rendering.",
            "mitigation_recommendation": "Prefer API-layer assertions for content and use stable UI hooks plus explicit status signals for thin end-to-end checks.",
            "confidence": "high",
        }
    ],
    "recommended_test_hooks": [
        "Add a stable UI hook for the Export CSV trigger.",
        "Expose a deterministic export request identifier in non-production test environments if available.",
    ],
    "recommended_logging_or_observability": [
        "Log export request outcome with filter summary and actor role.",
        "Expose a traceable audit event or request correlation identifier for export attempts.",
    ],
    "assumptions": ["Assume the reporting service owns the actual CSV generation logic."],
    "open_questions": ["What response contract will represent a successful export start versus a completed file delivery?"],
    "automation_design_readiness_score": 84,
    "safe_for_implementation_planning": True,
    "not_safe_to_generate": [],
}


class FakeProvider(BaseLLMProvider):
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def generate_json(self, system_prompt: str, user_prompt: str, response_schema=None, temperature: float = 0.2) -> LLMResponse:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "temperature": temperature,
            }
        )
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=self.model_name,
            content=self.responses.pop(0),
        )


def _field(value: str, confidence: str = "high", source: str = "provided", needs_clarification: bool = False) -> PacketField:
    return PacketField(
        value=value,
        confidence=confidence,
        source=source,
        needs_clarification=needs_clarification,
    )


def _requirements_response() -> RequirementsAgentResult:
    return RequirementsAgentResult.model_validate(
        {
            "functional_requirements": [
                {
                    "id": "FR-001",
                    "requirement": "Authorized users can export the currently filtered release readiness view as CSV.",
                    "source": "provided",
                    "confidence": "high",
                    "acceptance_hint": "Export contains the visible filtered rows only.",
                    "related_business_rules": ["BR-001"],
                    "open_questions": [],
                }
            ],
            "non_functional_requirements": [],
            "business_rules": [
                {
                    "id": "BR-001",
                    "rule": "Export must respect active filters and current user visibility rules.",
                    "source": "provided",
                    "confidence": "high",
                    "impacted_requirements": ["FR-001"],
                    "open_questions": [],
                }
            ],
            "data_requirements": [],
            "integration_requirements": [
                {
                    "id": "IR-001",
                    "system": "reporting-service",
                    "interaction": "Generate CSV export using filters and caller identity.",
                    "api_or_contract_impact": "Candidate export endpoint contract.",
                    "source": "provided",
                    "confidence": "high",
                    "open_questions": [],
                }
            ],
            "role_permission_requirements": [],
            "assumptions": ["Assume export authorization should follow existing visibility rules."],
            "open_questions": [],
            "risks": ["Permission drift could expose incorrect rows."],
            "requirements_readiness_score": 84,
            "safe_for_jira_story_generation": True,
            "safe_for_test_design": True,
            "not_safe_to_generate": [],
        }
    )


def _jira_story_response() -> JiraStoryAgentResult:
    return JiraStoryAgentResult.model_validate(
        {
            "summary": "Add CSV export for filtered release readiness view",
            "story_type": "story",
            "description": "Enable authorized users to export the current filtered dashboard view as CSV with audit logging.",
            "user_story": {
                "as_a": "program manager",
                "i_want": "to export the current filtered release readiness view as CSV",
                "so_that": "I can share accurate updates without manual spreadsheet work",
            },
            "acceptance_criteria": [
                {
                    "id": "AC-001",
                    "criterion": "Authorized users can export only the visible filtered rows.",
                    "given_when_then": {
                        "given": "an authorized user is viewing filtered results",
                        "when": "the user selects Export CSV",
                        "then": "the exported file contains only the visible filtered rows",
                    },
                    "source_requirement_ids": ["FR-001"],
                    "confidence": "high",
                }
            ],
            "business_rules_referenced": ["BR-001"],
            "dependencies": ["reporting-service", "audit-log-service"],
            "assumptions": [],
            "open_questions": [],
            "labels": ["reporting", "csv-export"],
            "components": ["dashboard-ui", "reporting-service"],
            "definition_of_done": ["Story reviewed and clarified."],
            "out_of_scope": ["Scheduled exports"],
            "story_readiness_score": 85,
            "safe_for_test_design": True,
            "safe_for_automation_design": True,
            "not_safe_to_generate": [],
        }
    )


def _test_design_response() -> DesignResultModel:
    return DesignResultModel.model_validate(
        {
            "test_design_summary": "Cover export behavior across happy path, permissions, failures, and data variation.",
            "coverage_strategy": {
                "primary_risks": ["Incorrect export contents", "Permission drift", "Poor failure handling"],
                "critical_business_rules": ["BR-001"],
                "recommended_test_levels": ["api", "ui", "integration"],
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
                    "expected_results": ["CSV is generated.", "Rows match visible filtered results."],
                    "source_requirement_ids": ["FR-001"],
                    "source_acceptance_criteria_ids": ["AC-001"],
                    "assumptions": [],
                    "open_questions": [],
                    "automation_candidate": True,
                    "confidence": "high",
                }
            ],
            "role_permission_tests": [],
            "data_variation_tests": [],
            "negative_tests": ["Unauthorized export attempt"],
            "edge_cases": ["Large result sets"],
            "regression_impact_areas": ["Dashboard filtering", "Audit logging"],
            "untestable_or_unclear_items": [],
            "assumptions": [],
            "open_questions": [],
            "test_design_readiness_score": 83,
            "safe_for_automation_design": True,
            "not_safe_to_generate": [],
        }
    )


def _build_request() -> AutomationDesignAgentRequest:
    packet = FeatureIntakePacket(
        feature_name=_field("Export filtered release readiness summary as CSV"),
        problem_statement=_field("Manual spreadsheet preparation is slow and error-prone."),
        business_goal=_field("Reduce reporting effort and improve accuracy."),
        target_users=_field("Program managers and release coordinators."),
        current_behavior=_field("Users manually copy filtered rows into spreadsheets."),
        desired_behavior=_field("Users export the filtered view as CSV."),
        in_scope=_field("On-demand CSV export from the dashboard."),
        out_of_scope=_field("No scheduled export or PDF export."),
        business_rules=_field("Export must respect active filters and existing permissions."),
        data_inputs=_field("Active filters and visible readiness rows."),
        data_outputs=_field("CSV file and audit event."),
        user_roles_permissions=_field("Program managers can export; unauthorized users cannot."),
        systems_impacted=_field("Dashboard UI, reporting service, audit log service."),
        api_or_contract_impacts=_field("Potential reporting export endpoint.", confidence="medium", source="inferred", needs_clarification=True),
        ui_impacts=_field("Add Export CSV button near filters."),
        reporting_or_audit_needs=_field("Record export attempts in audit logs."),
        error_handling_expectations=_field("Show a friendly error and avoid partial files."),
        edge_cases=_field("Empty result sets and very large result sets."),
        non_functional_requirements=_field("Exports should begin quickly for standard datasets.", confidence="medium", source="inferred", needs_clarification=True),
        dependencies=_field("Reporting service support and permission confirmation."),
        known_risks=_field("Permission drift and performance issues on large exports."),
        open_questions=_field("Performance target and exact API contract remain open.", confidence="medium", source="inferred", needs_clarification=True),
        assumptions=_field("Existing visibility rules can be reused.", confidence="medium", source="inferred", needs_clarification=True),
    )
    intake_summary = RunIntakeResponse(
        feature_intake_packet=packet,
        readiness_score=82,
        can_continue=True,
        blocking_gaps=[],
        clarification_questions=["Confirm performance target."],
        safe_to_generate=["draft_sdlc_package"],
        not_safe_to_generate=[],
    )
    requirements_result = _requirements_response()
    jira_story_result = _jira_story_response()
    test_design_result = _test_design_response()
    return AutomationDesignAgentRequest(
        feature_description="Add CSV export for the filtered release readiness dashboard view.",
        feature_intake_packet=packet,
        intake_summary=intake_summary,
        requirements_result=requirements_result,
        jira_story_result=jira_story_result,
        test_design_result=test_design_result,
        previous_workflow_outputs={
            "intake": intake_summary.model_dump(mode="json"),
            "requirements": requirements_result.model_dump(mode="json"),
            "jira_story": jira_story_result.model_dump(mode="json"),
            "test_design": test_design_result.model_dump(mode="json"),
        },
    )


def test_automation_design_service_parses_valid_response() -> None:
    provider = FakeProvider([json.dumps(VALID_AUTOMATION_DESIGN_RESULT)])
    service = AutomationDesignService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 1
    assert response.automation_design_readiness_score == 84
    assert response.automation_candidates[0].id == "AT-001"
    assert response.ui_test_recommendations[0].selector_or_hook_needs


def test_automation_design_service_repairs_invalid_json_once() -> None:
    provider = FakeProvider(["not-json", json.dumps(VALID_AUTOMATION_DESIGN_RESULT)])
    service = AutomationDesignService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 2
    assert "repair_invalid_automation_design_json" in str(provider.calls[1]["user_prompt"])
    assert response.automation_design_readiness_score == 84
