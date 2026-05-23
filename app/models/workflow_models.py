from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


WorkflowMode = Literal["full", "story_only", "test_only", "automation_only", "qa_review_only"]
WorkflowStatus = Literal["completed", "blocked", "failed"]
WorkflowStepStatus = Literal["completed", "skipped", "blocked", "failed"]


class RunWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_description: str = Field(min_length=1, description="Raw feature request text to analyze.")
    mode: WorkflowMode
    context: dict[str, Any] = Field(default_factory=dict)
    attachments: list[Any] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class WorkflowStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_name: str
    status: WorkflowStepStatus = Field(
        description="Step outcome: completed for success, blocked for an expected gating condition, skipped when intentionally not run, or failed for a technical issue."
    )
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class RunWorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    mode: WorkflowMode
    status: WorkflowStatus = Field(
        description="Workflow outcome. completed means successful workflow execution, blocked means an expected clarification-needed state, and failed means a technical or system failure."
    )
    reason_code: str = Field(
        default="",
        description="Machine-readable reason for blocked responses. Empty for completed responses.",
    )
    user_safe_message: str = Field(
        default="",
        description="User-facing message safe to show directly in a Custom GPT when the workflow is blocked.",
    )
    readiness_score: int = Field(ge=0, le=100)
    can_continue: bool
    blocking_gaps: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    steps: list[WorkflowStepResult] = Field(default_factory=list)
    final_output: dict[str, Any] = Field(default_factory=dict)


def build_blocked_workflow_response(
    *,
    run_id: str,
    mode: WorkflowMode,
    reason_code: str,
    user_safe_message: str,
    readiness_score: int,
    blocking_gaps: list[str],
    clarification_questions: list[str],
    final_output: dict[str, Any] | None = None,
    steps: list[WorkflowStepResult] | None = None,
) -> RunWorkflowResponse:
    return RunWorkflowResponse(
        run_id=run_id,
        mode=mode,
        status="blocked",
        reason_code=reason_code,
        user_safe_message=user_safe_message,
        readiness_score=readiness_score,
        can_continue=False,
        blocking_gaps=blocking_gaps,
        clarification_questions=clarification_questions,
        steps=steps or [],
        final_output=final_output or {},
    )
