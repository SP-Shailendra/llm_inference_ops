from enum import Enum


class OptimizationProfile(str, Enum):
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    COST_SAVER = "cost_saver"


class Provider(str, Enum):
    GROQ = "Groq"
    OPENAI = "OpenAI"
    GEMINI = "Gemini"
    OLLAMA = "Ollama"


class RuntimeStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CACHE_HIT = "cache_hit"


class CacheStatus(str, Enum):
    HIT = "hit"
    MISS = "miss"


class RoutingMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"