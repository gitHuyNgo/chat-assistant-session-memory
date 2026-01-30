from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration management for the application.

    Configuration values are sourced from environment variables, optionally
    loaded from a `.env` file, and validated using Pydantic's type system.
    """

    OPENAI_API_KEY: str
    MODEL_NAME: str = "gpt-4o"
    MEMORY_THRESHOLD_TOKENS: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",  # Target environment file
        env_file_encoding="utf-8",  # Standard encoding
        extra="ignore",  # Ignore unknown variables in the environment
    )


# Instantiate settings at import time to provide a single source of truth.
settings = Settings()