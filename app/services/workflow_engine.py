import logging
from uuid import uuid4

from app.constants.workflow_modes import WORKFLOW_MODES
from app.models.automation_design_models import AutomationDesignAgentRequest, AutomationDesignAgentResult
from app.models.context_models import ContextRetrievalRequest, RetrievedContextPacket
from app.models.dev_handoff_models import DevHandoffAgentRequest, DevHandoffAgentResult
from app.models.intake_models import RunIntakeRequest, RunIntakeResponse
from app.models.jira_story_models import JiraStoryAgentRequest, JiraStoryAgentResult
from app.models.requirements_models import RequirementsAgentRequest, RequirementsAgentResult
from app.models.test_design_models import TestDesignAgentRequest, TestDesignAgentResult
from app.models.workflow_models import (
    RunWorkflowRequest,
    RunWorkflowResponse,
    WorkflowStepResult,
    build_blocked_workflow_response,
)
from app.services.automation_design_service import AutomationDesignProcessingError, AutomationDesignService
from app.services.context_retrieval_service import ContextRetrievalService
from app.services.dev_handoff_service import DevHandoffProcessingError, DevHandoffService
from app.services.intake_service import IntakeService
from app.services.jira_story_service import JiraStoryProcessingError, JiraStoryService
from app.services.requirements_service import RequirementsProcessingError, RequirementsService
from app.services.test_design_service import TestDesignProcessingError, TestDesignService


logger = logging.getLogger(__name__)


class WorkflowExecutionError(RuntimeError):
    """Raised when the workflow shell cannot complete execution."""


