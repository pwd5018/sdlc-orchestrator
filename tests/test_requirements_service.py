import json

from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.requirements_models import RequirementsAgentRequest
from app.services.llm.base_provider import BaseLLMProvider, LLMResponse
from app.services.requirements_service import RequirementsService


VALID_REQUIREMENTS_RESULT = {
    "functional_requirements": [
        {
            "id": "FR-001",
            "requirement": "Authorized users can export the currently filtered release readiness view as CSV.",
            "source": "provided",
            "confidence": "high",
            "acceptance_hint": "Verify exported rows match the visible filtered dataset.",
            "related_business_rules": ["BR-001"],
            "open_questions": []
        }
    ],
    "non_functional_requirements": [
        {
            "id": "NFR-001",
            "requirement": "Normal CSV export requests should begin promptly for standard result sizes.",
            "category": "performance",
            "source": "inferred",
            "confidence": "medium",
            "measurement_hint": "Confirm an acceptable response-time threshold.",
            "open_questions": ["What response time target is acceptable for standard exports?"]
        }
    ],
    "business_rules": [
        {
            "id": "BR-001",
            "rule": "Export must respect the currently applied dashboard filters.",
            "source": "provided",
            "confidence": "high",
            "impacted_requirements": ["FR-001"],
            "open_questions": []
        }
    ],
    "data_requirements": [
        {
            "id": "DR-001",
            "data_element": "Active filter set",
            "description": "The applied dashboard filters used to scope exported records.",
            "input_or_output": "input",
            "validation_rules": ["Filters should be captured exactly as applied at export time."],
            "source": "provided",
            "confidence": "high",
            "open_questions": []
        }
    ],
    "integration_requirements": [
        {
            "id": "IR-001",
            "system": "reporting-service",
            "interaction": "Generate CSV content for the filtered readiness dataset.",
            "api_or_contract_impact": "May require an export endpoint or reporting contract extension.",
            "source": "inferred",
            "confidence": "medium",
            "open_questions": ["Should export use a new endpoint or extend an existing reporting contract?"]
        }
    ],
    "role_permission_requirements": [
        {
            "id": "RP-001",
            "role": "program manager",
            "allowed_actions": ["Export visible readiness records"],
            "restricted_actions": ["Export records outside assigned visibility scope"],
            "source": "provided",
            "confidence": "high",
            "open_questions": []
        }
    ],
    "assumptions": ["Assume existing visibility rules are already enforced in the reporting layer."],
    "open_questions": ["What response time target is acceptable for standard exports?"],
    "risks": ["Permission drift between UI visibility and export behavior could expose incorrect rows."],
    "requirements_readiness_score": 78,
    "safe_for_jira_story_generation": True,
    "safe_for_test_design": True,
    "not_safe_to_generate": ["finalized_test_cases_without_performance_target_confirmation"]
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


def _build_request() -> RequirementsAgentRequest:
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
    return RequirementsAgentRequest(
        feature_description="Add CSV export for the filtered release readiness dashboard view.",
        feature_intake_packet=packet,
        intake_summary=intake_summary,
        previous_workflow_outputs={"intake": intake_summary.model_dump(mode="json")},
    )


def test_requirements_service_parses_valid_response() -> None:
    provider = FakeProvider([json.dumps(VALID_REQUIREMENTS_RESULT)])
    service = RequirementsService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 1
    assert response.requirements_readiness_score == 78
    assert response.functional_requirements[0].id == "FR-001"
    assert response.safe_for_jira_story_generation is True


def test_requirements_service_repairs_invalid_json_once() -> None:
    provider = FakeProvider(["not-json", json.dumps(VALID_REQUIREMENTS_RESULT)])
    service = RequirementsService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 2
    assert "repair_invalid_requirements_json" in str(provider.calls[1]["user_prompt"])
    assert response.requirements_readiness_score == 78


def test_requirements_service_normalizes_missing_readiness_fields_after_repair() -> None:
    repaired_result = dict(VALID_REQUIREMENTS_RESULT)
    repaired_result.pop("requirements_readiness_score")
    repaired_result.pop("safe_for_jira_story_generation")
    repaired_result.pop("safe_for_test_design")

    provider = FakeProvider(["not-json", json.dumps(repaired_result)])
    service = RequirementsService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 2
    assert response.requirements_readiness_score >= 70
    assert response.safe_for_jira_story_generation is True
    assert response.safe_for_test_design is True
