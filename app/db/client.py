from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from supabase import Client

_client: "Client | None" = None


def get_db() -> "Client":
    global _client
    if _client is None:
        from supabase import create_client

        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client
