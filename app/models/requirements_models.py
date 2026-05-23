from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.context_models import RetrievedContextPacket
from app.models.intake_models import FeatureIntakePacket, RunIntakeResponse


SourceType = Literal["provided", "inferred"]
ConfidenceType = Literal["high", "medium", "low"]
NfrCategory = Literal[
    "performance",
    "security",
    "usability",
    "accessibility",
    "reliability",
    "compatibility",
    "auditability",
    "maintainability",
    "other",
]
InputOutputType = Literal["input", "output", "both"]


class FunctionalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement: str
    source: SourceType
    confidence: ConfidenceType
    acceptance_hint: str
    related_business_rules: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class NonFunctionalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement: str
    category: NfrCategory
    source: SourceType
    confidence: ConfidenceType
    measurement_hint: str
    open_questions: list[str] = Field(default_factory=list)


class BusinessRuleRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    rule: str
    source: SourceType
    confidence: ConfidenceType
    impacted_requirements: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class DataRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    data_element: str
    description: str
    input_or_output: InputOutputType
    validation_rules: list[str] = Field(default_factory=list)
    source: SourceType
    confidence: ConfidenceType
    open_questions: list[str] = Field(default_factory=list)


class IntegrationRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    system: str
    interaction: str
    api_or_contract_impact: str
    source: SourceType
    confidence: ConfidenceType
    open_questions: list[str] = Field(default_factory=list)


class RolePermissionRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    allowed_actions: list[str] = Field(default_factory=list)
    restricted_actions: list[str] = Field(default_factory=list)
    source: SourceType
    confidence: ConfidenceType
    open_questions: list[str] = Field(default_factory=list)


class RequirementsAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    business_rules: list[BusinessRuleRequirement] = Field(default_factory=list)
    data_requirements: list[DataRequirement] = Field(default_factory=list)
    integration_requirements: list[IntegrationRequirement] = Field(default_factory=list)
    role_permission_requirements: list[RolePermissionRequirement] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    requirements_readiness_score: int = Field(ge=0, le=100)
    safe_for_jira_story_generation: bool
    safe_for_test_design: bool
    not_safe_to_generate: list[str] = Field(default_factory=list)


class RequirementsAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    feature_intake_packet: FeatureIntakePacket
    intake_summary: RunIntakeResponse
    previous_workflow_outputs: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: RetrievedContextPacket | None = None


def build_requirements_response_schema() -> dict[str, Any]:
    source_enum = ["provided", "inferred"]
    confidence_enum = ["high", "medium", "low"]

    functional_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "requirement": {"type": "string"},
            "source": {"type": "string", "enum": source_enum},
            "confidence": {"type": "string", "enum": confidence_enum},
            "acceptance_hint": {"type": "string"},
            "related_business_rules": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "id",
            "requirement",
            "source",
            "confidence",
            "acceptance_hint",
            "related_business_rules",
            "open_questions",
        ],
    }

    non_functional_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "requirement": {"type": "string"},
            "category": {
                "type": "string",
                "enum": [
                    "performance",
                    "security",
                    "usability",
                    "accessibility",
                    "reliability",
                    "compatibility",
                    "auditability",
                    "maintainability",
                    "other",
                ],
            },
            "source": {"type": "string", "enum": source_enum},
            "confidence": {"type": "string", "enum": confidence_enum},
            "measurement_hint": {"type": "string"},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "id",
            "requirement",
            "category",
            "source",
            "confidence",
            "measurement_hint",
            "open_questions",
        ],
    }

    business_rule_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "rule": {"type": "string"},
            "source": {"type": "string", "enum": source_enum},
            "confidence": {"type": "string", "enum": confidence_enum},
            "impacted_requirements": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "rule", "source", "confidence", "impacted_requirements", "open_questions"],
    }

    data_requirement_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "data_element": {"type": "string"},
            "description": {"type": "string"},
            "input_or_output": {"type": "string", "enum": ["input", "output", "both"]},
            "validation_rules": {"type": "array", "items": {"type": "string"}},
            "source": {"type": "string", "enum": source_enum},
            "confidence": {"type": "string", "enum": confidence_enum},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "id",
            "data_element",
            "description",
            "input_or_output",
            "validation_rules",
            "source",
            "confidence",
            "open_questions",
        ],
    }

    integration_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "system": {"type": "string"},
            "interaction": {"type": "string"},
            "api_or_contract_impact": {"type": "string"},
            "source": {"type": "string", "enum": source_enum},
            "confidence": {"type": "string", "enum": confidence_enum},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "id",
            "system",
            "interaction",
            "api_or_contract_impact",
            "source",
            "confidence",
            "open_questions",
        ],
    }

    role_permission_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "role": {"type": "string"},
            "allowed_actions": {"type": "array", "items": {"type": "string"}},
            "restricted_actions": {"type": "array", "items": {"type": "string"}},
            "source": {"type": "string", "enum": source_enum},
            "confidence": {"type": "string", "enum": confidence_enum},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "id",
            "role",
            "allowed_actions",
            "restricted_actions",
            "source",
            "confidence",
            "open_questions",
        ],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "functional_requirements": {"type": "array", "items": functional_item},
            "non_functional_requirements": {"type": "array", "items": non_functional_item},
            "business_rules": {"type": "array", "items": business_rule_item},
            "data_requirements": {"type": "array", "items": data_requirement_item},
            "integration_requirements": {"type": "array", "items": integration_item},
            "role_permission_requirements": {"type": "array", "items": role_permission_item},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "requirements_readiness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "safe_for_jira_story_generation": {"type": "boolean"},
            "safe_for_test_design": {"type": "boolean"},
            "not_safe_to_generate": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "functional_requirements",
            "non_functional_requirements",
            "business_rules",
            "data_requirements",
            "integration_requirements",
            "role_permission_requirements",
            "assumptions",
            "open_questions",
            "risks",
            "requirements_readiness_score",
            "safe_for_jira_story_generation",
            "safe_for_test_design",
            "not_safe_to_generate",
        ],
    }
