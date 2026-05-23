import json

from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentRequest as DesignRequestModel
from app.services.llm.base_provider import BaseLLMProvider, LLMResponse
from app.services.test_design_service import TestDesignService as DesignServiceUnderTest


VALID_TEST_DESIGN_RESULT = {
    "test_design_summary": "Cover CSV export behavior across happy-path, permission, error handling, data variation, and regression-sensitive scenarios.",
    "coverage_strategy": {
        "primary_risks": [
            "Permission drift between visible rows and exported rows",
            "Incorrect export contents when filters are active",
            "Failures during export generation leaving users without a clear result"
        ],
        "critical_business_rules": [
            "BR-001",
            "Export must include UTC timestamp metadata"
        ],
        "recommended_test_levels": ["api", "ui", "integration", "regression", "performance"],
    },
    "test_scenarios": [
        {
            "id": "TS-001",
            "title": "Authorized user exports the currently filtered readiness view",
            "type": "happy_path",
            "priority": "critical",
            "description": "Validate that an authorized user can export exactly the visible filtered rows as CSV.",
            "preconditions": ["A program manager has access to the release readiness dashboard."],
            "test_data": ["A filtered dashboard view with multiple visible rows."],
            "steps": [
                "Open the dashboard as an authorized user.",
                "Apply product line and environment filters.",
                "Trigger Export CSV."
            ],
            "expected_results": [
                "A CSV file is generated successfully.",
                "The CSV contains only the visible filtered rows.",
                "The export metadata includes the active filters and a UTC timestamp."
            ],
            "source_requirement_ids": ["FR-001"],
            "source_acceptance_criteria_ids": ["AC-001"],
            "assumptions": [],
            "open_questions": [],
            "automation_candidate": True,
            "confidence": "high",
        }
    ],
    "role_permission_tests": [
        {
            "id": "RPT-001",
            "role": "program manager",
            "allowed_actions": ["Export filtered readiness rows"],
            "restricted_actions": ["Export rows outside current visibility scope"],
            "test_notes": ["Confirm export authorization matches current dashboard visibility rules."],
            "source": "provided",
            "confidence": "high",
        }
    ],
    "data_variation_tests": [
        {
            "id": "DVT-001",
            "data_condition": "Filtered result set is empty",
            "expected_behavior": "The user receives a clear empty-state export result or guidance without incorrect data rows.",
            "risk": "Empty datasets may produce confusing blank files or misleading success feedback.",
            "confidence": "medium",
        }
    ],
    "negative_tests": [
        "Export generation fails after the user triggers the action.",
        "An unauthorized user attempts to export."
    ],
    "edge_cases": [
        "Very large filtered result sets",
        "Permissions change during export generation"
    ],
    "regression_impact_areas": [
        "Dashboard filtering behavior",
        "Audit event creation",
        "Reporting glossary column naming"
    ],
    "untestable_or_unclear_items": [
        "Exact acceptable response-time threshold for large exports is not fully specified."
    ],
    "assumptions": ["Assume existing dashboard visibility rules should be reused for export authorization."],
    "open_questions": ["What is the exact performance threshold for standard and large exports?"],
    "test_design_readiness_score": 81,
    "safe_for_automation_design": True,
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


def _requirements_response(score: int = 82) -> RequirementsAgentResult:
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
                    "rule": "Export must respect active filters.",
                    "source": "provided",
                    "confidence": "high",
                    "impacted_requirements": ["FR-001"],
                    "open_questions": [],
                }
            ],
            "data_requirements": [],
            "integration_requirements": [],
            "role_permission_requirements": [
                {
                    "id": "RP-001",
                    "role": "program manager",
                    "allowed_actions": ["Export visible readiness records"],
                    "restricted_actions": ["Export records outside assigned visibility scope"],
                    "source": "provided",
                    "confidence": "high",
                    "open_questions": [],
                }
            ],
            "assumptions": ["Assume existing visibility rules can be reused."],
            "open_questions": [],
            "risks": ["Large exports may be slow."],
            "requirements_readiness_score": score,
            "safe_for_jira_story_generation": score >= 70,
            "safe_for_test_design": score >= 70,
            "not_safe_to_generate": [],
        }
    )


def _jira_story_response(score: int = 83) -> JiraStoryAgentResult:
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
            ],
            "business_rules_referenced": ["BR-001"],
            "dependencies": ["reporting-service", "audit-logging-service"],
            "assumptions": [],
            "open_questions": [],
            "labels": ["reporting", "csv-export"],
            "components": ["dashboard-ui", "reporting-service"],
            "definition_of_done": ["Story reviewed and clarified."],
            "out_of_scope": ["Scheduled exports", "PDF export"],
            "story_readiness_score": score,
            "safe_for_test_design": score >= 70,
            "safe_for_automation_design": score >= 70,
            "not_safe_to_generate": [],
        }
    )


def _build_request() -> DesignRequestModel:
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
    return DesignRequestModel(
        feature_description="Add CSV export for the filtered release readiness dashboard view.",
        feature_intake_packet=packet,
        intake_summary=intake_summary,
        requirements_result=requirements_result,
        jira_story_result=jira_story_result,
        previous_workflow_outputs={
            "intake": intake_summary.model_dump(mode="json"),
            "requirements": requirements_result.model_dump(mode="json"),
            "jira_story": jira_story_result.model_dump(mode="json"),
        },
    )


def test_test_design_service_parses_valid_response() -> None:
    provider = FakeProvider([json.dumps(VALID_TEST_DESIGN_RESULT)])
    service = DesignServiceUnderTest(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 1
    assert response.test_design_readiness_score == 81
    assert response.test_scenarios[0].id == "TS-001"
    assert response.test_scenarios[0].source_acceptance_criteria_ids == ["AC-001"]


def test_test_design_service_repairs_invalid_json_once() -> None:
    provider = FakeProvider(["not-json", json.dumps(VALID_TEST_DESIGN_RESULT)])
    service = DesignServiceUnderTest(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 2
    assert "repair_invalid_test_design_json" in str(provider.calls[1]["user_prompt"])
    assert response.test_design_readiness_score == 81
