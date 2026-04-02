from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    api_title: str = "Qualitative AI Interview Studio API"
    api_version: str = "0.1.0"
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_root: Path = Field(default=Path("backend_data"), alias="LOCAL_STORAGE_ROOT")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = BackendSettings()
