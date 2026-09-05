import secrets

from fastapi import Header, HTTPException, status

from app.core.config import get_settings

# Placeholder from .env.example — treat it the same as "unconfigured" so a
# copied-verbatim .env doesn't look secured when it isn't.
_PLACEHOLDER_KEYS = {"", "change-this-in-production"}


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    """
    Guards write/destructive/export routes. If API_KEY isn't configured (or is
    still the .env.example placeholder), auth is skipped — intended for local
    dev/test only; production deployments must set a real API_KEY.
    """
    configured_key = get_settings().api_key.strip()
    if configured_key in _PLACEHOLDER_KEYS:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header.",
        )
