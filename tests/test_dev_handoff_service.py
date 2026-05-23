import json

from app.models.automation_design_models import AutomationDesignAgentResult
from app.models.dev_handoff_models import DevHandoffAgentRequest
from app.models.intake_models import FeatureIntakePacket, PacketField, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentResult as DesignResultModel
from app.services.dev_handoff_service import DevHandoffService
from app.services.llm.base_provider import BaseLLMProvider, LLMResponse


VALID_DEV_HANDOFF_RESULT = {
    "developer_summary": "Implement digest configuration management across UI, API, persistence, authorization, and audit logging without expanding into new delivery channels.",
    "implementation_scope": {
        "in_scope": [
            "Digest configuration create and update flow",
            "Permission-aware management controls",
            "Audit logging for config changes and send attempts",
        ],
        "out_of_scope": [
            "SMS delivery",
            "Teams integration",
        ],
        "assumptions": [
            "The notification service already supports outbound email delivery once configuration is supplied."
        ],
    },
    "ui_impacts": [
        {
            "id": "UI-001",
            "area": "digest settings panel",
            "change": "Add create and edit controls for recipient, frequency, severity, and quiet-hours configuration.",
            "user_roles_impacted": ["customer_success_manager", "support_lead"],
            "validation_or_state_notes": [
                "Show validation feedback for invalid recipient entries or quiet-hours windows.",
                "Hide or disable controls for unauthorized roles.",
            ],
            "confidence": "high",
        }
    ],
    "api_impacts": [
        {
            "id": "API-001",
            "endpoint_or_contract": "POST /account-health/digests",
            "change": "Persist a new digest configuration with recipient, frequency, filters, and quiet-hours settings.",
            "request_response_notes": [
                "Server-side validation must align with the UI form rules.",
                "Caller identity and tenant scope must be enforced on write operations.",
            ],
            "error_handling_notes": [
                "Return field-level validation failures and clear authorization-denied outcomes.",
            ],
            "confidence": "high",
        }
    ],
    "data_model_impacts": [
        {
            "id": "DATA-001",
            "entity_or_table": "digest_configuration",
            "change": "Store digest recipient, schedule, filter, and audit metadata.",
            "fields_or_attributes": [
                "recipient list",
                "frequency",
                "severity filters",
                "quiet-hours window",
                "last modified by",
            ],
            "migration_needed": "unknown",
            "confidence": "medium",
        }
    ],
    "integration_impacts": [
        {
            "id": "INT-001",
            "system": "notification-service",
            "interaction": "Use existing outbound delivery capability for digest sends and test-send behavior.",
            "risk": "Exact request contract may need clarification before implementation estimates are final.",
            "confidence": "medium",
        }
    ],
    "configuration_impacts": [
        {
            "id": "CFG-001",
            "setting": "default_quiet_hours_window",
            "purpose": "Provide an operational default for digest quiet hours.",
            "default_value": "unknown",
            "admin_configurable": True,
            "confidence": "medium",
        }
    ],
    "audit_logging_requirements": [
        {
            "id": "LOG-001",
            "event": "digest configuration updated",
            "fields_to_capture": [
                "actor identity",
                "actor role",
                "timestamp",
                "digest configuration id",
                "changed fields summary",
            ],
            "reason": "Support traceability for operational and compliance review.",
            "confidence": "high",
        }
    ],
    "error_handling_requirements": [
        {
            "id": "ERR-001",
            "condition": "Notification service is unavailable during test-send or delivery initiation.",
            "expected_behavior": "Do not report success, preserve saved configuration state, and show a retry-capable failure outcome.",
            "user_message_needed": True,
            "confidence": "high",
        }
    ],
    "developer_tasks": [
        {
            "id": "DEV-001",
            "title": "Align digest configuration contract",
            "description": "Confirm the request and response shape for create, update, list, and test-send operations across UI and backend boundaries.",
            "area": "api",
            "depends_on": [],
            "confidence": "high",
        },
        {
            "id": "DEV-002",
            "title": "Plan persistence and audit capture",
            "description": "Identify storage responsibilities, tracked fields, and audit events required for configuration changes and delivery attempts.",
            "area": "data",
            "depends_on": ["DEV-001"],
            "confidence": "medium",
        }
    ],
    "definition_of_done": [
        "Authorized users can manage digest configurations.",
        "Unauthorized users cannot access digest management actions.",
        "Audit events are produced for configuration changes and send attempts.",
    ],
    "implementation_risks": [
        "The notification-service request contract may be underspecified for send-test and delivery outcomes."
    ],
    "open_questions": [
        "Should test-send use the same delivery path as scheduled digest delivery?"
    ],
    "handoff_readiness_score": 83,
    "safe_for_dev_planning": True,
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
                    "requirement": "Authorized users can create and update account-health digest configurations.",
                    "source": "provided",
                    "confidence": "high",
                    "acceptance_hint": "Changes persist and reflect current permission rules.",
                    "related_business_rules": ["BR-001"],
                    "open_questions": [],
                }
            ],
            "non_functional_requirements": [],
            "business_rules": [
                {
                    "id": "BR-001",
                    "rule": "Only authorized roles can manage digest configurations.",
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
                    "system": "notification-service",
                    "interaction": "Deliver configured account-health digest notifications.",
                    "api_or_contract_impact": "May require contract clarification for test-send and delivery result handling.",
                    "source": "provided",
                    "confidence": "medium",
                    "open_questions": [],
                }
            ],
            "role_permission_requirements": [],
            "assumptions": [],
            "open_questions": [],
            "risks": ["Notification-service contract details may still need clarification."],
            "requirements_readiness_score": 84,
            "safe_for_jira_story_generation": True,
            "safe_for_test_design": True,
            "not_safe_to_generate": [],
        }
    )


