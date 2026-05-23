from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.automation_design_models import AutomationDesignAgentResult
from app.models.context_models import RetrievedContextPacket
from app.models.intake_models import FeatureIntakePacket, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentResult


ConfidenceType = Literal["high", "medium", "low"]
MigrationNeededType = Literal["yes", "no", "unknown"]
DeveloperTaskArea = Literal["ui", "api", "data", "integration", "config", "logging", "testing", "other"]


class ImplementationScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class UiImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    area: str
    change: str
    user_roles_impacted: list[str] = Field(default_factory=list)
    validation_or_state_notes: list[str] = Field(default_factory=list)
    confidence: ConfidenceType


class ApiImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    endpoint_or_contract: str
    change: str
    request_response_notes: list[str] = Field(default_factory=list)
    error_handling_notes: list[str] = Field(default_factory=list)
    confidence: ConfidenceType


class DataModelImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    entity_or_table: str
    change: str
    fields_or_attributes: list[str] = Field(default_factory=list)
    migration_needed: MigrationNeededType
    confidence: ConfidenceType


class IntegrationImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    system: str
    interaction: str
    risk: str
    confidence: ConfidenceType


class ConfigurationImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    setting: str
    purpose: str
    default_value: str
    admin_configurable: bool
    confidence: ConfidenceType


class AuditLoggingRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event: str
    fields_to_capture: list[str] = Field(default_factory=list)
    reason: str
    confidence: ConfidenceType


class ErrorHandlingRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    condition: str
    expected_behavior: str
    user_message_needed: bool
    confidence: ConfidenceType


class DeveloperTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    area: DeveloperTaskArea
    depends_on: list[str] = Field(default_factory=list)
    confidence: ConfidenceType


class DevHandoffAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    developer_summary: str
    implementation_scope: ImplementationScope
    ui_impacts: list[UiImpact] = Field(default_factory=list)
    api_impacts: list[ApiImpact] = Field(default_factory=list)
    data_model_impacts: list[DataModelImpact] = Field(default_factory=list)
    integration_impacts: list[IntegrationImpact] = Field(default_factory=list)
    configuration_impacts: list[ConfigurationImpact] = Field(default_factory=list)
    audit_logging_requirements: list[AuditLoggingRequirement] = Field(default_factory=list)
    error_handling_requirements: list[ErrorHandlingRequirement] = Field(default_factory=list)
    developer_tasks: list[DeveloperTask] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)
    implementation_risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    handoff_readiness_score: int = Field(ge=0, le=100)
    safe_for_dev_planning: bool
    not_safe_to_generate: list[str] = Field(default_factory=list)


class DevHandoffAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    feature_intake_packet: FeatureIntakePacket
    intake_summary: RunIntakeResponse
    requirements_result: RequirementsAgentResult
    jira_story_result: JiraStoryAgentResult | None = None
    test_design_result: TestDesignAgentResult | None = None
    automation_design_result: AutomationDesignAgentResult | None = None
    previous_workflow_outputs: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: RetrievedContextPacket | None = None


def build_dev_handoff_response_schema() -> dict[str, Any]:
    confidence_enum = ["high", "medium", "low"]

    def array_of_strings() -> dict[str, Any]:
        return {"type": "array", "items": {"type": "string"}}

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "developer_summary": {"type": "string"},
            "implementation_scope": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "in_scope": array_of_strings(),
                    "out_of_scope": array_of_strings(),
                    "assumptions": array_of_strings(),
                },
                "required": ["in_scope", "out_of_scope", "assumptions"],
            },
            "ui_impacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "area": {"type": "string"},
                        "change": {"type": "string"},
                        "user_roles_impacted": array_of_strings(),
                        "validation_or_state_notes": array_of_strings(),
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": [
                        "id",
                        "area",
                        "change",
                        "user_roles_impacted",
                        "validation_or_state_notes",
                        "confidence",
                    ],
                },
            },
            "api_impacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "endpoint_or_contract": {"type": "string"},
                        "change": {"type": "string"},
                        "request_response_notes": array_of_strings(),
                        "error_handling_notes": array_of_strings(),
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": [
                        "id",
                        "endpoint_or_contract",
                        "change",
                        "request_response_notes",
                        "error_handling_notes",
                        "confidence",
                    ],
                },
            },
            "data_model_impacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "entity_or_table": {"type": "string"},
                        "change": {"type": "string"},
                        "fields_or_attributes": array_of_strings(),
                        "migration_needed": {"type": "string", "enum": ["yes", "no", "unknown"]},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": [
                        "id",
                        "entity_or_table",
                        "change",
                        "fields_or_attributes",
                        "migration_needed",
                        "confidence",
                    ],
                },
            },
            "integration_impacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "system": {"type": "string"},
                        "interaction": {"type": "string"},
                        "risk": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "system", "interaction", "risk", "confidence"],
                },
            },
            "configuration_impacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "setting": {"type": "string"},
                        "purpose": {"type": "string"},
                        "default_value": {"type": "string"},
                        "admin_configurable": {"type": "boolean"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": [
                        "id",
                        "setting",
                        "purpose",
                        "default_value",
                        "admin_configurable",
                        "confidence",
                    ],
                },
            },
            "audit_logging_requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "event": {"type": "string"},
                        "fields_to_capture": array_of_strings(),
                        "reason": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "event", "fields_to_capture", "reason", "confidence"],
                },
            },
            "error_handling_requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "condition": {"type": "string"},
                        "expected_behavior": {"type": "string"},
                        "user_message_needed": {"type": "boolean"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": [
                        "id",
                        "condition",
                        "expected_behavior",
                        "user_message_needed",
                        "confidence",
                    ],
                },
            },
            "developer_tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "area": {
                            "type": "string",
                            "enum": ["ui", "api", "data", "integration", "config", "logging", "testing", "other"],
                        },
                        "depends_on": array_of_strings(),
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "title", "description", "area", "depends_on", "confidence"],
                },
            },
            "definition_of_done": array_of_strings(),
            "implementation_risks": array_of_strings(),
            "open_questions": array_of_strings(),
            "handoff_readiness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "safe_for_dev_planning": {"type": "boolean"},
            "not_safe_to_generate": array_of_strings(),
        },
        "required": [
            "developer_summary",
            "implementation_scope",
            "ui_impacts",
            "api_impacts",
            "data_model_impacts",
            "integration_impacts",
            "configuration_impacts",
            "audit_logging_requirements",
            "error_handling_requirements",
            "developer_tasks",
            "definition_of_done",
            "implementation_risks",
            "open_questions",
            "handoff_readiness_score",
            "safe_for_dev_planning",
            "not_safe_to_generate",
        ],
    }
