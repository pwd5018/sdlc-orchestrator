import json
import logging

from pydantic import ValidationError

from app.models.automation_design_models import (
    AutomationDesignAgentRequest,
    AutomationDesignAgentResult,
    build_automation_design_response_schema,
)
from app.services.llm.base_provider import BaseLLMProvider
from app.services.llm.provider_factory import create_provider
from app.services.prompt_loader import load_prompt

__test__ = False


logger = logging.getLogger(__name__)


class AutomationDesignProcessingError(RuntimeError):
    """Raised when the Automation Design workflow cannot produce a valid result."""


class AutomationDesignService:
    def __init__(self, llm_provider: BaseLLMProvider | None = None) -> None:
        self.llm_provider = llm_provider
        self.automation_design_prompt = load_prompt("automation_design_agent.md")
        self.response_schema = build_automation_design_response_schema()

    def run(self, request: AutomationDesignAgentRequest) -> AutomationDesignAgentResult:
        provider = self.llm_provider or create_provider()
        request_payload = json.dumps(request.model_dump(mode="json"), indent=2)

        llm_response = provider.generate_json(
            system_prompt=self.automation_design_prompt,
            user_prompt=request_payload,
            response_schema=self.response_schema,
            temperature=0.2,
        )
        logger.info(
            "automation design processing started provider=%s model=%s",
            llm_response.provider_name,
            llm_response.model_name,
        )

        result = self._validate_or_repair(provider, request_payload, llm_response.content)
        logger.info(
            "automation design processing succeeded provider=%s model=%s automation_design_readiness_score=%s",
            provider.provider_name,
            provider.model_name,
            result.automation_design_readiness_score,
        )
        return result

    def _validate_or_repair(
        self,
        provider: BaseLLMProvider,
        request_payload: str,
        raw_response: str,
    ) -> AutomationDesignAgentResult:
        try:
            return AutomationDesignAgentResult.model_validate_json(raw_response)
        except ValidationError as exc:
            logger.warning(
                "automation design json parse failure provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            logger.warning(
                "automation design repair retry attempt=1 provider=%s model=%s",
                provider.provider_name,
                provider.model_name,
            )
            repaired_response = provider.generate_json(
                system_prompt=self.automation_design_prompt,
                user_prompt=self._build_repair_prompt(request_payload, raw_response, str(exc)),
                response_schema=self.response_schema,
                temperature=0.2,
            ).content
            try:
                return AutomationDesignAgentResult.model_validate_json(repaired_response)
            except ValidationError as repair_exc:
                logger.error(
                    "automation design processing failed after repair provider=%s model=%s",
                    provider.provider_name,
                    provider.model_name,
                )
                raise AutomationDesignProcessingError(
                    "The Automation Design Agent returned invalid structured JSON after one repair attempt."
                ) from repair_exc

    def _build_repair_prompt(
        self,
        request_payload: str,
        invalid_response: str,
        validation_error: str,
    ) -> str:
        return json.dumps(
            {
                "task": "repair_invalid_automation_design_json",
                "original_request": json.loads(request_payload),
                "invalid_response": invalid_response,
                "validation_error": validation_error,
                "instructions": [
                    "Repair the JSON so it exactly matches the required structure.",
                    "Do not add commentary.",
                    "Do not generate test automation framework code.",
                    "Do not invent architecture that is not present in the request.",
                    "Return JSON only.",
                ],
            },
            indent=2,
        )
