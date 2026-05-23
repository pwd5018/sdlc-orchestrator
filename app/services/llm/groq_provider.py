import logging
from typing import Any

from openai import OpenAI

from app.config import Settings
from app.services.llm.base_provider import BaseLLMProvider, LLMConfigurationError, LLMProviderError, LLMResponse


logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    provider_name = "groq"

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise LLMConfigurationError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")

        self.model_name = settings.groq_model_name
        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
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
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=max(temperature, 1e-8),
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "intake_agent_output",
                        "strict": False,
                        "schema": response_schema or {},
                    },
                },
            )
            content = response.choices[0].message.content or ""
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                content=content,
            )
        except Exception as exc:  # pragma: no cover - external API behavior
            logger.exception("llm provider request failed provider=%s model=%s", self.provider_name, self.model_name)
            raise LLMProviderError("Groq request failed during intake generation.") from exc
