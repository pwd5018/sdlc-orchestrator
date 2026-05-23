from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.context_models import RetrievedContextPacket


class PacketField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    confidence: Literal["high", "medium", "low"]
    source: Literal["provided", "inferred", "missing"]
    needs_clarification: bool


class FeatureIntakePacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_name: PacketField
    problem_statement: PacketField
    business_goal: PacketField
    target_users: PacketField
    current_behavior: PacketField
    desired_behavior: PacketField
    in_scope: PacketField
    out_of_scope: PacketField
    business_rules: PacketField
    data_inputs: PacketField
    data_outputs: PacketField
    user_roles_permissions: PacketField
    systems_impacted: PacketField
    api_or_contract_impacts: PacketField
    ui_impacts: PacketField
    reporting_or_audit_needs: PacketField
    error_handling_expectations: PacketField
    edge_cases: PacketField
    non_functional_requirements: PacketField
    dependencies: PacketField
    known_risks: PacketField
    open_questions: PacketField
    assumptions: PacketField


class RunIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    attachments: list[Any] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    retrieved_context: RetrievedContextPacket | None = None


class RunIntakeAIResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_intake_packet: FeatureIntakePacket
    readiness_score: int = Field(ge=0, le=100)
    blocking_gaps: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


class RunIntakeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_intake_packet: FeatureIntakePacket
    readiness_score: int = Field(ge=0, le=100)
    can_continue: bool
    blocking_gaps: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    safe_to_generate: list[str] = Field(default_factory=list)
    not_safe_to_generate: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str


def build_openai_response_schema() -> dict[str, Any]:
    packet_field_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "source": {"type": "string", "enum": ["provided", "inferred", "missing"]},
            "needs_clarification": {"type": "boolean"},
        },
        "required": ["value", "confidence", "source", "needs_clarification"],
    }

    packet_properties = {
        "feature_name": packet_field_schema,
        "problem_statement": packet_field_schema,
        "business_goal": packet_field_schema,
        "target_users": packet_field_schema,
        "current_behavior": packet_field_schema,
        "desired_behavior": packet_field_schema,
        "in_scope": packet_field_schema,
        "out_of_scope": packet_field_schema,
        "business_rules": packet_field_schema,
        "data_inputs": packet_field_schema,
        "data_outputs": packet_field_schema,
        "user_roles_permissions": packet_field_schema,
        "systems_impacted": packet_field_schema,
        "api_or_contract_impacts": packet_field_schema,
        "ui_impacts": packet_field_schema,
        "reporting_or_audit_needs": packet_field_schema,
        "error_handling_expectations": packet_field_schema,
        "edge_cases": packet_field_schema,
        "non_functional_requirements": packet_field_schema,
        "dependencies": packet_field_schema,
        "known_risks": packet_field_schema,
        "open_questions": packet_field_schema,
        "assumptions": packet_field_schema,
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "feature_intake_packet": {
                "type": "object",
                "additionalProperties": False,
                "properties": packet_properties,
                "required": list(packet_properties.keys()),
            },
            "readiness_score": {"type": "integer"},
            "blocking_gaps": {
                "type": "array",
                "items": {"type": "string"},
            },
            "clarification_questions": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "feature_intake_packet",
            "readiness_score",
            "blocking_gaps",
            "clarification_questions",
        ],
    }
