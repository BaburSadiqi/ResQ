from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RESQ_", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/resq",
        pattern=r"^postgresql\+asyncpg://",
    )
    usgs_base_url: AnyHttpUrl = "https://earthquake.usgs.gov/fdsnws/event/1"
    log_level: str = "INFO"
    http_timeout_seconds: float = Field(default=15, gt=0, le=60)


@lru_cache
def get_settings() -> Settings:
    return Settings()
