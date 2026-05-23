from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.context_models import RetrievedContextPacket
from app.models.intake_models import FeatureIntakePacket, RunIntakeResponse
from app.models.requirements_models import RequirementsAgentResult


StoryType = Literal["story", "task", "spike", "bug"]
ConfidenceType = Literal["high", "medium", "low"]


class UserStory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_a: str
    i_want: str
    so_that: str


class GivenWhenThen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    criterion: str
    given_when_then: GivenWhenThen
    source_requirement_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceType


class JiraStoryAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    story_type: StoryType
    description: str
    user_story: UserStory
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    business_rules_referenced: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    story_readiness_score: int = Field(ge=0, le=100)
    safe_for_test_design: bool
    safe_for_automation_design: bool
    not_safe_to_generate: list[str] = Field(default_factory=list)


class JiraStoryAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    feature_intake_packet: FeatureIntakePacket
    intake_summary: RunIntakeResponse
    requirements_result: RequirementsAgentResult
    previous_workflow_outputs: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: RetrievedContextPacket | None = None


def build_jira_story_response_schema() -> dict[str, Any]:
    confidence_enum = ["high", "medium", "low"]

    acceptance_criterion_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "criterion": {"type": "string"},
            "given_when_then": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "given": {"type": "string"},
                    "when": {"type": "string"},
                    "then": {"type": "string"},
                },
                "required": ["given", "when", "then"],
            },
            "source_requirement_ids": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": confidence_enum},
        },
        "required": [
            "id",
            "criterion",
            "given_when_then",
            "source_requirement_ids",
            "confidence",
        ],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "story_type": {"type": "string", "enum": ["story", "task", "spike", "bug"]},
            "description": {"type": "string"},
            "user_story": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "as_a": {"type": "string"},
                    "i_want": {"type": "string"},
                    "so_that": {"type": "string"},
                },
                "required": ["as_a", "i_want", "so_that"],
            },
            "acceptance_criteria": {"type": "array", "items": acceptance_criterion_item},
            "business_rules_referenced": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "labels": {"type": "array", "items": {"type": "string"}},
            "components": {"type": "array", "items": {"type": "string"}},
            "definition_of_done": {"type": "array", "items": {"type": "string"}},
            "out_of_scope": {"type": "array", "items": {"type": "string"}},
            "story_readiness_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "safe_for_test_design": {"type": "boolean"},
            "safe_for_automation_design": {"type": "boolean"},
            "not_safe_to_generate": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "summary",
            "story_type",
            "description",
            "user_story",
            "acceptance_criteria",
            "business_rules_referenced",
            "dependencies",
            "assumptions",
            "open_questions",
            "labels",
            "components",
            "definition_of_done",
            "out_of_scope",
            "story_readiness_score",
            "safe_for_test_design",
            "safe_for_automation_design",
            "not_safe_to_generate",
        ],
    }
