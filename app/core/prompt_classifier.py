"""
Prompt Intelligence Engine
--------------------------
Classifies every incoming prompt into a workload type and extracts
intelligence that drives parameter tuning, routing, and advisory decisions.

No LLM call required — purely rule-based + keyword pattern matching.
"""

from dataclasses import dataclass, field
from typing import Optional
import re


# ─────────────────────────────────────────────
# Workload Types
# ─────────────────────────────────────────────

class WorkloadType:
    CHAT            = "chat"
    CODING          = "coding"
    CODE_REVIEW     = "code_review"
    DEBUGGING       = "debugging"
    SQL             = "sql"
    JSON_GENERATION = "json_generation"
    TRANSLATION     = "translation"
    SUMMARIZATION   = "summarization"
    RESEARCH        = "research"
    PLANNING        = "planning"
    RAG             = "rag"
    FUNCTION_CALLING = "function_calling"
    AGENT_WORKFLOW  = "agent_workflow"
    CREATIVE_WRITING = "creative_writing"
    SENTIMENT       = "sentiment_analysis"
    CLASSIFICATION  = "classification"
    EXTRACTION      = "extraction"
    QUESTION_ANSWER = "question_answer"
    ADVISORY        = "advisory"           # "which model should I use for X?"
    UNKNOWN         = "unknown"


class ComplexityLevel:
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class ReasoningLevel:
    MINIMAL  = "minimal"
    MODERATE = "moderate"
    DEEP     = "deep"


class SafetyRisk:
    SAFE     = "safe"
    MODERATE = "moderate"
    HIGH     = "high"


# ─────────────────────────────────────────────
# Classification Result
# ─────────────────────────────────────────────

@dataclass
class PromptClassification:
    workload_type: str = WorkloadType.UNKNOWN
    complexity: str = ComplexityLevel.MEDIUM
    reasoning_level: str = ReasoningLevel.MODERATE
    safety_risk: str = SafetyRisk.SAFE
    estimated_input_tokens: int = 0
    recommended_max_tokens: int = 1024
    recommended_temperature: float = 0.7
    requires_large_context: bool = False
    is_advisory_query: bool = False
    confidence: int = 70              # 0–100
    classification_reason: str = ""   # Human-readable explanation


# ─────────────────────────────────────────────
# Keyword Patterns (workload → keyword sets)
# ─────────────────────────────────────────────

