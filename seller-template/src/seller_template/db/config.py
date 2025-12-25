from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database-specific settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore", env_file=".env")

    # Example: database_url: str = "sqlite:///./test.db"
    # For in-memory, we don't need a specific URL, but this serves as a placeholder
    database_url: str = ""

def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()
