from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ConfidenceType = Literal["high", "medium", "low"]


class MatchedContextItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    reason_matched: str
    source_file: str
    confidence: ConfidenceType


class ContextRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class RetrievedContextPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched_features: list[MatchedContextItem] = Field(default_factory=list)
    matched_ui_screens: list[MatchedContextItem] = Field(default_factory=list)
    matched_api_endpoints: list[MatchedContextItem] = Field(default_factory=list)
    matched_database_tables: list[MatchedContextItem] = Field(default_factory=list)
    matched_business_rules: list[MatchedContextItem] = Field(default_factory=list)
    matched_automation_tests: list[MatchedContextItem] = Field(default_factory=list)
    matched_known_defects: list[MatchedContextItem] = Field(default_factory=list)
    matched_test_history: list[MatchedContextItem] = Field(default_factory=list)
    risk_areas: list[str] = Field(default_factory=list)
    source_files_loaded: list[str] = Field(default_factory=list)
    retrieval_confidence: ConfidenceType
    open_context_questions: list[str] = Field(default_factory=list)
