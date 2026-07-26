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

    # Fallback per-model cost ($ per 1M tokens: input, output) for models absent from the table below.
    cost_per_mtok_input: float = 1.0
    cost_per_mtok_output: float = 5.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def model_cost_table(self) -> dict[str, tuple[float, float]]:
        """Per-model ($/Mtok input, $/Mtok output). Illustrative tiering: cheap monitor, strong
        diagnosis. Keyed by the configured model ids so agent-run costing tiers by which model ran."""
        return {
            self.model_cheap: (0.80, 4.00),
            self.model_strong: (3.00, 15.00),
        }

    def cost_usd(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rate_in, rate_out = self.model_cost_table.get(
            model, (self.cost_per_mtok_input, self.cost_per_mtok_output)
        )
        return (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000


@lru_cache
def get_settings() -> Settings:
    # gotcha (cached-config): settings are cached; test fixtures must call
    # get_settings.cache_clear() after mutating the environment.
    return Settings()