_WORKLOAD_PATTERNS: list[tuple[str, list[str]]] = [
    # Advisory MUST come first — catch "which model", "best model for" etc.
    (WorkloadType.ADVISORY, [
        "which model", "best model", "which llm", "best llm", "recommend a model",
        "what model", "which provider", "best provider", "should i use",
        "which ai", "what ai", "i want to build", "building a platform",
        "building an ai", "best for coding", "best for translation",
        "best for summarization", "best ai for", "model recommendation",
        "estimated cost", "gpu recommendation", "self-hosted vs", "api vs",
        "deployment strategy", "choose between", "suggest a model",
        "which approach for ai", "what llm"
    ]),
    (WorkloadType.DEBUGGING, [
        "debug", "fix this error", "traceback", "exception", "error:", "why is this failing",
        "not working", "bug", "issue with", "stack trace", "segfault", "undefined",
        "null pointer", "type error", "syntax error", "runtime error"
    ]),
    (WorkloadType.CODE_REVIEW, [
        "review this code", "code review", "check my code", "improve this code",
        "refactor", "is this code correct", "code quality", "best practices",
        "optimize this function", "what's wrong with this",
        "review this", "suggest improvements", "improve this function",
        "review my", "feedback on this code", "is this good code"
    ]),
    (WorkloadType.CODING, [
        "write a function", "write code", "implement", "create a class", "generate code",
        "code for", "script to", "program that", "write a script", "python function",
        "javascript function", "typescript", "react component", "api endpoint",
        "test script", "unit test", "write tests", "test case", "automate"
    ]),
    (WorkloadType.SQL, [
        "sql query", "write a query", "select from", "join table", "database query",
        "sql for", "query to find", "fetch from", "insert into", "update table",
        "delete from", "stored procedure", "optimize query", "explain query",
        "mysql", "postgresql", "sqlite"
    ]),
    (WorkloadType.JSON_GENERATION, [
        "json output", "return json", "generate json", "json format", "json schema",
        "structured output", "extract as json", "parse into json", "output json",
        "json object", "json array", "as json"
    ]),
    (WorkloadType.TRANSLATION, [
        "translate", "translation", "in french", "in spanish", "in german", "in japanese",
        "in chinese", "in arabic", "in hindi", "to english", "from english",
        "multilingual", "language", "convert to"
    ]),
    (WorkloadType.SUMMARIZATION, [
        "summarize", "summary", "tldr", "in brief", "key points", "main points",
        "condense", "shorten", "abstract", "overview of", "brief description"
    ]),
    (WorkloadType.EXTRACTION, [
        "extract", "pull out", "identify", "find all", "list all", "parse",
        "extract from", "get the", "retrieve", "invoice", "receipt", "document",
        "named entity", "ner", "ocr"
    ]),
    (WorkloadType.SENTIMENT, [
        "sentiment", "positive or negative", "tone of", "opinion", "feel about",
        "customer feedback", "review analysis", "is this positive", "is this negative"
    ]),
    (WorkloadType.CLASSIFICATION, [
        "classify", "categorize", "what category", "which type", "label this",
        "is this a", "determine if", "identify the type", "bucket"
    ]),
    (WorkloadType.CREATIVE_WRITING, [
        "write a story", "write a short story", "short story", "creative writing", "poem", "blog post", "write an essay",
        "fiction", "narrative", "write about", "imagine", "brainstorm",
        "generate ideas", "marketing copy", "advertisement", "slogan", "write a poem",
        "write a blog", "creative", "story about"
    ]),
    (WorkloadType.RESEARCH, [
        "research", "explain in detail", "deep dive", "comprehensive analysis",
        "compare and contrast", "pros and cons", "advantages and disadvantages",
        "literature review", "overview of", "what is", "how does", "explain",
        "analyze", "analyse", "in-depth", "architecture of", "how it works",
        "distributed", "microservices", "system design analysis"
    ]),
    (WorkloadType.PLANNING, [
        "create a plan", "roadmap", "strategy", "steps to", "how to build",
        "project plan", "sprint", "timeline", "milestone", "architecture plan",
        "design document", "system design"
    ]),
    (WorkloadType.RAG, [
        "based on the document", "from the context", "according to", "given this text",
        "using the provided", "based on the following", "from the passage",
        "retrieval", "knowledge base", "vector search"
    ]),
    (WorkloadType.AGENT_WORKFLOW, [
        "agent", "multi-step", "chain of thought", "tool use", "function calling",
        "orchestrate", "workflow", "pipeline", "autonomous", "agentic"
    ]),
    (WorkloadType.QUESTION_ANSWER, [
        "what is", "who is", "when did", "where is", "why did", "how many",
        "tell me about", "explain", "what are"
    ]),
    (WorkloadType.CHAT, [
        "hello", "how are you", "thanks", "thank you", "good morning",
        "what do you think", "can you help me", "hey there", "hi there",
        "nice to meet", "who are you"
    ]),
]


# ─────────────────────────────────────────────
# Parameter Tuning Map
# workload_type → (temperature, max_tokens, reasoning_level)
# ─────────────────────────────────────────────

