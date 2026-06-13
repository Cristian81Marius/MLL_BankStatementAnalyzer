from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    anthropic_api_key: str
    api_key: str

    claude_model: str = "claude-haiku-4-5-20251001"
    llm_max_tokens: int = 4096
    llm_max_content_chars: int = 12000

    max_file_size_bytes: int = 50 * 1024 * 1024

    log_level: str = "INFO"
    debug: bool = False
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
