import logging
from typing import Any

from openai import OpenAI

from app.config import Settings
from app.services.llm.base_provider import BaseLLMProvider, LLMConfigurationError, LLMProviderError, LLMResponse


logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")

        self.model_name = settings.openai_model_name
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout_seconds,
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        try:
            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}],
                    },
                ],
                temperature=temperature,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "intake_agent_output",
                        "strict": True,
                        "schema": response_schema or {},
                    }
                },
            )
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                content=response.output_text,
            )
        except Exception as exc:  # pragma: no cover - external API behavior
            logger.exception("llm provider request failed provider=%s model=%s", self.provider_name, self.model_name)
            raise LLMProviderError("OpenAI request failed during intake generation.") from exc
