from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ML model
    model_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.35

    # App
    app_env: str = "development"
    app_port: int = 8000

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
