import logging

from langchain_core.language_models import BaseLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_together import ChatTogether

from xy_market.vendor.model_registry.chat_models import (
    SupportedGoogleModels,
    SupportedModels,
    SupportedTogetherModels,
)
from xy_market.vendor.model_registry.config import ModelConfig

logger = logging.getLogger(__name__)


def get_model(model: SupportedModels, **model_kwargs) -> BaseLLM:
    """
    Creates and returns an LLM instance for the given model and configuration.

    Args:
        model: The selected model from SupportedModels (e.g., SupportedModels.GEMINI_2_0_FLASH)
        **model_kwargs: Keyword arguments specific to the model's configuration.
            - For Google models: `google_api_key` (str) - Required if not set via GOOGLE_API_KEY env var
            - For Together AI models: `together_api_key` (str) - Required if not set via TOGETHER_API_KEY env var

    Returns:
        An instance of the selected BaseChatModel.

    Raises:
        ValueError: If model initialization fails (e.g., missing API key, invalid kwargs)

    Environment Variables:
        GOOGLE_API_KEY: Single Google API key (used by LangChain if google_api_key not in kwargs)
        TOGETHER_API_KEY: Single Together API key (used by LangChain if together_api_key not in kwargs)

        Note: You can also use ModelConfig with GOOGLE_API_KEYS/TOGETHER_API_KEYS (JSON arrays)
        and pass keys explicitly: get_model(..., google_api_key=config.google_api_keys[0])

    Examples:
        ```python
        from xy_market.vendor.model_registry import get_model, SupportedModels, ModelConfig

        # Option 1: Pass API key directly
        llm = get_model(SupportedModels.GEMINI_2_0_FLASH, google_api_key="your-key-here")

        # Option 2: Rely on GOOGLE_API_KEY environment variable (LangChain will use it)
        # Set: export GOOGLE_API_KEY="your-key-here"
        llm = get_model(SupportedModels.GEMINI_2_0_FLASH)

        # Option 3: Use ModelConfig (access some key from list)
        config = ModelConfig()
        if config.google_api_keys:
            llm = get_model(SupportedModels.GEMINI_2_0_FLASH, google_api_key=config.google_api_keys[0])
        ```

    """
    try:
        llm_model = model.model_provider(model=model.model_name, **model_kwargs)
        logger.info(f"Successfully initialized model {model.model_name}.")
        return llm_model

    except TypeError as e:
        logger.error(f"Error initializing model {model.model_name}: {e}")
        raise ValueError(
            f"Error initializing model {model.model_name} with kwargs {model_kwargs}. "
            f"Ensure the arguments are valid for this model."
        ) from e


def get_multiple_model_instances(
    model_names: list[str],
    google_api_keys: list[str] | None = None,
    together_api_keys: list[str] | None = None,
) -> list[BaseLLM]:
    """
    Creates multiple model instances - one for each API key.

    This function takes model names and creates multiple instances:
    - For Google models: creates one instance per Google API key
    - For Together AI models: creates one instance per Together API key

    :param model_names: List of model names (e.g., ["GEMINI_2_0_FLASH", "META_LLAMA_3_3_70B"])
    :param google_api_keys: List of Google API keys (e.g., ["Bsg4", "I0qE"])
    :param together_api_keys: List of Together AI API keys (e.g., ["8e14f765"])
    :param model_kwargs: Additional keyword arguments for model configuration
    :return: List of initialized model instances

    Example:
        models = create_multiple_model_instances(
            ["GEMINI_2_0_FLASH", "META_LLAMA_3_3_70B"],
            google_api_keys=["Bsg4", "I0qE"],
            together_api_keys=["8e14f765"]
        )
        # Returns: [GEMINI_2_0_FLASH with key Bsg4, GEMINI_2_0_FLASH with key I0qE, META_LLAMA_3_3_70B with key 8e14f765]

    """
    if not google_api_keys and not together_api_keys:
        config = ModelConfig()
        google_api_keys = config.google_api_keys
        together_api_keys = config.together_api_keys

    model_instances = []

    for model_name in model_names:
        try:
            # Get the model enum
            model_enum = getattr(SupportedModels, model_name)

            if model_enum.model_provider == ChatGoogleGenerativeAI:
                # Create one instance per Google API key
                for api_key in google_api_keys:
                    try:
                        llm = get_model(
                            SupportedGoogleModels[model_name],
                            google_api_key=api_key,
                        )
                        model_instances.append(llm)
                        logger.info(
                            f"✅ {model_name} initialized with Google API key: {api_key[:4]}..."
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize {model_name} with Google API key {api_key[:4]}...: {e}"
                        )

            elif model_enum.model_provider == ChatTogether:
                # Create one instance per Together AI API key
                for api_key in together_api_keys:
                    try:
                        llm = get_model(
                            SupportedTogetherModels[model_name],
                            together_api_key=api_key,
                        )
                        model_instances.append(llm)
                        logger.info(
                            f"✅ {model_name} initialized with Together AI API key: {api_key[:4]}..."
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize {model_name} with Together AI API key {api_key[:4]}...: {e}"
                        )

            else:
                logger.warning(f"Unknown model provider for {model_name}")

        except AttributeError as e:
            logger.error(f"Model {model_name} not found in SupportedModels: {e}")
        except Exception as e:
            logger.error(f"Failed to process model {model_name}: {e}")

    if not model_instances:
        raise ValueError("No models were successfully initialized")

    logger.info(f"🎉 Successfully created {len(model_instances)} model instances")
    return model_instances
