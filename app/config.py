from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Application Config
    PROJECT_NAME: str = "LLM Inference Ops Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Primary LLM API Keys
    GROQ_API_KEY: str
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    NVIDIA_NIM_API_KEY: Optional[str] = None
    ALIBABA_API_KEY: Optional[str] = None

    # Optional provider endpoints (for hosted/self-hosted OpenAI-compatible APIs)
    OPENAI_BASE_URL: Optional[str] = None
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    MISTRAL_BASE_URL: str = "https://api.mistral.ai/v1"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    NVIDIA_NIM_BASE_URL: Optional[str] = None
    ALIBABA_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    # Local SLM Config
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    VLLM_BASE_URL: Optional[str] = None
    TGI_BASE_URL: Optional[str] = None
    LLAMACPP_BASE_URL: Optional[str] = None
    VLLM_METRICS_URL: Optional[str] = None
    TGI_METRICS_URL: Optional[str] = None

    # Pydantic configuration to read from the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate the settings so they can be imported anywhere in the app
settings = Settings()