def _jira_story_response() -> JiraStoryAgentResult:
    return JiraStoryAgentResult.model_validate(
        {
            "summary": "Manage account health digest configurations",
            "story_type": "story",
            "description": "Allow authorized users to manage digest settings for account health notifications.",
            "user_story": {
                "as_a": "customer success manager",
                "i_want": "to manage digest settings for account health alerts",
                "so_that": "stakeholders receive the right summaries without manual work",
            },
            "acceptance_criteria": [],
            "business_rules_referenced": ["BR-001"],
            "dependencies": ["notification-service", "audit-log-service"],
            "assumptions": [],
            "open_questions": [],
            "labels": ["notifications", "account-health"],
            "components": ["dashboard-ui", "notification-service"],
            "definition_of_done": ["Story reviewed and clarified."],
            "out_of_scope": ["SMS delivery"],
            "story_readiness_score": 84,
            "safe_for_test_design": True,
            "safe_for_automation_design": True,
            "not_safe_to_generate": [],
        }
    )


def _test_design_response() -> DesignResultModel:
    return DesignResultModel.model_validate(
        {
            "test_design_summary": "Cover digest create, update, permissions, and failure handling.",
            "coverage_strategy": {
                "primary_risks": ["Permission gaps", "Validation drift", "Notification-service failures"],
                "critical_business_rules": ["BR-001"],
                "recommended_test_levels": ["api", "ui", "integration"],
            },
            "test_scenarios": [],
            "role_permission_tests": [],
            "data_variation_tests": [],
            "negative_tests": ["Unauthorized management attempt"],
            "edge_cases": ["Duplicate recipient entries"],
            "regression_impact_areas": ["Notification preferences", "Audit logging"],
            "untestable_or_unclear_items": [],
            "assumptions": [],
            "open_questions": [],
            "test_design_readiness_score": 82,
            "safe_for_automation_design": True,
            "not_safe_to_generate": [],
        }
    )


def _automation_design_response() -> AutomationDesignAgentResult:
    return AutomationDesignAgentResult.model_validate(
        {
            "automation_strategy_summary": "Cover API validation and permission behavior first, then add thin UI checks for the configuration flow.",
            "recommended_test_layers": [],
            "automation_candidates": [],
            "api_test_recommendations": [],
            "ui_test_recommendations": [],
            "contract_test_recommendations": [],
            "test_data_requirements": [],
            "flaky_risk_areas": [],
            "recommended_test_hooks": [],
            "recommended_logging_or_observability": [],
            "assumptions": [],
            "open_questions": [],
            "automation_design_readiness_score": 80,
            "safe_for_implementation_planning": True,
            "not_safe_to_generate": [],
        }
    )


