from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.context_models import RetrievedContextPacket
from app.models.intake_models import FeatureIntakePacket, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult

__test__ = False


ConfidenceType = Literal["high", "medium", "low"]
ScenarioType = Literal[
    "happy_path",
    "negative",
    "edge_case",
    "permission",
    "regression",
    "integration",
    "accessibility",
    "performance",
    "security",
]
ScenarioPriority = Literal["critical", "high", "medium", "low"]
RecommendedTestLevel = Literal[
    "unit",
    "api",
    "ui",
    "integration",
    "contract",
    "accessibility",
    "performance",
    "security",
    "regression",
]
SourceType = Literal["provided", "inferred"]


class CoverageStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_risks: list[str] = Field(default_factory=list)
    critical_business_rules: list[str] = Field(default_factory=list)
    recommended_test_levels: list[RecommendedTestLevel] = Field(default_factory=list)


class TestScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    type: ScenarioType
    priority: ScenarioPriority
    description: str
    preconditions: list[str] = Field(default_factory=list)
    test_data: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_results: list[str] = Field(default_factory=list)
    source_requirement_ids: list[str] = Field(default_factory=list)
    source_acceptance_criteria_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    automation_candidate: bool
    confidence: ConfidenceType


class RolePermissionTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    allowed_actions: list[str] = Field(default_factory=list)
    restricted_actions: list[str] = Field(default_factory=list)
    test_notes: list[str] = Field(default_factory=list)
    source: SourceType
    confidence: ConfidenceType


class DataVariationTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    data_condition: str
    expected_behavior: str
    risk: str
    confidence: ConfidenceType


class TestDesignAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_design_summary: str
    coverage_strategy: CoverageStrategy
    test_scenarios: list[TestScenario] = Field(default_factory=list)
    role_permission_tests: list[RolePermissionTest] = Field(default_factory=list)
    data_variation_tests: list[DataVariationTest] = Field(default_factory=list)
    negative_tests: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    regression_impact_areas: list[str] = Field(default_factory=list)
    untestable_or_unclear_items: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    test_design_readiness_score: int = Field(ge=0, le=100)
    safe_for_automation_design: bool
    not_safe_to_generate: list[str] = Field(default_factory=list)


class TestDesignAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    feature_intake_packet: FeatureIntakePacket
    intake_summary: RunIntakeResponse
    requirements_result: RequirementsAgentResult
    jira_story_result: JiraStoryAgentResult | None = None
    previous_workflow_outputs: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: RetrievedContextPacket | None = None


def build_test_design_response_schema() -> dict[str, Any]:
    confidence_enum = ["high", "medium", "low"]

    scenario_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "type": {
                "type": "string",
                "enum": [
                    "happy_path",
                    "negative",
                    "edge_case",
                    "permission",
                    "regression",
                    "integration",
                    "accessibility",
                    "performance",
                    "security",
                ],
            },
            "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
            "description": {"type": "string"},
            "preconditions": {"type": "array", "items": {"type": "string"}},
            "test_data": {"type": "array", "items": {"type": "string"}},
            "steps": {"type": "array", "items": {"type": "string"}},
            "expected_results": {"type": "array", "items": {"type": "string"}},
            "source_requirement_ids": {"type": "array", "items": {"type": "string"}},
            "source_acceptance_criteria_ids": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "automation_candidate": {"type": "boolean"},
            "confidence": {"type": "string", "enum": confidence_enum},
        },
        "required": [
            "id",
            "title",
            "type",
            "priority",
            "description",
            "preconditions",
            "test_data",
            "steps",
            "expected_results",
            "source_requirement_ids",
            "source_acceptance_criteria_ids",
            "assumptions",
            "open_questions",
            "automation_candidate",
            "confidence",
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
            "test_notes": {"type": "array", "items": {"type": "string"}},
            "source": {"type": "string", "enum": ["provided", "inferred"]},
            "confidence": {"type": "string", "enum": confidence_enum},
        },
        "required": [
            "id",
            "role",
            "allowed_actions",
            "restricted_actions",
            "test_notes",
            "source",
            "confidence",
        ],
    }

    data_variation_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "data_condition": {"type": "string"},
            "expected_behavior": {"type": "string"},
            "risk": {"type": "string"},
            "confidence": {"type": "string", "enum": confidence_enum},
        },
        "required": ["id", "data_condition", "expected_behavior", "risk", "confidence"],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "test_design_summary": {"type": "string"},
            "coverage_strategy": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "primary_risks": {"type": "array", "items": {"type": "string"}},
                    "critical_business_rules": {"type": "array", "items": {"type": "string"}},
                    "recommended_test_levels": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "unit",
                                "api",
                                "ui",
                                "integration",
                                "contract",
                                "accessibility",
                                "performance",
                                "security",
                                "regression",
                            ],
                        },
                    },
                },
                "required": ["primary_risks", "critical_business_rules", "recommended_test_levels"],
            },
            "test_scenarios": {"type": "array", "items": scenario_item},
            "role_permission_tests": {"type": "array", "items": role_permission_item},
            "data_variation_tests": {"type": "array", "items": data_variation_item},
            "negative_tests": {"type": "array", "items": {"type": "string"}},
            "edge_cases": {"type": "array", "items": {"type": "string"}},
            "regression_impact_areas": {"type": "array", "items": {"type": "string"}},
            "untestable_or_unclear_items": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "test_design_readiness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "safe_for_automation_design": {"type": "boolean"},
            "not_safe_to_generate": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "test_design_summary",
            "coverage_strategy",
            "test_scenarios",
            "role_permission_tests",
            "data_variation_tests",
            "negative_tests",
            "edge_cases",
            "regression_impact_areas",
            "untestable_or_unclear_items",
            "assumptions",
            "open_questions",
            "test_design_readiness_score",
            "safe_for_automation_design",
            "not_safe_to_generate",
        ],
    }
