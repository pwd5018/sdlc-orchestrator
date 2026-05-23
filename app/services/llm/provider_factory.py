import logging

from app.config import Settings, get_settings
from app.services.llm.base_provider import BaseLLMProvider, LLMConfigurationError
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.openai_provider import OpenAIProvider


logger = logging.getLogger(__name__)


def create_provider(settings: Settings | None = None) -> BaseLLMProvider:
    resolved_settings = settings or get_settings()
    provider_name = resolved_settings.llm_provider.lower().strip()

    if provider_name == "openai":
        provider = OpenAIProvider(resolved_settings)
    elif provider_name == "groq":
        provider = GroqProvider(resolved_settings)
    else:
        raise LLMConfigurationError(
            f"Unsupported LLM_PROVIDER '{resolved_settings.llm_provider}'. "
            "Supported providers are: openai, groq."
        )

    logger.info("selected llm provider provider=%s model=%s", provider.provider_name, provider.model_name)
    return provider
