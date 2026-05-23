import json

from app.models.intake_models import RunIntakeRequest
from app.services.intake_service import IntakeService
from app.services.llm.base_provider import BaseLLMProvider, LLMResponse


VALID_RESULT = {
    "feature_intake_packet": {
        "feature_name": {"value": "Feature", "confidence": "high", "source": "provided", "needs_clarification": False},
        "problem_statement": {"value": "Problem", "confidence": "high", "source": "provided", "needs_clarification": False},
        "business_goal": {"value": "Goal", "confidence": "high", "source": "provided", "needs_clarification": False},
        "target_users": {"value": "Users", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "current_behavior": {"value": "Current", "confidence": "high", "source": "provided", "needs_clarification": False},
        "desired_behavior": {"value": "Desired", "confidence": "high", "source": "provided", "needs_clarification": False},
        "in_scope": {"value": "In scope", "confidence": "high", "source": "provided", "needs_clarification": False},
        "out_of_scope": {"value": "Out scope", "confidence": "high", "source": "provided", "needs_clarification": False},
        "business_rules": {"value": "Rules", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "data_inputs": {"value": "Inputs", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "data_outputs": {"value": "Outputs", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "user_roles_permissions": {"value": "Roles", "confidence": "low", "source": "missing", "needs_clarification": True},
        "systems_impacted": {"value": "Systems", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "api_or_contract_impacts": {"value": "API", "confidence": "low", "source": "missing", "needs_clarification": True},
        "ui_impacts": {"value": "UI", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "reporting_or_audit_needs": {"value": "Audit", "confidence": "low", "source": "missing", "needs_clarification": True},
        "error_handling_expectations": {"value": "Errors", "confidence": "low", "source": "missing", "needs_clarification": True},
        "edge_cases": {"value": "Edge", "confidence": "low", "source": "missing", "needs_clarification": True},
        "non_functional_requirements": {"value": "NFR", "confidence": "low", "source": "missing", "needs_clarification": True},
        "dependencies": {"value": "Deps", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "known_risks": {"value": "Risks", "confidence": "medium", "source": "inferred", "needs_clarification": True},
        "open_questions": {"value": "Questions", "confidence": "high", "source": "provided", "needs_clarification": True},
        "assumptions": {"value": "Assumptions", "confidence": "medium", "source": "inferred", "needs_clarification": True}
    },
    "readiness_score": 72,
    "blocking_gaps": ["Confirm permissions", "Confirm permissions"],
    "clarification_questions": ["Who can access the feature?", "Who can access the feature?"]
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


def test_intake_service_uses_provider_interface() -> None:
    provider = FakeProvider([json.dumps(VALID_RESULT)])
    service = IntakeService(llm_provider=provider)

    response = service.run(
        RunIntakeRequest(
            feature_description="Add export support",
            context={},
            attachments=[],
            notes=[],
        )
    )

    assert len(provider.calls) == 1
    assert response.readiness_score == 72
    assert response.can_continue is True
    assert response.blocking_gaps == ["Confirm permissions"]
    assert response.clarification_questions == ["Who can access the feature?"]


def test_json_repair_works_through_selected_provider() -> None:
    provider = FakeProvider(["not-json", json.dumps(VALID_RESULT)])
    service = IntakeService(llm_provider=provider)

    response = service.run(
        RunIntakeRequest(
            feature_description="Add export support",
            context={},
            attachments=[],
            notes=[],
        )
    )

    assert len(provider.calls) == 2
    assert "repair_invalid_intake_json" in str(provider.calls[1]["user_prompt"])
    assert response.readiness_score == 72
