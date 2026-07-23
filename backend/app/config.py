"""Application settings from environment / .env. Secrets never hard-coded."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://icc:icc@localhost:5432/icc"
    anthropic_api_key: str = ""
    model_cheap: str = "claude-haiku-4-5-20251001"
    model_strong: str = "claude-sonnet-5"
    serving_url: str = "http://localhost:8001"
    cors_origins: str = "http://localhost:5173"

    # Per-model cost table ($ per 1M tokens: input, output). Used for agent-run costing (ITER_02).
    # Values are illustrative defaults; override via env if pricing changes.
    cost_per_mtok_input: float = 1.0
    cost_per_mtok_output: float = 5.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    # gotcha (cached-config): settings are cached; test fixtures must call
    # get_settings.cache_clear() after mutating the environment.
    return Settings()