def _build_request() -> DevHandoffAgentRequest:
    packet = FeatureIntakePacket(
        feature_name=_field("Account health digest management"),
        problem_statement=_field("Users need a controlled way to configure recurring account health notification digests."),
        business_goal=_field("Reduce manual follow-up and improve stakeholder communication."),
        target_users=_field("Customer success managers and support leads."),
        current_behavior=_field("Notification summaries are managed manually outside the dashboard."),
        desired_behavior=_field("Authorized users configure digest recipients, frequency, and filters from the product."),
        in_scope=_field("Create, update, and manage digest configuration plus delivery planning."),
        out_of_scope=_field("SMS delivery and cross-project preferences."),
        business_rules=_field("Only authorized roles can manage digest configurations."),
        data_inputs=_field("Recipients, frequency, severity filters, quiet-hours window."),
        data_outputs=_field("Saved digest configuration metadata and audit events."),
        user_roles_permissions=_field("Only authorized roles can create or update digest settings."),
        systems_impacted=_field("Dashboard UI, notification-service, authorization-service, audit-log-service."),
        api_or_contract_impacts=_field("Digest management endpoints and notification-service contract touchpoints."),
        ui_impacts=_field("Digest settings panel and permission-aware management controls."),
        reporting_or_audit_needs=_field("Audit log configuration changes and send attempts."),
        error_handling_expectations=_field("Show actionable validation and delivery failure feedback."),
        edge_cases=_field("Duplicate recipients, invalid quiet-hours window, notification-service failure."),
        non_functional_requirements=_field("Responsive save experience and strong auditability."),
        dependencies=_field("Existing notification-service and authorization-service."),
        known_risks=_field("Contract ambiguity and permission drift."),
        open_questions=_field("Clarify send-test behavior and delivery outcome contract.", confidence="medium", source="inferred", needs_clarification=True),
        assumptions=_field("Existing outbound delivery can be reused.", confidence="medium", source="inferred", needs_clarification=True),
    )
    intake_summary = RunIntakeResponse(
        feature_intake_packet=packet,
        readiness_score=84,
        can_continue=True,
        blocking_gaps=[],
        clarification_questions=[],
        safe_to_generate=["draft_sdlc_package"],
        not_safe_to_generate=[],
    )
    requirements_result = _requirements_response()
    jira_story_result = _jira_story_response()
    test_design_result = _test_design_response()
    automation_design_result = _automation_design_response()
    return DevHandoffAgentRequest(
        feature_description="Plan the implementation handoff for account health digest management.",
        feature_intake_packet=packet,
        intake_summary=intake_summary,
        requirements_result=requirements_result,
        jira_story_result=jira_story_result,
        test_design_result=test_design_result,
        automation_design_result=automation_design_result,
        previous_workflow_outputs={
            "intake": intake_summary.model_dump(mode="json"),
            "requirements": requirements_result.model_dump(mode="json"),
            "jira_story": jira_story_result.model_dump(mode="json"),
            "test_design": test_design_result.model_dump(mode="json"),
            "automation_design": automation_design_result.model_dump(mode="json"),
        },
    )


def test_dev_handoff_service_parses_valid_response() -> None:
    provider = FakeProvider([json.dumps(VALID_DEV_HANDOFF_RESULT)])
    service = DevHandoffService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 1
    assert response.handoff_readiness_score == 83
    assert response.developer_tasks[0].id == "DEV-001"
    assert response.ui_impacts[0].id == "UI-001"


def test_dev_handoff_service_repairs_invalid_json_once() -> None:
    provider = FakeProvider(["not-json", json.dumps(VALID_DEV_HANDOFF_RESULT)])
    service = DevHandoffService(llm_provider=provider)

    response = service.run(_build_request())

    assert len(provider.calls) == 2
    assert "repair_invalid_dev_handoff_json" in str(provider.calls[1]["user_prompt"])
    assert response.handoff_readiness_score == 83
