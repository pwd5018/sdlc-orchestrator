import json
import logging
from typing import Any

from pydantic import ValidationError

from app.models.requirements_models import (
    RequirementsAgentRequest,
    RequirementsAgentResult,
    build_requirements_response_schema,
)
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.provider_factory import create_provider
from app.services.prompt_loader import load_prompt


logger = logging.getLogger(__name__)


class RequirementsProcessingError(RuntimeError):
    """Raised when the requirements workflow cannot produce a valid result."""


class RequirementsService:
    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider
        self.requirements_prompt = load_prompt("requirements_agent.md")
        self.response_schema = build_requirements_response_schema()

    def run(self, request: RequirementsAgentRequest) -> RequirementsAgentResult:
        provider = self.llm_provider or create_provider()
        request_payload = json.dumps(request.model_dump(mode="json"), indent=2)

        llm_response = provider.generate_json(
            system_prompt=self.requirements_prompt,
            user_prompt=request_payload,
            response_schema=self.response_schema,
            temperature=0.2,
        )
        logger.info(
            "requirements processing started provider=%s model=%s",
            llm_response.provider_name,
            llm_response.model_name,
        )

        result = self._validate_or_repair(provider, request_payload, llm_response.content)
        logger.info(
            "requirements processing succeeded provider=%s model=%s requirements_readiness_score=%s",
            provider.provider_name,
            provider.model_name,
            result.requirements_readiness_score,
        )
        return result

    def _validate_or_repair(
        self,
        provider: BaseLLMProvider,
        request_payload: str,
        raw_response: str,
    ) -> RequirementsAgentResult:
        try:
            return self._validate_with_normalization(raw_response)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(
                "requirements json parse failure provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            logger.warning(
                "requirements repair retry attempt=1 provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            repaired_response = provider.generate_json(
                system_prompt=self.requirements_prompt,
                user_prompt=self._build_repair_prompt(request_payload, raw_response, str(exc)),
                response_schema=self.response_schema,
                temperature=0.2,
            ).content
            try:
                return self._validate_with_normalization(repaired_response)
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as repair_exc:
                logger.error(
                    "requirements processing failed after repair provider=%s model=%s",
                    provider.provider_name,
                    provider.model_name,
                )
                raise RequirementsProcessingError(
                    "The Requirements Agent returned invalid structured JSON after one repair attempt."
                ) from repair_exc

    def _validate_with_normalization(self, raw_response: str) -> RequirementsAgentResult:
        try:
            return RequirementsAgentResult.model_validate_json(raw_response)
        except ValidationError:
            normalized_payload = self._normalize_payload(raw_response)
            return RequirementsAgentResult.model_validate(normalized_payload)

    def _normalize_payload(self, raw_response: str) -> dict[str, Any]:
        payload = self._parse_json_object(raw_response)

        for list_field in (
            "functional_requirements",
            "non_functional_requirements",
            "business_rules",
            "data_requirements",
            "integration_requirements",
            "role_permission_requirements",
            "assumptions",
            "open_questions",
            "risks",
            "not_safe_to_generate",
        ):
            payload.setdefault(list_field, [])

        score = payload.get("requirements_readiness_score")
        normalized_score = self._coerce_int(score)
        if normalized_score is None:
            normalized_score = self._estimate_readiness_score(payload)
        payload["requirements_readiness_score"] = max(0, min(100, normalized_score))

        if "safe_for_jira_story_generation" not in payload:
            payload["safe_for_jira_story_generation"] = payload["requirements_readiness_score"] >= 70

        if "safe_for_test_design" not in payload:
            payload["safe_for_test_design"] = payload["requirements_readiness_score"] >= 70

        if not payload["not_safe_to_generate"] and payload["requirements_readiness_score"] < 70:
            payload["not_safe_to_generate"] = ["jira_story_generation", "test_design", "automation_design"]

        return payload

    def _parse_json_object(self, raw_response: str) -> dict[str, Any]:
        stripped = raw_response.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.startswith("json"):
                stripped = stripped[4:]
            stripped = stripped.strip()

        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError("Requirements agent response must be a JSON object.")
        return parsed

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        if isinstance(value, str) and value.strip():
            try:
                return int(float(value.strip()))
            except ValueError:
                return None
        return None

    def _estimate_readiness_score(self, payload: dict[str, Any]) -> int:
        evidence_fields = (
            "functional_requirements",
            "non_functional_requirements",
            "business_rules",
            "data_requirements",
            "integration_requirements",
            "role_permission_requirements",
        )
        evidence_count = sum(1 for field_name in evidence_fields if payload.get(field_name))
        open_question_count = len(payload.get("open_questions", []))
        assumption_count = len(payload.get("assumptions", []))

        score = 40 + (evidence_count * 8)
        score -= min(open_question_count * 4, 20)
        score -= min(assumption_count * 2, 10)

        if payload.get("functional_requirements") and payload.get("business_rules"):
            score += 8

        return max(0, min(95, score))

    def _build_repair_prompt(
        self,
        request_payload: str,
        invalid_response: str,
        validation_error: str,
    ) -> str:
        return json.dumps(
            {
                "task": "repair_invalid_requirements_json",
                "original_request": json.loads(request_payload),
                "invalid_response": invalid_response,
                "validation_error": validation_error,
                "instructions": [
                    "Repair the JSON so it exactly matches the required structure.",
                    "Do not add commentary.",
                    "Do not create Jira stories or test cases.",
                    "Keep ambiguity visible instead of masking it.",
                    "Return JSON only.",
                ],
            },
            indent=2,
        )
