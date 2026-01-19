from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_together import ChatTogether


class SupportedModels(Enum):
    # Large models
    META_LLAMA_3_1_405B = (
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        ChatTogether,
    )
    QWEN_3_235B = ("Qwen/Qwen3-235B-A22B-fp8-tput", ChatTogether)
    DEEPSEEK_R1 = ("deepseek-ai/DeepSeek-R1", ChatTogether)
    DEEPSEEK_V3 = ("deepseek-ai/DeepSeek-V3", ChatTogether)

    # Medium models
    META_LLAMA_3_3_70B = ("meta-llama/Llama-3.3-70B-Instruct-Turbo", ChatTogether)

    # Small models
    QWEN_2_5_7B_TURBO = ("Qwen/Qwen2.5-7B-Instruct-Turbo", ChatTogether)
    META_LLAMA_3_2_3B_TURBO = ("meta-llama/Llama-3.2-3B-Instruct-Turbo", ChatTogether)
    META_LLAMA_3_8B_LITE = ("meta-llama/Meta-Llama-3-8B-Instruct-Lite", ChatTogether)

    # Google models
    GEMINI_2_0_FLASH = ("gemini-2.0-flash", ChatGoogleGenerativeAI)
    GEMINI_2_5_PRO = ("gemini-2.5-pro", ChatGoogleGenerativeAI)

    def __init__(
        self,
        model_name: str,
        model_provider: type[ChatTogether] | type[ChatGoogleGenerativeAI],
    ):
        self.model_name = model_name
        self.model_provider = model_provider


class SupportedGoogleModels(Enum):
    """Google AI models supported by the system."""

    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_provider = ChatGoogleGenerativeAI


class SupportedTogetherModels(Enum):
    """Together AI models supported by the system."""

    # Large models
    META_LLAMA_3_1_405B = "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
    QWEN_3_235B = "Qwen/Qwen3-235B-A22B-fp8-tput"
    DEEPSEEK_R1 = "deepseek-ai/DeepSeek-R1"
    DEEPSEEK_V3 = "deepseek-ai/DeepSeek-V3"

    # Medium models
    META_LLAMA_3_3_70B = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

    # Small models
    QWEN_2_5_7B_TURBO = "Qwen/Qwen2.5-7B-Instruct-Turbo"
    META_LLAMA_3_2_3B_TURBO = "meta-llama/Llama-3.2-3B-Instruct-Turbo"
    META_LLAMA_3_8B_LITE = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_provider = ChatTogether
