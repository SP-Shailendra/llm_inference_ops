"""
Application-wide constants.

This file contains all platform-wide constants used across the
LLM Inference Operations Platform.

Avoid hardcoding strings anywhere else in the project.
"""


class ProfileNames:
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    COST_SAVER = "cost_saver"


class RoutingTier:
    AUTO = "auto"
    PREMIUM = "tier_1_premium"
    BALANCED = "tier_2_balanced"
    LOW_COST = "tier_3_low_cost"


class Provider:
    GROQ = "Groq"
    OPENAI = "OpenAI"
    GEMINI = "Gemini"
    ANTHROPIC = "Anthropic"
    OLLAMA = "Ollama"
    VLLM = "vLLM"


class ModelName:
    LLAMA_8B = "llama3-8b-8192"
    LLAMA_70B = "llama3-70b-8192"


class RuntimeStage:
    GOVERNANCE = "Governance"
    POLICY = "Policy"
    BUDGET = "Budget"
    ROUTING = "Routing"
    CACHE = "Cache"
    PROMPT = "Prompt"
    INFERENCE = "Inference"
    TELEMETRY = "Telemetry"
    ADVISOR = "Advisor"
    RESPONSE = "Response"


class FeatureFlag:
    CACHE = "enable_cache"
    PROMPT_COMPRESSION = "enable_prompt_compression"
    AGENT_MODE = "enable_agentic_loop"
    STREAMING = "enable_streaming"
    AUTO_ROUTING = "enable_auto_routing"
    SPECULATIVE_DECODING = "enable_speculative_decoding"
    CANARY = "enable_canary"
    ROLLBACK = "enable_rollback"


class Limits:
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TOP_P = 0.95
    DEFAULT_TIMEOUT = 60


class Analytics:
    MAX_LOGS = 100


class WorkloadType:
    CHAT             = "chat"
    CODING           = "coding"
    CODE_REVIEW      = "code_review"
    DEBUGGING        = "debugging"
    SQL              = "sql"
    JSON_GENERATION  = "json_generation"
    TRANSLATION      = "translation"
    SUMMARIZATION    = "summarization"
    RESEARCH         = "research"
    PLANNING         = "planning"
    RAG              = "rag"
    AGENT_WORKFLOW   = "agent_workflow"
    CREATIVE_WRITING = "creative_writing"
    SENTIMENT        = "sentiment_analysis"
    CLASSIFICATION   = "classification"
    EXTRACTION       = "extraction"
    QUESTION_ANSWER  = "question_answer"
    ADVISORY         = "advisory"
    UNKNOWN          = "unknown"