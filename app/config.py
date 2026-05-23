import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


load_dotenv()


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm_provider: str = Field(default="openai")
    orchestrator_api_key: str = Field(default="")
    public_base_url: str = Field(default="http://127.0.0.1:8000")
    openai_api_key: str = Field(default="")
    openai_model_name: str = Field(default="gpt-4.1-mini")
    groq_api_key: str = Field(default="")
    groq_model_name: str = Field(default="llama-3.1-8b-instant")
    llm_timeout_seconds: float = Field(default=60.0)
    policysphere_lab_path: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai").strip() or "openai",
        orchestrator_api_key=os.getenv("ORCHESTRATOR_API_KEY", "").strip(),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").strip()
        or "http://127.0.0.1:8000",
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model_name=(
            os.getenv("OPENAI_MODEL_NAME")
            or os.getenv("MODEL_NAME")
            or "gpt-4.1-mini"
        ).strip(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.1-8b-instant").strip()
        or "llama-3.1-8b-instant",
        llm_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
        policysphere_lab_path=os.getenv("POLICYSPHERE_LAB_PATH", "").strip(),
    )
