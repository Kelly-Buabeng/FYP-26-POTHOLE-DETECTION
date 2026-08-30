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

    # API authentication
    api_key: str = "dev-key-change-in-production"

    # Ghana geographic bounding box — reject coordinates outside this range
    ghana_lat_min: float = 4.5
    ghana_lat_max: float = 11.5
    ghana_lng_min: float = -3.5
    ghana_lng_max: float = 1.5

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