class WorkflowEngine:
    def __init__(
        self,
        intake_service: IntakeService | None = None,
        requirements_service: RequirementsService | None = None,
        jira_story_service: JiraStoryService | None = None,
        test_design_service: TestDesignService | None = None,
        automation_design_service: AutomationDesignService | None = None,
        dev_handoff_service: DevHandoffService | None = None,
        context_retrieval_service: ContextRetrievalService | None = None,
    ) -> None:
        self.intake_service = intake_service or IntakeService()
        self.requirements_service = requirements_service or RequirementsService()
        self.jira_story_service = jira_story_service or JiraStoryService()
        self.test_design_service = test_design_service or TestDesignService()
        self.automation_design_service = automation_design_service or AutomationDesignService()
        self.dev_handoff_service = dev_handoff_service or DevHandoffService()
        self.context_retrieval_service = context_retrieval_service or ContextRetrievalService()

    def run(self, request: RunWorkflowRequest) -> RunWorkflowResponse:
        run_id = uuid4().hex
        logger.info("workflow started run_id=%s mode=%s", run_id, request.mode)
        logger.info("selected mode run_id=%s mode=%s", run_id, request.mode)

        steps: list[WorkflowStepResult] = []
        workflow_warnings: list[str] = []
        retrieved_context: RetrievedContextPacket | None = None
        context_step_output: dict[str, object] | None = None
        context_retrieval_status = "not_configured"

        if self.context_retrieval_service.is_configured():
            logger.info("workflow context retrieval started run_id=%s mode=%s", run_id, request.mode)
            try:
                retrieved_context = self.context_retrieval_service.run(
                    ContextRetrievalRequest(
                        feature_description=request.feature_description,
                        mode=request.mode,
                        context=request.context,
                    )
                )
                context_step_output = retrieved_context.model_dump(mode="json")
                context_status = "completed" if retrieved_context.source_files_loaded else "skipped"
                context_retrieval_status = context_status
                if context_status == "skipped" and retrieved_context.open_context_questions:
                    workflow_warnings.extend(retrieved_context.open_context_questions)
                steps.append(
                    WorkflowStepResult(
                        step_name="context_retrieval",
                        status=context_status,
                        input={
                            "feature_description": request.feature_description,
                            "mode": request.mode,
                            "context": request.context,
                        },
                        output=context_step_output,
                    )
                )
                logger.info("workflow context retrieval completed run_id=%s status=%s", run_id, context_status)
            except Exception as exc:  # pragma: no cover - defensive non-blocking path
                warning = f"Context retrieval failed non-blocking: {exc}"
                workflow_warnings.append(warning)
                context_retrieval_status = "failed_non_blocking"
                steps.append(
                    WorkflowStepResult(
                        step_name="context_retrieval",
                        status="skipped",
                        input={
                            "feature_description": request.feature_description,
                            "mode": request.mode,
                            "context": request.context,
                        },
                        output={
                            "message": "Context retrieval failed non-blocking.",
                            "warning": warning,
                        },
                    )
                )
                logger.exception("workflow context retrieval failed non-blocking run_id=%s", run_id)

        try:
            intake_result = self.intake_service.run(
                RunIntakeRequest(
                    feature_description=request.feature_description,
                    context=request.context,
                    attachments=request.attachments,
                    notes=request.notes,
                    retrieved_context=retrieved_context,
                )
            )
        except Exception as exc:
            logger.exception("workflow failed during intake run_id=%s mode=%s", run_id, request.mode)
            raise WorkflowExecutionError("Failed to run the intake step for the SDLC workflow.") from exc

        logger.info(
            "intake readiness score run_id=%s score=%s",
            run_id,
            intake_result.readiness_score,
        )
        intake_previous_outputs: dict[str, dict] = {}
        if context_step_output and steps and steps[0].step_name == "context_retrieval" and steps[0].status == "completed":
            intake_previous_outputs["context_retrieval"] = context_step_output

        steps.append(
            WorkflowStepResult(
                step_name="intake",
                status="completed",
                input=self._build_step_input(
                    run_id=run_id,
                    mode=request.mode,
                    feature_description=request.feature_description,
                    previous_outputs=intake_previous_outputs,
                    retrieved_context=retrieved_context,
                    include_feature_description=True,
                ),
                output=intake_result.model_dump(mode="json"),
            )
        )

        previous_outputs: dict[str, dict] = {}
        if context_step_output and steps[0].step_name == "context_retrieval" and steps[0].status == "completed":
            previous_outputs["context_retrieval"] = context_step_output
        previous_outputs["intake"] = intake_result.model_dump(mode="json")

        if intake_result.readiness_score < 70:
            logger.info("workflow blocked run_id=%s score=%s", run_id, intake_result.readiness_score)
            response = build_blocked_workflow_response(
                run_id=run_id,
                mode=request.mode,
                reason_code="insufficient_feature_detail",
                user_safe_message="I need a little more detail before I can generate the SDLC workflow package.",
                readiness_score=intake_result.readiness_score,
                blocking_gaps=intake_result.blocking_gaps,
                clarification_questions=intake_result.clarification_questions,
                final_output={
                    "message": "Workflow blocked pending intake clarification.",
                    "intake_summary_available": True,
                    "context_retrieval_summary": self._build_context_retrieval_summary(
                        status=context_retrieval_status,
                        retrieved_context=retrieved_context,
                    ),
                    "warnings": workflow_warnings,
                },
                steps=steps if any(step.step_name == "context_retrieval" for step in steps) else None,
            )
            logger.info("workflow completed run_id=%s status=%s", run_id, response.status)
            return response

        selected_steps = WORKFLOW_MODES[request.mode]
        requirements_result: RequirementsAgentResult | None = None
        jira_story_result: JiraStoryAgentResult | None = None
        test_design_result: TestDesignAgentResult | None = None
        automation_design_result: AutomationDesignAgentResult | None = None
        dev_handoff_result: DevHandoffAgentResult | None = None

        for step_name in selected_steps[1:]:
            logger.info("workflow step started run_id=%s step=%s", run_id, step_name)

            if step_name == "requirements":
                try:
                    requirements_result = self.requirements_service.run(
                        RequirementsAgentRequest(
                            feature_description=request.feature_description,
                            feature_intake_packet=intake_result.feature_intake_packet,
                            intake_summary=intake_result,
                            previous_workflow_outputs=previous_outputs,
                            retrieved_context=retrieved_context,
                        )
                    )
                except RequirementsProcessingError as exc:
                    logger.exception("workflow failed during requirements run_id=%s", run_id)
                    raise WorkflowExecutionError("Failed to run the requirements step for the SDLC workflow.") from exc

                step_output = requirements_result.model_dump(mode="json")
                step_result = WorkflowStepResult(
                    step_name=step_name,
                    status="completed",
                    input=self._build_step_input(
                        run_id=run_id,
                        mode=request.mode,
                        previous_outputs=previous_outputs,
                        retrieved_context=retrieved_context,
                    ),
                    output=step_output,
                )
                steps.append(step_result)
                previous_outputs[step_name] = step_output
                logger.info("workflow step completed run_id=%s step=%s", run_id, step_name)

                if requirements_result.requirements_readiness_score < 70:
                    logger.info(
                        "workflow blocked by requirements readiness run_id=%s requirements_readiness_score=%s",
                        run_id,
                        requirements_result.requirements_readiness_score,
                    )
                    remaining_steps = selected_steps[selected_steps.index(step_name) + 1 :]
                    for remaining_step in remaining_steps:
                        blocked_status = (
                            "blocked"
                            if remaining_step in {"jira_story", "test_design", "automation_design", "dev_handoff"}
                            else "skipped"
                        )
                        blocked_output = {
                            "message": "Skipped or blocked because requirements readiness is below the continuation threshold.",
                            "requirements_readiness_score": requirements_result.requirements_readiness_score,
                            "not_safe_to_generate": requirements_result.not_safe_to_generate,
                            "received_previous_outputs": True,
                        }
                        steps.append(
                            WorkflowStepResult(
                                step_name=remaining_step,
                                status=blocked_status,
                                input=self._build_step_input(
                                    run_id=run_id,
                                    mode=request.mode,
                                    previous_outputs=previous_outputs,
                                    retrieved_context=retrieved_context,
                                ),
                                output=blocked_output,
                            )
                        )

                    response = build_blocked_workflow_response(
                        run_id=run_id,
                        mode=request.mode,
                        reason_code="insufficient_requirements_detail",
                        user_safe_message="I need a little more detail before I can generate the downstream SDLC planning outputs.",
                        readiness_score=intake_result.readiness_score,
                        blocking_gaps=intake_result.blocking_gaps,
                        clarification_questions=self._merge_questions(
                            intake_result.clarification_questions,
                            requirements_result.open_questions,
                        ),
                        steps=steps,
                        final_output={
                            "message": "Workflow blocked because requirements are not ready for downstream generation.",
                            "requirements": step_output,
                            "requirements_readiness_score": requirements_result.requirements_readiness_score,
                            "open_questions": requirements_result.open_questions,
                            "not_safe_to_generate": requirements_result.not_safe_to_generate,
                            "warnings": workflow_warnings,
                        },
                    )
                    logger.info("workflow completed run_id=%s status=%s", run_id, response.status)
                    return response

                continue

            if step_name == "jira_story":
                if requirements_result is None:
                    raise WorkflowExecutionError("Requirements output is required before Jira story generation.")

                try:
                    jira_story_result = self.jira_story_service.run(
                        JiraStoryAgentRequest(
                            feature_description=request.feature_description,
                            feature_intake_packet=intake_result.feature_intake_packet,
                            intake_summary=intake_result,
                            requirements_result=requirements_result,
                            previous_workflow_outputs=previous_outputs,
                            retrieved_context=retrieved_context,
                        )
                    )
                except JiraStoryProcessingError as exc:
                    logger.exception("workflow failed during jira story run_id=%s", run_id)
                    raise WorkflowExecutionError("Failed to run the Jira story step for the SDLC workflow.") from exc

                step_output = jira_story_result.model_dump(mode="json")
                step_result = WorkflowStepResult(
                    step_name=step_name,
                    status="completed",
                    input=self._build_step_input(
                        run_id=run_id,
                        mode=request.mode,
                        previous_outputs=previous_outputs,
                        retrieved_context=retrieved_context,
                    ),
                    output=step_output,
                )
                steps.append(step_result)
                previous_outputs[step_name] = step_output
                logger.info("workflow step completed run_id=%s step=%s", run_id, step_name)

                if jira_story_result.story_readiness_score < 70 and request.mode == "full":
                    logger.info(
                        "workflow blocked by story readiness run_id=%s story_readiness_score=%s",
                        run_id,
                        jira_story_result.story_readiness_score,
                    )
                    remaining_steps = selected_steps[selected_steps.index(step_name) + 1 :]
                    for remaining_step in remaining_steps:
                        blocked_status = (
                            "blocked"
                            if remaining_step in {"test_design", "automation_design", "dev_handoff"}
                            else "skipped"
                        )
                        blocked_output = {
                            "message": "Skipped or blocked because story readiness is below the continuation threshold.",
                            "story_readiness_score": jira_story_result.story_readiness_score,
                            "not_safe_to_generate": jira_story_result.not_safe_to_generate,
                            "received_previous_outputs": True,
                        }
                        steps.append(
                            WorkflowStepResult(
                                step_name=remaining_step,
                                status=blocked_status,
                                input=self._build_step_input(
                                    run_id=run_id,
                                    mode=request.mode,
                                    previous_outputs=previous_outputs,
                                    retrieved_context=retrieved_context,
                                ),
                                output=blocked_output,
                            )
                        )

                    response = build_blocked_workflow_response(
                        run_id=run_id,
                        mode=request.mode,
                        reason_code="insufficient_story_detail",
                        user_safe_message="I can draft the Jira story, but I need a little more detail before downstream test or automation planning should continue.",
                        readiness_score=intake_result.readiness_score,
                        blocking_gaps=intake_result.blocking_gaps,
                        clarification_questions=self._merge_questions(
                            intake_result.clarification_questions,
                            jira_story_result.open_questions,
                        ),
                        steps=steps,
                        final_output={
                            "message": "Workflow blocked because the Jira story is not ready for downstream planning.",
                            "requirements": requirements_result.model_dump(mode="json"),
                            "jira_story": step_output,
                            "story_readiness_score": jira_story_result.story_readiness_score,
                            "open_questions": jira_story_result.open_questions,
                            "not_safe_to_generate": jira_story_result.not_safe_to_generate,
                            "warnings": workflow_warnings,
                        },
                    )
                    logger.info("workflow completed run_id=%s status=%s", run_id, response.status)
                    return response

                continue

            if step_name == "test_design":
                if requirements_result is None:
                    raise WorkflowExecutionError("Requirements output is required before test design generation.")

                if jira_story_result is not None and jira_story_result.story_readiness_score < 70:
                    logger.info(
                        "workflow blocked by story readiness before test design run_id=%s story_readiness_score=%s",
                        run_id,
                        jira_story_result.story_readiness_score,
                    )
                    remaining_steps = selected_steps[selected_steps.index(step_name) :]
                    for remaining_step in remaining_steps:
                        blocked_status = "blocked" if remaining_step in {"test_design", "automation_design"} else "skipped"
                        blocked_output = {
                            "message": "Skipped or blocked because story readiness is below the continuation threshold.",
                            "story_readiness_score": jira_story_result.story_readiness_score,
                            "not_safe_to_generate": jira_story_result.not_safe_to_generate,
                            "received_previous_outputs": True,
                        }
                        steps.append(
                            WorkflowStepResult(
                                step_name=remaining_step,
                                status=blocked_status,
                                input=self._build_step_input(
                                    run_id=run_id,
                                    mode=request.mode,
                                    previous_outputs=previous_outputs,
                                    retrieved_context=retrieved_context,
                                ),
                                output=blocked_output,
                            )
                        )

                    response = build_blocked_workflow_response(
                        run_id=run_id,
                        mode=request.mode,
                        reason_code="insufficient_story_detail",
                        user_safe_message="I need a little more story detail before I can generate reliable downstream test planning.",
                        readiness_score=intake_result.readiness_score,
                        blocking_gaps=intake_result.blocking_gaps,
                        clarification_questions=self._merge_questions(
                            intake_result.clarification_questions,
                            jira_story_result.open_questions,
                        ),
                        steps=steps,
                        final_output={
                            "message": "Workflow blocked because the Jira story is not ready for test design.",
                            "requirements": requirements_result.model_dump(mode="json"),
                            "jira_story": jira_story_result.model_dump(mode="json"),
                            "story_readiness_score": jira_story_result.story_readiness_score,
                            "open_questions": jira_story_result.open_questions,
                            "not_safe_to_generate": jira_story_result.not_safe_to_generate,
                            "warnings": workflow_warnings,
                        },
                    )
                    logger.info("workflow completed run_id=%s status=%s", run_id, response.status)
                    return response

                try:
                    test_design_result = self.test_design_service.run(
                        TestDesignAgentRequest(
                            feature_description=request.feature_description,
                            feature_intake_packet=intake_result.feature_intake_packet,
                            intake_summary=intake_result,
                            requirements_result=requirements_result,
                            jira_story_result=jira_story_result,
                            previous_workflow_outputs=previous_outputs,
                            retrieved_context=retrieved_context,
                        )
                    )
                except TestDesignProcessingError as exc:
                    logger.exception("workflow failed during test design run_id=%s", run_id)
                    raise WorkflowExecutionError("Failed to run the test design step for the SDLC workflow.") from exc

                step_output = test_design_result.model_dump(mode="json")
                step_result = WorkflowStepResult(
                    step_name=step_name,
                    status="completed",
                    input=self._build_step_input(
                        run_id=run_id,
                        mode=request.mode,
                        previous_outputs=previous_outputs,
                        retrieved_context=retrieved_context,
                    ),
                    output=step_output,
                )
                steps.append(step_result)
                previous_outputs[step_name] = step_output
                logger.info("workflow step completed run_id=%s step=%s", run_id, step_name)

                if (
                    test_design_result.test_design_readiness_score < 70
                    and "automation_design" in selected_steps[selected_steps.index(step_name) + 1 :]
                ):
                    logger.info(
                        "workflow blocked by test design readiness run_id=%s test_design_readiness_score=%s",
                        run_id,
                        test_design_result.test_design_readiness_score,
                    )
                    remaining_steps = selected_steps[selected_steps.index(step_name) + 1 :]
                    for remaining_step in remaining_steps:
                        blocked_status = "blocked" if remaining_step == "automation_design" else "skipped"
                        blocked_output = {
                            "message": "Skipped or blocked because test design readiness is below the continuation threshold.",
                            "test_design_readiness_score": test_design_result.test_design_readiness_score,
                            "not_safe_to_generate": test_design_result.not_safe_to_generate,
                            "received_previous_outputs": True,
                        }
                        steps.append(
                            WorkflowStepResult(
                                step_name=remaining_step,
                                status=blocked_status,
                                input=self._build_step_input(
                                    run_id=run_id,
                                    mode=request.mode,
                                    previous_outputs=previous_outputs,
                                    retrieved_context=retrieved_context,
                                ),
                                output=blocked_output,
                            )
                        )

                    response = build_blocked_workflow_response(
                        run_id=run_id,
                        mode=request.mode,
                        reason_code="insufficient_test_design_detail",
                        user_safe_message="I can draft the test design, but I need a little more detail before automation planning should continue.",
                        readiness_score=intake_result.readiness_score,
                        blocking_gaps=intake_result.blocking_gaps,
                        clarification_questions=self._merge_questions(
                            intake_result.clarification_questions,
                            test_design_result.open_questions,
                        ),
                        steps=steps,
                        final_output={
                            "message": "Workflow blocked because the test design is not ready for automation planning.",
                            "requirements": requirements_result.model_dump(mode="json"),
                            "jira_story": jira_story_result.model_dump(mode="json") if jira_story_result else None,
                            "test_design": step_output,
                            "test_design_readiness_score": test_design_result.test_design_readiness_score,
                            "missing_information": test_design_result.untestable_or_unclear_items,
                            "open_questions": test_design_result.open_questions,
                            "not_safe_to_generate": test_design_result.not_safe_to_generate,
                            "warnings": workflow_warnings,
                        },
                    )
                    logger.info("workflow completed run_id=%s status=%s", run_id, response.status)
                    return response

                continue

            if step_name == "automation_design":
                if requirements_result is None:
                    raise WorkflowExecutionError("Requirements output is required before automation design generation.")

                if test_design_result is None:
                    raise WorkflowExecutionError("Test design output is required before automation design generation.")

                try:
                    automation_design_result = self.automation_design_service.run(
                        AutomationDesignAgentRequest(
                            feature_description=request.feature_description,
                            feature_intake_packet=intake_result.feature_intake_packet,
                            intake_summary=intake_result,
                            requirements_result=requirements_result,
                            jira_story_result=jira_story_result,
                            test_design_result=test_design_result,
                            previous_workflow_outputs=previous_outputs,
                            retrieved_context=retrieved_context,
                        )
                    )
                except AutomationDesignProcessingError as exc:
                    logger.exception("workflow failed during automation design run_id=%s", run_id)
                    raise WorkflowExecutionError(
                        "Failed to run the automation design step for the SDLC workflow."
                    ) from exc

                step_output = automation_design_result.model_dump(mode="json")
                step_result = WorkflowStepResult(
                    step_name=step_name,
                    status="completed",
                    input=self._build_step_input(
                        run_id=run_id,
                        mode=request.mode,
                        previous_outputs=previous_outputs,
                        retrieved_context=retrieved_context,
                    ),
                    output=step_output,
                )
                steps.append(step_result)
                previous_outputs[step_name] = step_output
                logger.info("workflow step completed run_id=%s step=%s", run_id, step_name)
                continue

            if step_name == "dev_handoff":
                if requirements_result is None:
                    raise WorkflowExecutionError("Requirements output is required before dev handoff generation.")

                try:
                    dev_handoff_result = self.dev_handoff_service.run(
                        DevHandoffAgentRequest(
                            feature_description=request.feature_description,
                            feature_intake_packet=intake_result.feature_intake_packet,
                            intake_summary=intake_result,
                            requirements_result=requirements_result,
                            jira_story_result=jira_story_result,
                            test_design_result=test_design_result,
                            automation_design_result=automation_design_result,
                            previous_workflow_outputs=previous_outputs,
                            retrieved_context=retrieved_context,
                        )
                    )
                except DevHandoffProcessingError as exc:
                    logger.exception("workflow failed during dev handoff run_id=%s", run_id)
                    raise WorkflowExecutionError("Failed to run the dev handoff step for the SDLC workflow.") from exc

                dev_handoff_result = self._apply_dev_handoff_guardrails(dev_handoff_result, automation_design_result)
                step_output = dev_handoff_result.model_dump(mode="json")
                step_result = WorkflowStepResult(
                    step_name=step_name,
                    status="completed",
                    input=self._build_step_input(
                        run_id=run_id,
                        mode=request.mode,
                        previous_outputs=previous_outputs,
                        retrieved_context=retrieved_context,
                    ),
                    output=step_output,
                )
                steps.append(step_result)
                previous_outputs[step_name] = step_output
                logger.info("workflow step completed run_id=%s step=%s", run_id, step_name)
                continue

            step_output = self._build_placeholder_output(previous_outputs)
            step_result = WorkflowStepResult(
                step_name=step_name,
                status="completed",
                input=self._build_step_input(
                    run_id=run_id,
                    mode=request.mode,
                    previous_outputs=previous_outputs,
                    retrieved_context=retrieved_context,
                ),
                output=step_output,
            )
            steps.append(step_result)
            previous_outputs[step_name] = step_output
            logger.info("workflow step completed run_id=%s step=%s", run_id, step_name)

        final_output = {
            "message": self._build_final_message(context_retrieval_status, retrieved_context),
            "mode": request.mode,
            "generated_steps": [step.step_name for step in steps],
            "requirements": requirements_result.model_dump(mode="json") if requirements_result else None,
            "jira_story": jira_story_result.model_dump(mode="json") if jira_story_result else None,
            "test_design": test_design_result.model_dump(mode="json") if test_design_result else None,
            "automation_design": automation_design_result.model_dump(mode="json") if automation_design_result else None,
            "dev_handoff": dev_handoff_result.model_dump(mode="json") if dev_handoff_result else None,
            "retrieved_context": retrieved_context.model_dump(mode="json") if retrieved_context else None,
            "context_retrieval_summary": self._build_context_retrieval_summary(
                status=context_retrieval_status,
                retrieved_context=retrieved_context,
            ),
            "warnings": workflow_warnings,
            "artifacts": {
                step.step_name: step.output
                for step in steps
                if step.step_name != "intake"
            },
        }

        response = RunWorkflowResponse(
            run_id=run_id,
            mode=request.mode,
            status="completed",
            reason_code="",
            user_safe_message="",
            readiness_score=intake_result.readiness_score,
            can_continue=intake_result.can_continue,
            blocking_gaps=intake_result.blocking_gaps,
            clarification_questions=intake_result.clarification_questions,
            steps=steps,
            final_output=final_output,
        )
        logger.info("workflow completed run_id=%s status=%s", run_id, response.status)
        return response

    def _build_placeholder_output(self, previous_outputs: dict[str, dict]) -> dict[str, object]:
        return {
            "message": "Placeholder only. Real agent will be implemented in a future milestone.",
            "received_previous_outputs": bool(previous_outputs),
        }

    def _build_context_retrieval_summary(
        self,
        *,
        status: str,
        retrieved_context: RetrievedContextPacket | None,
    ) -> dict[str, object]:
        packet = retrieved_context
        return {
            "status": status,
            "retrieval_confidence": packet.retrieval_confidence if packet else "low",
            "matched_feature_names": [item.name for item in packet.matched_features] if packet else [],
            "matched_ui_screen_names": [item.name for item in packet.matched_ui_screens] if packet else [],
            "matched_api_endpoint_names": [item.name for item in packet.matched_api_endpoints] if packet else [],
            "matched_database_table_names": [item.name for item in packet.matched_database_tables] if packet else [],
            "matched_known_defect_names": [item.name for item in packet.matched_known_defects] if packet else [],
            "source_files_loaded": packet.source_files_loaded if packet else [],
            "open_context_questions": packet.open_context_questions if packet else [],
            "matched_feature_count": len(packet.matched_features) if packet else 0,
            "matched_api_endpoint_count": len(packet.matched_api_endpoints) if packet else 0,
            "matched_ui_screen_count": len(packet.matched_ui_screens) if packet else 0,
            "matched_database_table_count": len(packet.matched_database_tables) if packet else 0,
            "matched_known_defect_count": len(packet.matched_known_defects) if packet else 0,
            "source_file_count": len(packet.source_files_loaded) if packet else 0,
            "total_match_count": self._count_context_matches(packet) if packet else 0,
        }

    def _build_final_message(
        self,
        context_retrieval_status: str,
        retrieved_context: RetrievedContextPacket | None,
    ) -> str:
        base_message = (
            "Workflow completed with the currently implemented SDLC agents plus placeholder downstream QA review and finalizer steps."
        )
        if context_retrieval_status == "completed" and retrieved_context is not None:
            return (
                f"{base_message} PolicySphere context retrieved from {len(retrieved_context.source_files_loaded)} files "
                f"with {self._count_context_matches(retrieved_context)} matched artifacts."
            )
        if context_retrieval_status in {"skipped", "failed_non_blocking"}:
            return f"{base_message} PolicySphere context retrieval did not produce reusable artifact matches."
        return base_message

    def _count_context_matches(self, packet: RetrievedContextPacket) -> int:
        return sum(
            len(match_set)
            for match_set in (
                packet.matched_features,
                packet.matched_ui_screens,
                packet.matched_api_endpoints,
                packet.matched_database_tables,
                packet.matched_business_rules,
                packet.matched_automation_tests,
                packet.matched_known_defects,
                packet.matched_test_history,
            )
        )

    def _build_step_input(
        self,
        *,
        run_id: str,
        mode: str,
        previous_outputs: dict[str, dict],
        retrieved_context: RetrievedContextPacket | None,
        feature_description: str | None = None,
        include_feature_description: bool = False,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_id": run_id,
            "mode": mode,
            "received_previous_step_names": list(previous_outputs.keys()),
        }
        if include_feature_description and feature_description is not None:
            payload["feature_description"] = feature_description
        if retrieved_context is not None:
            payload["retrieved_context"] = retrieved_context.model_dump(mode="json")
        return payload

    def _apply_dev_handoff_guardrails(
        self,
        result: DevHandoffAgentResult,
        automation_design_result: AutomationDesignAgentResult | None,
    ) -> DevHandoffAgentResult:
        if (
            automation_design_result is None
            or automation_design_result.automation_design_readiness_score >= 70
        ):
            return result

        automation_message = (
            "Automation design readiness is below 70, so implementation planning should treat"
            " testability and observability recommendations as provisional until clarified."
        )
        implementation_risks = list(result.implementation_risks)
        open_questions = list(result.open_questions)
        not_safe_to_generate = list(result.not_safe_to_generate)
        safe_for_dev_planning = result.safe_for_dev_planning

        if automation_message not in implementation_risks:
            implementation_risks.append(automation_message)
        if automation_message not in open_questions:
            open_questions.append(automation_message)

        if result.handoff_readiness_score < 90:
            safe_for_dev_planning = False
            if "implementation_planning" not in not_safe_to_generate:
                not_safe_to_generate.append("implementation_planning")

        return result.model_copy(
            update={
                "implementation_risks": implementation_risks,
                "open_questions": open_questions,
                "safe_for_dev_planning": safe_for_dev_planning,
                "not_safe_to_generate": not_safe_to_generate,
            }
        )

    def _merge_questions(self, existing: list[str], new_items: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []

        for item in existing + new_items:
            normalized = " ".join(item.split()).strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(item.strip())

        return merged
