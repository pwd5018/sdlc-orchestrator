from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LLMConfigurationError(RuntimeError):
    """Raised when a provider is configured incorrectly."""


class LLMProviderError(RuntimeError):
    """Raised when a provider request fails."""


@dataclass(frozen=True)
class LLMResponse:
    provider_name: str
    model_name: str
    content: str


class BaseLLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Generate structured JSON content from the selected LLM provider."""
