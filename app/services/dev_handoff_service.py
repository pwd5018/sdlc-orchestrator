import json
import logging

from pydantic import ValidationError

from app.models.dev_handoff_models import (
    DevHandoffAgentRequest,
    DevHandoffAgentResult,
    build_dev_handoff_response_schema,
)
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.provider_factory import create_provider
from app.services.prompt_loader import load_prompt


logger = logging.getLogger(__name__)


class DevHandoffProcessingError(RuntimeError):
    """Raised when the Dev Handoff workflow cannot produce a valid result."""


class DevHandoffService:
    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider
        self.dev_handoff_prompt = load_prompt("dev_handoff_agent.md")
        self.response_schema = build_dev_handoff_response_schema()

    def run(self, request: DevHandoffAgentRequest) -> DevHandoffAgentResult:
        provider = self.llm_provider or create_provider()
        request_payload = json.dumps(request.model_dump(mode="json"), indent=2)

        llm_response = provider.generate_json(
            system_prompt=self.dev_handoff_prompt,
            user_prompt=request_payload,
            response_schema=self.response_schema,
            temperature=0.2,
        )
        logger.info(
            "dev handoff processing started provider=%s model=%s",
            llm_response.provider_name,
            llm_response.model_name,
        )

        result = self._validate_or_repair(provider, request_payload, llm_response.content)
        logger.info(
            "dev handoff processing succeeded provider=%s model=%s handoff_readiness_score=%s",
            provider.provider_name,
            provider.model_name,
            result.handoff_readiness_score,
        )
        return result

    def _validate_or_repair(
        self,
        provider: BaseLLMProvider,
        request_payload: str,
        raw_response: str,
    ) -> DevHandoffAgentResult:
        try:
            return DevHandoffAgentResult.model_validate_json(raw_response)
        except ValidationError as exc:
            logger.warning(
                "dev handoff json parse failure provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            logger.warning(
                "dev handoff repair retry attempt=1 provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            repaired_response = provider.generate_json(
                system_prompt=self.dev_handoff_prompt,
                user_prompt=self._build_repair_prompt(request_payload, raw_response, str(exc)),
                response_schema=self.response_schema,
                temperature=0.2,
            ).content
            try:
                return DevHandoffAgentResult.model_validate_json(repaired_response)
            except ValidationError as repair_exc:
                logger.error(
                    "dev handoff processing failed after repair provider=%s model=%s",
                    provider.provider_name,
                    provider.model_name,
                )
                raise DevHandoffProcessingError(
                    "The Dev Handoff Agent returned invalid structured JSON after one repair attempt."
                ) from repair_exc

    def _build_repair_prompt(
        self,
        request_payload: str,
        invalid_response: str,
        validation_error: str,
    ) -> str:
        return json.dumps(
            {
                "task": "repair_invalid_dev_handoff_json",
                "original_request": json.loads(request_payload),
                "invalid_response": invalid_response,
                "validation_error": validation_error,
                "instructions": [
                    "Repair the JSON so it exactly matches the required structure.",
                    "Do not add commentary.",
                    "Do not generate production code or implementation snippets.",
                    "Do not invent architecture, endpoints, or schemas that were not provided.",
                    "Return JSON only.",
                ],
            },
            indent=2,
        )
