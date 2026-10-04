"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_vision_model: str = ""
    sleep_seconds: float = 30.0
    ai_provider_chain: str = "groq,cache,mock"
    database_url: str = "sqlite:///./aqualens.db"
    expert_pin: str = "change-me"
    fhir_server_url: str = "https://hapi.fhir.org/baseR4"
    fhir_codesystem_url: str = (
        "https://example.org/aqualens/CodeSystem/stream-observation"
    )
    cors_origins: str = "http://localhost:5173"
    storage_backend: str = "local"
    upload_dir: str = "../uploads"
    ai_cache_dir: str = "../cache/ai"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "aqualens-photos"

    @property
    def ai_chain_list(self) -> list[str]:
        return [part.strip() for part in self.ai_provider_chain.split(",") if part.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
