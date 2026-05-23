import logging

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.config import get_settings


logger = logging.getLogger(__name__)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(x_api_key: str | None = Security(api_key_header)) -> None:
    settings = get_settings()
    configured_key = settings.orchestrator_api_key

    if not configured_key:
        logger.warning("orchestrator api key is not configured; allowing protected endpoint access in local/dev mode")
        return

    if x_api_key != configured_key:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid X-API-Key header.",
        )
