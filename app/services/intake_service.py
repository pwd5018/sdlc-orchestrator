import json
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from app.models.intake_models import (
    RunIntakeAIResult,
    RunIntakeRequest,
    RunIntakeResponse,
    build_openai_response_schema,
)
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.provider_factory import create_provider
from app.services.prompt_loader import load_prompt


logger = logging.getLogger(__name__)


class IntakeProcessingError(RuntimeError):
    """Raised when the intake workflow cannot produce a valid result."""


@dataclass(frozen=True)
class ReadinessDecision:
    can_continue: bool
    safe_to_generate: list[str]
    not_safe_to_generate: list[str]


class IntakeService:
    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider
        self.intake_prompt = load_prompt("intake_agent.md")
        self.response_schema = build_openai_response_schema()

    def run(self, request: RunIntakeRequest) -> RunIntakeResponse:
        logger.info("request started")

        provider = self.llm_provider or create_provider()
        request_payload = json.dumps(request.model_dump(mode="json"), indent=2)
        llm_response = provider.generate_json(
            system_prompt=self.intake_prompt,
            user_prompt=request_payload,
            response_schema=self.response_schema,
            temperature=0.2,
        )

        logger.info(
            "intake processing started provider=%s model=%s",
            llm_response.provider_name,
            llm_response.model_name,
        )

        ai_result = self._validate_or_repair(provider, request_payload, llm_response.content)
        readiness = self._classify_readiness(ai_result.readiness_score)

        response = RunIntakeResponse(
            feature_intake_packet=ai_result.feature_intake_packet,
            readiness_score=ai_result.readiness_score,
            can_continue=readiness.can_continue,
            blocking_gaps=self._dedupe(ai_result.blocking_gaps),
            clarification_questions=self._dedupe(ai_result.clarification_questions),
            safe_to_generate=readiness.safe_to_generate,
            not_safe_to_generate=readiness.not_safe_to_generate,
        )

        logger.info(
            "intake processing succeeded readiness_score=%s can_continue=%s",
            response.readiness_score,
            response.can_continue,
        )
        return response

    def _validate_or_repair(
        self,
        provider: BaseLLMProvider,
        request_payload: str,
        raw_response: str,
    ) -> RunIntakeAIResult:
        try:
            return RunIntakeAIResult.model_validate_json(raw_response)
        except ValidationError as exc:
            logger.warning(
                "json parse failure provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            logger.warning(
                "repair retry attempt=1 provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            repaired_response = provider.generate_json(
                system_prompt=self.intake_prompt,
                user_prompt=self._build_repair_prompt(request_payload, raw_response, str(exc)),
                response_schema=self.response_schema,
                temperature=0.2,
            ).content
            try:
                return RunIntakeAIResult.model_validate_json(repaired_response)
            except ValidationError as repair_exc:
                logger.error(
                    "intake processing failed after repair provider=%s model=%s",
                    provider.provider_name,
                    provider.model_name,
                )
                raise IntakeProcessingError(
                    "The Intake Agent returned invalid structured JSON after one repair attempt."
                ) from repair_exc

    def _build_repair_prompt(
        self,
        request_payload: str,
        invalid_response: str,
        validation_error: str,
    ) -> str:
        return json.dumps(
            {
                "task": "repair_invalid_intake_json",
                "original_request": json.loads(request_payload),
                "invalid_response": invalid_response,
                "validation_error": validation_error,
                "instructions": [
                    "Repair the JSON so it exactly matches the required structure.",
                    "Do not add commentary.",
                    "Keep the clarification questions prioritized with blocking gaps first.",
                    "Return JSON only.",
                ],
            },
            indent=2,
        )

    def _classify_readiness(self, readiness_score: int) -> ReadinessDecision:
        logger.info("readiness score evaluated score=%s", readiness_score)

        if readiness_score >= 90:
            return ReadinessDecision(
                can_continue=True,
                safe_to_generate=[
                    "full_sdlc_package",
                    "jira_story_generation",
                    "test_case_generation",
                    "automation_recommendations",
                ],
                not_safe_to_generate=[],
            )

        if readiness_score >= 70:
            return ReadinessDecision(
                can_continue=True,
                safe_to_generate=[
                    "draft_sdlc_package",
                    "draft_jira_stories_with_assumptions",
                    "draft_test_cases_with_assumptions",
                    "draft_automation_recommendations_with_assumptions",
                ],
                not_safe_to_generate=[
                    "finalized_delivery_artifacts_without_human_review",
                ],
            )

        if readiness_score >= 50:
            return ReadinessDecision(
                can_continue=False,
                safe_to_generate=[
                    "discovery_summary",
                    "clarification_questions",
                    "readiness_feedback",
                ],
                not_safe_to_generate=[
                    "full_sdlc_package",
                    "jira_story_generation",
                    "test_case_generation",
                    "automation_recommendations",
                ],
            )

        return ReadinessDecision(
            can_continue=False,
            safe_to_generate=[
                "clarification_questions",
                "readiness_feedback",
            ],
            not_safe_to_generate=[
                "full_sdlc_package",
                "jira_story_generation",
                "test_case_generation",
                "automation_recommendations",
                "discovery_summary_generation_without_better_input",
            ],
        )

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []

        for item in items:
            normalized = " ".join(item.split()).strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(item.strip())

        return deduped