_PARAM_MAP: dict[str, dict] = {
    WorkloadType.CODING:           {"temperature": 0.10, "max_tokens": 2048, "reasoning": ReasoningLevel.MODERATE},
    WorkloadType.CODE_REVIEW:      {"temperature": 0.15, "max_tokens": 1500, "reasoning": ReasoningLevel.MODERATE},
    WorkloadType.DEBUGGING:        {"temperature": 0.05, "max_tokens": 1500, "reasoning": ReasoningLevel.MODERATE},
    WorkloadType.SQL:              {"temperature": 0.05, "max_tokens": 512,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.JSON_GENERATION:  {"temperature": 0.00, "max_tokens": 800,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.EXTRACTION:       {"temperature": 0.05, "max_tokens": 600,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.TRANSLATION:      {"temperature": 0.20, "max_tokens": 1024, "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.SUMMARIZATION:    {"temperature": 0.30, "max_tokens": 400,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.CLASSIFICATION:   {"temperature": 0.10, "max_tokens": 200,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.SENTIMENT:        {"temperature": 0.10, "max_tokens": 150,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.QUESTION_ANSWER:  {"temperature": 0.40, "max_tokens": 800,  "reasoning": ReasoningLevel.MODERATE},
    WorkloadType.RESEARCH:         {"temperature": 0.50, "max_tokens": 2048, "reasoning": ReasoningLevel.DEEP},
    WorkloadType.PLANNING:         {"temperature": 0.50, "max_tokens": 2048, "reasoning": ReasoningLevel.DEEP},
    WorkloadType.CREATIVE_WRITING: {"temperature": 1.10, "max_tokens": 2048, "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.RAG:              {"temperature": 0.30, "max_tokens": 1024, "reasoning": ReasoningLevel.MODERATE},
    WorkloadType.AGENT_WORKFLOW:   {"temperature": 0.20, "max_tokens": 2048, "reasoning": ReasoningLevel.DEEP},
    WorkloadType.CHAT:             {"temperature": 0.80, "max_tokens": 256,  "reasoning": ReasoningLevel.MINIMAL},
    WorkloadType.ADVISORY:         {"temperature": 0.40, "max_tokens": 1500, "reasoning": ReasoningLevel.DEEP},
    WorkloadType.UNKNOWN:          {"temperature": 0.70, "max_tokens": 1024, "reasoning": ReasoningLevel.MODERATE},
}


# ─────────────────────────────────────────────
# Safety Keywords
# ─────────────────────────────────────────────

_SAFETY_HIGH_KEYWORDS = [
    "hack", "exploit", "malware", "ransomware", "phishing", "bypass security",
    "crack password", "sql injection", "xss attack", "ddos", "illegal"
]

_SAFETY_MODERATE_KEYWORDS = [
    "violence", "weapon", "drug", "sensitive", "confidential", "private data",
    "personal information", "credit card", "password", "secret"
]


# ─────────────────────────────────────────────
# Classifier
# ─────────────────────────────────────────────

class PromptClassifier:
    """
    Rule-based prompt intelligence engine.
    Classifies workload type, complexity, and derives optimal parameters.
    Zero LLM calls — purely deterministic.
    """

    def classify(self, prompt: str) -> PromptClassification:
        text = prompt.strip().lower()
        word_count = len(text.split())
        estimated_tokens = int(len(text) / 4)

        # ── Workload Detection ──
        workload, confidence, reason = self._detect_workload(text)

        # ── Complexity ──
        complexity = self._detect_complexity(text, word_count)

        # ── Safety ──
        safety_risk = self._detect_safety(text)

        # ── Large context check ──
        requires_large_context = estimated_tokens > 1500 or word_count > 500

        # ── Parameter tuning ──
        params = _PARAM_MAP.get(workload, _PARAM_MAP[WorkloadType.UNKNOWN])

        # Boost max_tokens for complex requests
        max_tokens = params["max_tokens"]
        if complexity == ComplexityLevel.HIGH:
            max_tokens = min(max_tokens * 2, 4096)
        elif requires_large_context:
            max_tokens = min(max_tokens + 512, 4096)

        return PromptClassification(
            workload_type=workload,
            complexity=complexity,
            reasoning_level=params["reasoning"],
            safety_risk=safety_risk,
            estimated_input_tokens=estimated_tokens,
            recommended_max_tokens=max_tokens,
            recommended_temperature=params["temperature"],
            requires_large_context=requires_large_context,
            is_advisory_query=(workload == WorkloadType.ADVISORY),
            confidence=confidence,
            classification_reason=reason,
        )

    def _detect_workload(self, text: str) -> tuple[str, int, str]:
        for workload, keywords in _WORKLOAD_PATTERNS:
            matched = [kw for kw in keywords if kw in text]
            if matched:
                confidence = min(60 + len(matched) * 10, 95)
                reason = f"Matched keywords: {', '.join(matched[:3])}"
                return workload, confidence, reason
        return WorkloadType.UNKNOWN, 50, "No strong keyword signals detected"

    def _detect_complexity(self, text: str, word_count: int) -> str:
        if word_count > 300:
            return ComplexityLevel.HIGH
        high_complexity_signals = [
            "enterprise", "distributed", "scalable", "architecture", "complex",
            "multi-step", "comprehensive", "in-depth", "detailed analysis",
            "production-grade", "optimize", "performance"
        ]
        score = sum(1 for kw in high_complexity_signals if kw in text)
        if score >= 2 or word_count > 150:
            return ComplexityLevel.HIGH
        if score == 1 or word_count > 50:
            return ComplexityLevel.MEDIUM
        return ComplexityLevel.LOW

    def _detect_safety(self, text: str) -> str:
        if any(kw in text for kw in _SAFETY_HIGH_KEYWORDS):
            return SafetyRisk.HIGH
        if any(kw in text for kw in _SAFETY_MODERATE_KEYWORDS):
            return SafetyRisk.MODERATE
        return SafetyRisk.SAFE


# Global singleton
prompt_classifier = PromptClassifier()
