from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    """
    Configuration for model initialization.

    This class defines the public contract for environment variables required
    to initialize models from xy_market.vendor.model_registry.

    Environment Variables:
        GOOGLE_API_KEYS: JSON array of Google API keys (e.g., '["key1","key2","key3"]')
        TOGETHER_API_KEYS: JSON array of Together AI API keys (e.g., '["key1","key2","key3"]')

        Alternatively, you can manually create:
        GOOGLE_API_KEY: Single Google API key (used by LangChain if not passed as kwarg)
        TOGETHER_API_KEY: Single Together API key (used by LangChain if not passed as kwarg)

    Examples:
        ```python
        from xy_market.vendor.model_registry import ModelConfig, get_model, SupportedModels

        # Load config from environment
        config = ModelConfig()

        # Use first key for get_model()
        if config.google_api_keys:
            llm = get_model(SupportedModels.GEMINI_2_0_FLASH, google_api_key=config.google_api_keys[0])

        # Use all keys for get_multiple_model_instances()
        models = get_multiple_model_instances(
            ["GEMINI_2_0_FLASH"],
            google_api_keys=config.google_api_keys
        )
        ```

    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    google_api_keys: list[str] = []
    """List of Google API keys loaded from GOOGLE_API_KEYS environment variable."""

    together_api_keys: list[str] = []
    """List of Together API keys loaded from TOGETHER_API_KEYS environment variable."""

    @field_validator("google_api_keys", "together_api_keys", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str] | None) -> list[str]:
        """Parse comma-separated string into list, or return list as-is."""
        if v is None:
            return []
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [key.strip() for key in v.split(",") if key.strip()]
        if isinstance(v, list):
            return v
        return []
