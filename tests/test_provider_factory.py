from app.config import Settings
from app.services.llm.base_provider import LLMConfigurationError
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.provider_factory import create_provider


def test_provider_factory_returns_openai_provider() -> None:
    settings = Settings(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model_name="gpt-4.1-mini",
        groq_api_key="",
        groq_model_name="llama-3.1-8b-instant",
        llm_timeout_seconds=60.0,
    )

    provider = create_provider(settings)

    assert isinstance(provider, OpenAIProvider)


def test_provider_factory_returns_groq_provider() -> None:
    settings = Settings(
        llm_provider="groq",
        openai_api_key="",
        openai_model_name="gpt-4.1-mini",
        groq_api_key="test-key",
        groq_model_name="llama-3.1-8b-instant",
        llm_timeout_seconds=60.0,
    )

    provider = create_provider(settings)

    assert isinstance(provider, GroqProvider)


def test_provider_factory_fails_for_unsupported_provider() -> None:
    settings = Settings(
        llm_provider="ollama",
        openai_api_key="",
        openai_model_name="gpt-4.1-mini",
        groq_api_key="",
        groq_model_name="llama-3.1-8b-instant",
        llm_timeout_seconds=60.0,
    )

    try:
        create_provider(settings)
    except LLMConfigurationError as exc:
        assert "Unsupported LLM_PROVIDER 'ollama'" in str(exc)
    else:
        raise AssertionError("Expected unsupported provider to raise LLMConfigurationError.")
