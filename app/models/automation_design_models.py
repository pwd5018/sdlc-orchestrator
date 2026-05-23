from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.context_models import RetrievedContextPacket
from app.models.intake_models import FeatureIntakePacket, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentResult

__test__ = False


ConfidenceType = Literal["high", "medium", "low"]
RecommendedLayer = Literal["unit", "api", "ui", "integration", "contract", "performance", "security", "accessibility"]
CandidateLayer = Literal["api", "ui", "integration", "contract"]
CandidatePriority = Literal["critical", "high", "medium", "low"]


class RecommendedTestLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: RecommendedLayer
    recommendation: str
    reasoning: str
    confidence: ConfidenceType


class AutomationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    recommended_layer: CandidateLayer
    priority: CandidatePriority
    business_risk: str
    recommended_approach: str
    source_test_scenario_ids: list[str] = Field(default_factory=list)
    estimated_stability: ConfidenceType
    confidence: ConfidenceType


class ApiTestRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    recommendation: str
    reasoning: str
    contract_or_endpoint: str
    confidence: ConfidenceType


class UiTestRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    recommendation: str
    selector_or_hook_needs: list[str] = Field(default_factory=list)
    stability_risks: list[str] = Field(default_factory=list)
    confidence: ConfidenceType


class ContractTestRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    recommendation: str
    systems_involved: list[str] = Field(default_factory=list)
    risk_if_missing: str
    confidence: ConfidenceType


class TestDataRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    data_need: str
    purpose: str
    risk: str
    confidence: ConfidenceType


class FlakyRiskArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    risk_area: str
    why_risky: str
    mitigation_recommendation: str
    confidence: ConfidenceType


class AutomationDesignAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    automation_strategy_summary: str
    recommended_test_layers: list[RecommendedTestLayer] = Field(default_factory=list)
    automation_candidates: list[AutomationCandidate] = Field(default_factory=list)
    api_test_recommendations: list[ApiTestRecommendation] = Field(default_factory=list)
    ui_test_recommendations: list[UiTestRecommendation] = Field(default_factory=list)
    contract_test_recommendations: list[ContractTestRecommendation] = Field(default_factory=list)
    test_data_requirements: list[TestDataRequirement] = Field(default_factory=list)
    flaky_risk_areas: list[FlakyRiskArea] = Field(default_factory=list)
    recommended_test_hooks: list[str] = Field(default_factory=list)
    recommended_logging_or_observability: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    automation_design_readiness_score: int = Field(ge=0, le=100)
    safe_for_implementation_planning: bool
    not_safe_to_generate: list[str] = Field(default_factory=list)


class AutomationDesignAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    feature_intake_packet: FeatureIntakePacket
    intake_summary: RunIntakeResponse
    requirements_result: RequirementsAgentResult
    jira_story_result: JiraStoryAgentResult | None = None
    test_design_result: TestDesignAgentResult
    previous_workflow_outputs: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: RetrievedContextPacket | None = None


def build_automation_design_response_schema() -> dict[str, Any]:
    confidence_enum = ["high", "medium", "low"]

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "automation_strategy_summary": {"type": "string"},
            "recommended_test_layers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "layer": {
                            "type": "string",
                            "enum": ["unit", "api", "ui", "integration", "contract", "performance", "security", "accessibility"],
                        },
                        "recommendation": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["layer", "recommendation", "reasoning", "confidence"],
                },
            },
            "automation_candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "recommended_layer": {"type": "string", "enum": ["api", "ui", "integration", "contract"]},
                        "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "business_risk": {"type": "string"},
                        "recommended_approach": {"type": "string"},
                        "source_test_scenario_ids": {"type": "array", "items": {"type": "string"}},
                        "estimated_stability": {"type": "string", "enum": confidence_enum},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": [
                        "id",
                        "title",
                        "recommended_layer",
                        "priority",
                        "business_risk",
                        "recommended_approach",
                        "source_test_scenario_ids",
                        "estimated_stability",
                        "confidence",
                    ],
                },
            },
            "api_test_recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "contract_or_endpoint": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "recommendation", "reasoning", "contract_or_endpoint", "confidence"],
                },
            },
            "ui_test_recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "selector_or_hook_needs": {"type": "array", "items": {"type": "string"}},
                        "stability_risks": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "recommendation", "selector_or_hook_needs", "stability_risks", "confidence"],
                },
            },
            "contract_test_recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "systems_involved": {"type": "array", "items": {"type": "string"}},
                        "risk_if_missing": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "recommendation", "systems_involved", "risk_if_missing", "confidence"],
                },
            },
            "test_data_requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "data_need": {"type": "string"},
                        "purpose": {"type": "string"},
                        "risk": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "data_need", "purpose", "risk", "confidence"],
                },
            },
            "flaky_risk_areas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "risk_area": {"type": "string"},
                        "why_risky": {"type": "string"},
                        "mitigation_recommendation": {"type": "string"},
                        "confidence": {"type": "string", "enum": confidence_enum},
                    },
                    "required": ["id", "risk_area", "why_risky", "mitigation_recommendation", "confidence"],
                },
            },
            "recommended_test_hooks": {"type": "array", "items": {"type": "string"}},
            "recommended_logging_or_observability": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "automation_design_readiness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "safe_for_implementation_planning": {"type": "boolean"},
            "not_safe_to_generate": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "automation_strategy_summary",
            "recommended_test_layers",
            "automation_candidates",
            "api_test_recommendations",
            "ui_test_recommendations",
            "contract_test_recommendations",
            "test_data_requirements",
            "flaky_risk_areas",
            "recommended_test_hooks",
            "recommended_logging_or_observability",
            "assumptions",
            "open_questions",
            "automation_design_readiness_score",
            "safe_for_implementation_planning",
            "not_safe_to_generate",
        ],
    }
