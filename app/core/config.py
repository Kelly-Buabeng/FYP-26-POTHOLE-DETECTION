from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str

    # ML model
    model_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.35

    # App
    app_env: str = "development"
    app_port: int = 8000

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
