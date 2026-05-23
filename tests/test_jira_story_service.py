import json

from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentRequest
from app.models.requirements_models import RequirementsAgentResult
from app.services.jira_story_service import JiraStoryService
from app.services.llm.base_provider import BaseLLMProvider, LLMResponse


VALID_JIRA_STORY_RESULT = {
    "summary": "Add CSV export for filtered release readiness view",
    "story_type": "story",
    "description": "Enable authorized dashboard users to export the currently filtered release readiness view as CSV. The export should preserve active filters, include a UTC export timestamp, and record an audit event for each export attempt. This draft excludes scheduling, PDF export, and historical archive storage.",
    "user_story": {
        "as_a": "program manager",
        "i_want": "to export the filtered release readiness dashboard view as CSV",
        "so_that": "I can share accurate stakeholder updates without manually copying rows",
    },
    "acceptance_criteria": [
        {
            "id": "AC-001",
            "criterion": "Authorized users can export only the currently visible filtered readiness rows as CSV.",
            "given_when_then": {
                "given": "an authorized user is viewing the filtered release readiness dashboard",
                "when": "the user triggers Export CSV",
                "then": "the generated CSV contains only the currently visible filtered rows",
            },
            "source_requirement_ids": ["FR-001", "BR-001"],
            "confidence": "high",
        }
    ],
    "business_rules_referenced": ["BR-001"],
    "dependencies": ["reporting-service export capability", "audit-logging-service event capture"],
    "assumptions": ["Assume existing visibility rules can be reused for export authorization."],
    "open_questions": [],
    "labels": ["reporting", "csv-export"],
    "components": ["release-readiness-dashboard-ui", "reporting-service"],
    "definition_of_done": [
        "Story reviewed by product and engineering.",
        "Open questions are resolved or explicitly accepted as assumptions.",
    ],
    "out_of_scope": ["Scheduled delivery", "PDF export", "Historical archive storage"],
    "story_readiness_score": 83,
    "safe_for_test_design": True,
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
            "role_permission_requirements": [],
            "assumptions": ["Assume existing visibility rules can be reused."],
            "open_questions": [] if score >= 70 else ["Confirm export size expectations."],
            "risks": ["Large exports may be slow."],
            "requirements_readiness_score": score,
            "safe_for_jira_story_generation": score >= 70,
            "safe_for_test_design": score >= 70,
            "not_safe_to_generate": [] if score >= 70 else ["jira_story_generation"],
        }
    )


def _build_request() -> JiraStoryAgentRequest:
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
    return JiraStoryAgentRequest(
        feature_description="Add CSV export for the filtered release readiness dashboard view.",
        feature_intake_packet=packet,
        intake_summary=intake_summary,
        requirements_result=requirements_result,
        previous_workflow_outputs={
            "intake": intake_summary.model_dump(mode="json"),
            "requirements": requirements_result.model_dump(mode="json"),
        },
    )


def test_jira_story_service_parses_valid_response() -> None:
    provider = FakeProvider([json.dumps(VALID_JIRA_STORY_RESULT)])
    service = JiraStoryService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 1
    assert response.story_readiness_score == 83
    assert response.summary == "Add CSV export for filtered release readiness view"
    assert response.acceptance_criteria[0].source_requirement_ids == ["FR-001", "BR-001"]


def test_jira_story_service_repairs_invalid_json_once() -> None:
    provider = FakeProvider(["not-json", json.dumps(VALID_JIRA_STORY_RESULT)])
    service = JiraStoryService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 2
    assert "repair_invalid_jira_story_json" in str(provider.calls[1]["user_prompt"])
    assert response.story_readiness_score == 83
