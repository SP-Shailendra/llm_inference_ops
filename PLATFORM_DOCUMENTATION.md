# Compunnel AIOps Control — Platform Documentation

> **Compunnel AIOps Control** is a unified, enterprise-grade control plane for managing, routing, benchmarking, and governing Large Language Model (LLM) inference workloads. It provides full observability, cost governance, and multi-provider model experimentation through a single web interface.

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Architecture & Core Concepts](#2-architecture--core-concepts)
3. [Glossary — Full Forms & Definitions](#3-glossary--full-forms--definitions)
4. [Page 1 — Overview](#4-page-1--overview)
5. [Page 2 — Catalog](#5-page-2--catalog)
6. [Page 3 — Policies](#6-page-3--policies)
7. [Page 4 — Benchmarks](#7-page-4--benchmarks)
8. [How the Platform Selects the Best Model](#8-how-the-platform-selects-the-best-model)
9. [Role-Based Access Control (RBAC)](#9-role-based-access-control-rbac)
10. [API Endpoints Reference](#10-api-endpoints-reference)
11. [Backend Engines & Their Roles](#11-backend-engines--their-roles)
12. [Prompt Intelligence Engine](#12-prompt-intelligence-engine)
13. [AI Solution Advisor](#13-ai-solution-advisor)
14. [Configuration & Environment Variables](#14-configuration--environment-variables)

---

## 1. Platform Overview

### What is Compunnel AIOps Control?

Compunnel AIOps Control is a **LLM Inference Operations Platform** — a system that sits between your application and multiple AI provider APIs (Groq, Gemini, OpenAI, etc.). Instead of connecting directly to one provider, all requests flow through this control plane, which:

- **Routes** each request to the optimal model based on complexity and cost
- **Caches** repeated or semantically similar prompts to save cost and reduce latency
- **Enforces** governance policies — budget caps, temperature limits, safety guardrails
- **Tracks** every dollar spent across departments (chargeback)
- **Benchmarks** model performance with reproducible test suites
- **Experiments** by running side-by-side comparisons of up to 6 models simultaneously
- **Advises** with real-time optimization insights based on observed traffic patterns

### Why Does This Platform Exist?

In enterprise AI deployment, teams face several recurring challenges:

| Challenge | How This Platform Solves It |
|---|---|
| Unpredictable inference costs | Budget engine with daily/monthly hard limits |
| No visibility into model performance | Live telemetry, TTFT/TPOT/cost per request |
| Too many providers to manage | Unified gateway — one API, multiple providers |
| Risk of deploying bad model updates | Canary deployments with auto-rollback |
| No way to compare models objectively | Multi-model comparison with scoring analysis |
| Governance & compliance gaps | Policy profiles with audit trail |
| Redundant compute spend | Semantic cache engine (in-memory/Redis-ready) |

---

## 2. Architecture & Core Concepts

### Request Lifecycle

Every inference request travels through a 10-stage pipeline:

```
Incoming Request
     │
     ▼
1. 🛡️  Governance      — Apply optimization profile (balanced / performance / cost_saver)
                          Department chargeback tracking, agent session initialization
     │
     ▼
2. 🧠  Prompt Intel     — Classify workload type, complexity, safety risk (no LLM call)
                          19+ workload types: chat, coding, research, SQL, RAG, agent_workflow …
     │
     ▼
3. ⚙️  Parameters       — Auto-tune temperature & max_tokens based on workload classification
                          Profile acts as governance ceiling; classifier fills optimal values within range
     │
     ▼
4. ⚖️  Policy           — Enforce temperature, cost-per-request, token limits
     │
     ▼
5. 💰  Budget           — Check daily/monthly spend vs. limits; validate agent session budget
     │
     ▼
6. 🔀  Routing          — Select model (auto / tier / profile / canary)
                          Routing reason derived from workload type + complexity
     │
     ▼
7. ⚡  Cache            — Hash-check for semantically identical prior response
     │
     ▼
8. ✉️  Inference        — Send request to LLM provider
                          Groq / Gemini / OpenAI / xAI / Mistral / DeepSeek / OpenRouter / NVIDIA NIM / Alibaba / Local
     │
     ▼
9. 📊  Telemetry        — Record TTFT, TPOT, cost, cache status, canary flag, RAG breakdown
                          Agent call tracking, department chargeback attribution
     │
     ▼
10. 🎯  Advisor         — Evaluate aggregate metrics and generate optimization insights
```

Every stage is visible in the **Execution Pipeline Trace** shown on the Policies page after running a request.

### Supported Providers

| Provider | Status | Models | Notes |
|---|---|---|---|
| **Groq** | ✅ Primary | llama-3.1-8b-instant, llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b | Fastest inference via custom LPU hardware |
| **Gemini** (Google) | ✅ Supported | gemini-2.5-flash, gemini-1.5-flash | Native Gemini adapter with model fallback |
| **OpenAI** | ✅ Supported | gpt-5, gpt-5-mini, gpt-5-nano, o3, o4-mini | Requires `OPENAI_API_KEY` |
| **xAI** | ✅ Supported | grok-4, grok-3 | Requires `XAI_API_KEY`; base URL `https://api.x.ai/v1` |
| **Mistral** | ✅ Supported | mistral-large, codestral, mixtral-8x7b-instruct | Requires `MISTRAL_API_KEY` |
| **DeepSeek** | ✅ Supported | deepseek-v3, deepseek-r1, deepseek-coder | Requires `DEEPSEEK_API_KEY` |
| **OpenRouter** | ✅ Supported | openrouter/auto, anthropic/claude-sonnet-4, openai/gpt-5-mini | Unified gateway to 100+ models |
| **NVIDIA NIM** | ✅ Supported | meta/llama-3.1-70b-instruct, mistralai/mixtral-8x7b-instruct-v0.1 | Requires `NVIDIA_NIM_API_KEY` + `NVIDIA_NIM_BASE_URL` |
| **Alibaba** (Qwen) | ✅ Supported | qwen-plus, qwen-max, qwen-turbo | Requires `ALIBABA_API_KEY`; DashScope endpoint |
| **Anthropic** | ⚠️ Placeholder | claude-opus-4-1, claude-sonnet-4, claude-3-5-haiku | Listed in registry; native adapter not yet implemented |
| **Ollama** (Local) | ✅ Local | Any locally pulled model | Default: `http://localhost:11434/v1` |
| **vLLM** (Local) | ✅ Local | Any model served by vLLM | Requires `VLLM_BASE_URL` |
| **TGI** (Local) | ✅ Local | Any model served by Hugging Face TGI | Requires `TGI_BASE_URL` |
| **llama.cpp** (Local) | ✅ Local | GGUF models | Requires `LLAMACPP_BASE_URL` |

> **Local provider activation rule:** A local provider (Ollama / vLLM / TGI / llama.cpp) is only considered **enabled** if its `{base_url}/models` endpoint is reachable at startup. Configuration alone is not sufficient.

---

## 3. Glossary — Full Forms & Definitions

This section explains every abbreviated term used across the platform, how each is measured, and how it influences model selection.

---

### Performance Metrics

#### TTFT — Time To First Token
- **Full Form:** Time To First Token
- **Unit:** Milliseconds (ms)
- **What it measures:** The time elapsed from sending the request until the model streams back its very first output token.
- **Why it matters:** TTFT is the primary indicator of perceived responsiveness. In chat applications, a high TTFT makes the interface feel "frozen". A TTFT under 500ms feels instant; above 3000ms feels sluggish.
- **How it helps select the best model:** The model with the **lowest TTFT** wins the "Fastest" category in comparison analysis. TTFT carries **+2 points** in the overall scoring system — the highest weight.

#### TPOT — Time Per Output Token
- **Full Form:** Time Per Output Token
- **Unit:** Milliseconds per token (ms/token)
- **What it measures:** The average time the model takes to generate each subsequent token after the first one has been delivered.
- **Why it matters:** TPOT governs the streaming throughput. A low TPOT means the full response completes quickly. For long outputs (e.g., code generation, reports), TPOT is more important than TTFT.
- **How it helps select the best model:** Lower TPOT = faster total generation speed. Shown in the Detailed Metrics Comparison table.

#### Total Latency
- **Full Form:** Total End-to-End Latency
- **Unit:** Milliseconds (ms)
- **What it measures:** Total wall-clock time from sending the request to receiving the complete response. Approximately: `TTFT + (TPOT × output_tokens)`.
- **Why it matters:** This is what the user actually waits for. For short prompts, Total Latency ≈ TTFT. For long generations, it diverges significantly.
- **How it helps select the best model:** The model with the **lowest total latency** wins the "Lowest Total Latency" category. Carries **+1 point** in scoring.

---

### Cost Metrics

#### Cost (USD) / Total Cost
- **Full Form:** Total Inference Cost in US Dollars
- **Unit:** USD (shown as $0.000000 for micro-cost precision)
- **What it measures:** Actual money charged for one inference call = `(input_tokens / 1000 × input_price) + (output_tokens / 1000 × output_price)`.
- **Why it matters:** At scale, even fractions of a cent per request become significant. A system running 1 million requests/day at $0.0001/request costs $100/day or $36,500/year.
- **How it helps select the best model:** The model with the **lowest cost** wins "Most Economical". Cost carries **+2 points** in scoring — equal to TTFT.

#### Input Tokens
- **Full Form:** Input Token Count
- **Unit:** Integer count
- **What it measures:** The number of tokens (roughly 0.75 words per token in English) in the prompt sent to the model.
- **Why it matters:** Input tokens directly impact cost. Longer prompts = higher spend. Prompt compression (a feature flag) can reduce this count.

#### Output Tokens
- **Full Form:** Output Token Count
- **Unit:** Integer count
- **What it measures:** The number of tokens generated by the model in its response.
- **Why it matters:** Output tokens are typically billed at 2–4× the input token rate. Controlling `max_tokens` limits runaway output costs.

---

### Quality Metrics

#### Accuracy / Accuracy Retention
- **Full Form:** Accuracy Retention Rate (post-quantization)
- **Unit:** Percentage (0–100%)
- **What it measures:** How much of the full-precision model's accuracy is retained after quantization. A FP16 model has 100% retention. An INT4 model might have 94%.
- **Why it matters:** Accuracy degradation from quantization is often invisible for casual chat but can matter for reasoning-heavy tasks, code generation, or factual Q&A.
- **How it helps select the best model:** The model with the **highest accuracy retention** wins "Highest Accuracy". Carries **+2 points** in scoring.

#### Outlier Risk / Outlier Sensitivity
- **Full Form:** Outlier Sensitivity Risk
- **Values:** `SAFE` or `HIGH`
- **What it measures:** Whether this model variant is known to produce significantly degraded outputs on edge-case or unusual prompts — a behavior especially common in aggressively quantized models (INT4).
- **Why it matters:** A `HIGH` risk model might perform well on average but catastrophically fail on 1–2% of production requests. This is unacceptable for customer-facing applications.
- **How it helps select the best model:** Models rated `SAFE` earn **+1 point** in scoring. The comparison report explicitly labels outlier risk in the metrics table.

---

### Hardware & Efficiency Metrics

#### VRAM — Video Random Access Memory
- **Full Form:** Video Random Access Memory
- **Unit:** Gigabytes (GB)
- **What it measures:** The GPU memory required to load and serve this model. FP16 models require maximum VRAM; INT4/AWQ models require far less.
- **Why it matters:** VRAM is the primary hardware constraint for self-hosted deployments. A 70B FP16 model needs ~140GB VRAM (multiple A100 GPUs), while a 70B AWQ INT4 model needs ~40GB (single A100).
- **How it helps select the best model:** The model with the **lowest VRAM requirement** wins "Lowest VRAM". Carries **+1 point** in scoring.

#### Quantization Precision Levels
- **FP16 (Full Precision 16-bit Float):** Maximum accuracy, highest VRAM, highest cost.
- **INT8 (8-bit Integer):** ~47% memory reduction, ~1% accuracy loss, good for production.
- **INT4 (4-bit Integer):** ~70% memory reduction, ~6% accuracy loss, outlier-sensitive, cheapest.
- **AWQ-INT4 (Activation-aware Weight Quantization INT4):** Intel-optimized INT4 — better accuracy than plain INT4 at similar memory savings. Best of both worlds.
- **GGUF (GPT-Generated Unified Format):** Portable quantized format for CPU inference via llama.cpp.

#### Memory Reduction %
- **Full Form:** Percentage of memory saved vs. FP16 baseline
- **What it measures:** `(FP16_VRAM - quantized_VRAM) / FP16_VRAM × 100`
- **Why it matters:** Directly translates to cost savings in cloud GPU infrastructure and allows more concurrent model instances on the same hardware.

---

### Cache & Deduplication

#### Cache Hit Rate
- **Full Form:** Semantic Cache Hit Rate
- **Unit:** Percentage (0–100%)
- **What it measures:** The proportion of requests served from cache (no LLM call made) vs. those that required a live inference.
- **Why it matters:** Every cache hit = zero LLM cost + near-zero latency (typically <1ms vs 500–15000ms for live inference). A 50% cache hit rate effectively halves your inference bill.
- **How it helps select the best model:** The Advisor engine flags low cache rates (<20%) and recommends reducing similarity thresholds. High cache rate (>80%) is highlighted as excellent utilization.

#### Cache Hit (per request)
- **Values:** `YES` or `NO`
- **What it measures:** Whether this specific request was served from the cache.
- **Why it matters:** In the telemetry table, cache hits are visually tagged so you can see which prompts benefit from caching.

---

### Scoring & Selection Metrics

#### Fit Score
- **Full Form:** Workload Fit Score
- **Unit:** 0–100 score
- **What it measures:** How well a model variant matches the selected use-case preset (Chat Assistant, Deep Reasoning, Fast Extraction, Balanced). Calculated from accuracy retention, VRAM suitability, and recommended_for tags.
- **Why it matters:** In the Catalog page, Fit Score is the default sort order — highest fit appears first, guiding users toward the right model for their use case without needing deep technical knowledge.

#### Overall Score (in Comparison)
- **Full Form:** Weighted Multi-Dimensional Performance Score
- **Unit:** Points out of 11
- **What it measures:** A composite score calculated during model comparison:
  - TTFT (lowest) → **+2 points**
  - Cost (lowest) → **+2 points**
  - Accuracy (highest) → **+2 points**
  - Total Latency (lowest) → **+1 point**
  - VRAM (lowest) → **+1 point**
  - Outlier Risk = SAFE → **+1 point**
- **Why it matters:** The model with the highest overall score wins the "Overall Winner" category and drives the recommendation text.

---

### Governance & Operations

#### RBAC — Role-Based Access Control
- **Full Form:** Role-Based Access Control
- **What it measures:** The access tier of the current user, which determines which platform features are visible or editable.
- **Roles available:** Viewer → User → Developer → MLOps → Admin

#### FinOps — Financial Operations
- **Full Form:** Financial Operations (for AI/Cloud)
- **What it covers:** The practice of managing and optimizing cloud/AI spending — chargeback by department, budget enforcement, cost-per-request tracking, and efficiency recommendations.

#### RAG — Retrieval-Augmented Generation
- **Full Form:** Retrieval-Augmented Generation
- **What it is:** A technique where relevant documents are fetched from a database and injected into the prompt before sending to the LLM, improving factual accuracy without fine-tuning.
- **Platform tracking:** RAG Cost is tracked separately in the KPI bar, showing the overhead added by document retrieval operations.

#### QPS — Queries Per Second
- **Full Form:** Queries Per Second
- **What it measures:** Inference throughput — how many requests the model can handle per second. Higher QPS is important for high-traffic production deployments.

#### KV Cache
- **Full Form:** Key-Value Cache (attention cache inside the transformer)
- **What it is:** An internal optimization inside the model that stores previously computed attention values, preventing redundant computation during autoregressive generation. Not to be confused with the platform's semantic cache.

---

### Prompt Intelligence Terms

#### Workload Type
- **Full Form:** Prompt Workload Classification Type
- **What it is:** A label automatically assigned to each incoming prompt by the Prompt Intelligence Engine. It describes the primary task the prompt is requesting, without making an LLM call.
- **Available Types (19+):** `chat`, `coding`, `code_review`, `debugging`, `sql`, `json_generation`, `translation`, `summarization`, `extraction`, `sentiment_analysis`, `classification`, `creative_writing`, `research`, `planning`, `rag`, `function_calling`, `agent_workflow`, `question_answer`, `advisory`, `unknown`
- **Why it matters:** Workload type drives model routing, parameter auto-tuning, and the Advisor's recommendations.

#### Complexity Level
- **Full Form:** Prompt Complexity Assessment
- **Values:** `low`, `medium`, `high`
- **What it measures:** How demanding the prompt is in terms of reasoning requirements, output size, and precision needed.
- **Why it matters:** High complexity requests are automatically escalated to premium (70B) models; low complexity requests are served by efficient 8B models.

#### Classification Confidence
- **Full Form:** Workload Classification Confidence Score
- **Unit:** Percentage (0–100%)
- **What it measures:** How certain the Prompt Intelligence Engine is about its workload type classification. High confidence (>85%) means the routing and parameters are well-calibrated.

#### Safety Risk
- **Full Form:** Prompt Safety Risk Level
- **Values:** `safe`, `moderate`, `high`
- **What it measures:** Whether the prompt contains potentially harmful, sensitive, or policy-violating content patterns.
- **Why it matters:** High safety risk prompts are flagged in the execution trace with a `🚨 Safety` warning, and the Advisor may surface warnings about content filtering.

#### RAG Cost Breakdown
- **Full Form:** Retrieval-Augmented Generation Cost Breakdown
- **What it tracks:** Splits the total inference cost into two components:
  - `retrieval_cost_usd` — cost of fetching document chunks from the vector store
  - `llm_cost_usd` — cost of the LLM call itself
- **Why it matters:** Helps teams identify whether high costs are driven by expensive LLM calls or by over-fetching too many retrieval chunks.

---

## 4. Page 1 — Overview

> **Significance:** The Overview page is your real-time operations dashboard. It gives an at-a-glance view of system health, financial spend, model performance, and AI advisor recommendations. This is the first page operators and executives visit to understand whether the platform is running optimally.

---

### 4.1 KPI Bar (Key Performance Indicators)

The top row displays 10 live metrics — all updating after every request.

| KPI Card | Full Form | Significance |
|---|---|---|
| **Total Requests** | Total Inference Requests Processed | Shows platform utilization volume. Rising quickly = high traffic, may trigger budget alerts. |
| **Total Spend** | Total Cumulative Inference Cost (USD) | Direct measure of financial burn rate. Compared against daily budget limits. |
| **Avg TTFT** | Average Time To First Token (ms) | System-wide responsiveness indicator. Rising avg TTFT = potential provider degradation or model overload. |
| **Cache Hit Rate** | Semantic Cache Hit Rate (%) | Cost efficiency indicator. Higher = better. Target: >30% for most workloads. |
| **Agent Calls** | Total Agentic Loop LLM Calls | Tracks how many sub-calls the AI agent made (multi-step reasoning). Avg per request shown below. |
| **Agent Cost** | Total Cost Attributed to Agentic Calls (USD) | Shows what percentage of total spend is being consumed by agent workloads. |
| **Budget Limits** | Requests Terminated by Budget Enforcement | Count of requests rejected because daily budget ceiling was reached. Non-zero = investigate and adjust daily limits. |
| **RAG Cost** | Retrieval-Augmented Generation Cost (USD) | Overhead from document retrieval (`retrieval_chunks_count × $0.001 + $0.002/search`). Avg % of total spend shown below. |
| **Canary Req** | Canary Deployment Requests | Count of requests routed to the experimental model. Rate shown as % of total traffic. |
| **Canary Rollback** | Automatic Canary Rollbacks Triggered | Count of times auto-rollback fired due to TTFT or cost threshold breach. |

---

### 4.2 Deployment Health

**What it shows:** A grid of infrastructure node cards, one per active provider/deployment slot. Each card displays:
- Provider name and model
- Active connection count (animate-pulse dot = live traffic)
- Node status (Online / Degraded / Offline)

**Significance:** This panel allows MLOps engineers to detect provider-level degradation in real time. If a node goes red, the routing engine should automatically fall back to an alternative provider. The panel is collapsible to save screen space.

**Parameters:**
- **Active Connections:** Live concurrent requests being processed
- **Node Status:** Health state of the deployment endpoint
- **Provider Region:** Deployment geography (e.g., groq-us-east-1)

---

### 4.3 Chargeback by Department

**What it shows:** A breakdown of inference costs attributed to different business units or teams using the platform, based on the `department_id` field sent with each request.

**Significance:** Enterprise organizations need to allocate AI costs to the right cost center for budgeting and P&L reporting. This panel provides the raw data needed for internal chargebacks without requiring a separate billing system.

**How to enable:** Include `"department_id": "engineering"` (or any team name) in every `/gateway/generate` request. Requests without a `department_id` are grouped under `"unassigned"`.

**Parameters:**
- **Department Name:** Business unit identifier (from `department_id` request field)
- **Total Requests:** Volume from that department
- **Total Cost:** Spend attributed to that department
- **% of Total Spend:** Their share of platform costs

**Multi-tenant support:** An optional `tenant_id` field is also available for SaaS platforms that need workspace-level isolation.

---

### 4.4 Telemetry Table

**What it shows:** A rolling log of the last 100 inference requests processed by the platform.

**Significance:** The Telemetry table is the primary observability tool. Engineers can see which model handled each request, how fast it responded, what it cost, and whether the cache saved a live call. This data feeds the Advisor and budget enforcement systems.

**Columns Explained:**

| Column | Full Form | What to Watch For |
|---|---|---|
| **Model Routed** | The model that processed this request | Unexpected model routing = check profile configuration |
| **TTFT (ms)** | Time To First Token (milliseconds) | Spikes above 5000ms indicate provider latency issues |
| **TPOT (ms)** | Time Per Output Token (milliseconds) | High TPOT with short TTFT = slow generation throughput |
| **Cost (USD)** | Total Cost for this Request | Expensive single requests = over-budget prompts or wrong model |
| **Cache** | Cache Hit Status (HIT/MISS) | Too many MISS entries = low cache utilization, tuning needed |

**Row Highlight:** The most recent row pulses with a glow animation to help operators immediately spot new traffic.

---

### 4.5 Optimization Insights (Advisor Panel)

**What it shows:** Automatically generated, data-driven recommendations based on observed traffic patterns in the Telemetry table.

**Significance:** The Advisor eliminates the need for manual log analysis. It continuously watches cost, latency, and cache patterns and surfaces actionable recommendations. It assigns a platform-wide **Grade** (A, A-, B+) to summarize overall system health.

**Insight Types Generated:**

| Insight Type | Trigger Condition | Recommendation |
|---|---|---|
| **Cost Reduction (Quantization)** | 70B or FP16 models dominating traffic | Switch to INT4 quantization, shows estimated savings |
| **Latency & Cost Optimization** | Cache hit rate < 20% | Lower similarity threshold to increase cache hits |
| **Excellent Cache Utilization** | Cache hit rate > 80% | Confirms efficient caching, no action needed |
| **Compute Downgrade** | High total spend (>$0.0005) | Route simple tasks to 8B instead of 70B |
| **System Profiling Active** | < 5 requests processed | Baseline still accumulating, run more traffic |
| **System Optimal** | All metrics within bounds | Platform is fully optimized |

---

### 4.6 Model Comparison Panel (Experimentation Lab)

**What it shows:** An interactive interface for running live, side-by-side comparisons of 2–6 LLM models simultaneously against the same prompt.

**Significance:** This is the most powerful feature of the Overview page. Instead of manually switching between providers and taking notes, teams can compare an entire roster of models in one click. The output includes a full analysis report with scoring, category winners, and a recommendation.

**Input Parameters:**

| Parameter | Description | Significance |
|---|---|---|
| **Prompt** | The test input sent to all models | Should represent a real use-case scenario, not a trivial question |
| **Number of Models** | How many comparison slots to open (2–6) | More models = broader comparison, longer wait time |
| **Provider (per slot)** | Cloud provider for this slot (Groq / Gemini / OpenRouter) | Selecting different providers tests cross-provider performance |
| **Variant / Model** | Which model variant to run in this slot | Automatically filtered to only show models available for the selected provider |

**Output — Detailed Metrics Comparison Table:**
All 10 metrics per model displayed side-by-side. The winner in each metric column is highlighted in green.

**Output — Category Winners:**

| Category | Winner Criterion |
|---|---|
| ⚡ Fastest (TTFT) | Lowest time to first token |
| 💰 Most Economical | Lowest total cost |
| ✓ Highest Accuracy | Highest accuracy retention |
| ⏱️ Lowest Total Latency | Lowest end-to-end response time |
| 💾 Lowest VRAM | Least GPU memory required |
| 🎯 Overall Winner | Highest composite score (out of 11 points) |

**Output — Overall Recommendation:**
A paragraph recommendation is generated explaining why the winner was selected, with specific percentage deltas (e.g., "21.8% lower latency", "40% cost savings") vs. the other models.

**Output — Delta Summary Bar:**
A dark bar at the bottom showing the numerical difference (Δ) in TTFT, Cost, and Accuracy between the top two models — for quick, at-a-glance comparison.

---

## 5. Page 2 — Catalog

> **Significance:** The Catalog page is the model intelligence library. It displays every registered model variant with detailed hardware specifications, quantization trade-offs, and suitability scores. Teams use this page to research and choose the right model before deploying it in a policy or running a comparison test.

---

### 5.1 Catalog Overview

The catalog is fetched live from the Model Registry (`/api/v1/registry/variants`). Each card represents a **quantized model variant** — a specific version of a base model with a defined precision format.

**Why Variants Instead of Just Models?**

A single base model (e.g., Llama 3.1 8B) can be deployed in multiple precision formats. Each variant has different performance, memory, and cost characteristics:

| Variant | Precision | VRAM | Accuracy | Cost Factor |
|---|---|---|---|---|
| llama3-8b-fp16 | FP16 | 16.0 GB | 100% | 1.0× |
| llama3-8b-int8 | INT8 | 8.5 GB | 99% | 0.8× |
| llama3-8b-int4 | INT4 | 4.8 GB | 94% | 0.5× |
| llama3-70b-fp16 | FP16 | 140.0 GB | 100% | 1.0× |
| llama3-70b-awq | AWQ-INT4 | ~40 GB | 97% | 0.6× |

---

### 5.2 Filters & Controls

| Control | Options | Purpose |
|---|---|---|
| **Search** | Free text | Find models by name or base model family |
| **Provider Filter** | All / Groq / Gemini / OpenAI / etc. | Narrow to models available from a specific provider |
| **Preset Selector** | Chat Assistant / Deep Reasoning / Fast Extraction / Balanced | Pre-configured use-case filter — automatically surfaces the most suitable models |
| **Sort** | Fit Score ↓ / Accuracy ↓ / VRAM ↑ / Cost Factor ↑ | Reorder cards based on the most relevant optimization axis |

---

### 5.3 Model Variant Card Parameters

Each card in the catalog shows the following fields:

| Parameter | Full Form | Significance |
|---|---|---|
| **Display Name** | Human-readable model identifier | e.g., "Llama 3.3 70B AWQ INT4" |
| **Provider** | Cloud provider hosting this variant | Determines which API key is needed |
| **Fit Score** | Workload Fit Score (0–100) | How well this variant matches the current preset |
| **Quantization Precision** | Floating-point or integer precision format | FP16 = full quality; INT4 = max efficiency |
| **Memory Reduction %** | % VRAM saved vs. FP16 baseline | Directly maps to infrastructure cost savings |
| **Expected Accuracy** | Post-quantization accuracy retention | 100% = no degradation; 94% = some capability loss |
| **VRAM Required (GB)** | GPU memory footprint for serving | Determines which GPU tier is required |
| **Context Window** | Max input tokens the model can process | 8192 = short context; 32768+ = long documents |
| **Max Output Tokens** | Maximum tokens in a single response | Limits response length for cost containment |
| **Input Cost per 1K tokens** | Price for processing 1000 input tokens | Base component of per-request cost calculation |
| **Output Cost per 1K tokens** | Price for generating 1000 output tokens | Higher than input cost (generation is more expensive) |
| **Cost Multiplier** | Cost factor relative to baseline (1.0 = standard) | 0.5× = half the cost; useful for quick cost comparison |
| **Outlier Sensitive** | Whether this variant is prone to edge-case failures | TRUE = HIGH risk; FALSE = SAFE |
| **Recommended For** | Use-case tags | e.g., "cost_optimized", "deep_reasoning", "batch_inference" |
| **Tags** | Categorical labels | e.g., "premium", "quantized", "baseline" |
| **Deployment ID** | Internal infrastructure identifier | Tracks which specific deployment is serving the variant |

---

### 5.4 Significance of the Catalog Page

- **Pre-experiment research:** Before running a comparison test, check the catalog to understand each variant's specs
- **Infrastructure planning:** VRAM requirements tell you exactly what GPU hardware you need
- **Cost modeling:** Use input/output pricing to estimate monthly spend before deploying
- **Risk assessment:** Outlier sensitivity and accuracy retention help determine deployment risk
- **Preset guidance:** The preset filter removes guesswork — "Chat Assistant" surfaces low-latency, cost-effective models; "Deep Reasoning" surfaces high-accuracy 70B models

---

## 6. Page 3 — Policies

> **Significance:** The Policies page is the governance control center. It allows MLOps engineers and admins to define, configure, and test the behavioral rules that govern every inference request. Policies determine which model is used, how much it can spend, what safety limits apply, and whether experimental traffic routing (canary) is enabled.

---

### 6.1 Profile & Policies Panel

The platform ships with three built-in **Inference Profiles**, each representing a different operational posture:

| Profile | Purpose | Default Model | Cost Cap/Req | Temperature |
|---|---|---|---|---|
| **Balanced** | General-purpose, default for most workloads | llama-3.1-8b-instant | $0.05 | 0.7 |
| **Performance** | Maximum capability, complex reasoning tasks | llama-3.3-70b-versatile | $0.05 | 0.7 |
| **Cost Saver** | Minimum spend, simple tasks (summarization, extraction) | llama-3.1-8b-instant | $0.05 | 0.7 |

Each profile is fully customizable. Selecting a profile card reveals the **Inline Policy Editor**.

---

### 6.2 Policy Parameters Explained

#### Runtime Limits (`RuntimeLimits`)

| Parameter | Full Form | Default | Significance |
|---|---|---|---|
| **max_tokens** | Maximum Output Tokens per Request | 1024 | Hard cap on response length. Prevents runaway generation that inflates cost. |
| **temperature** | Sampling Temperature | 0.7 | Controls randomness. 0.0 = deterministic; 2.0 = very random. Policy enforces valid range. |
| **top_p** | Top-P (Nucleus) Sampling Threshold | 0.95 | Controls diversity of token selection. Works with temperature to tune output quality. |
| **max_cost_per_request** | Maximum Allowed Cost per Single Request (USD) | $0.05 | Security guardrail — enterprise policy blocks any request exceeding this. Hard limit: $0.50. |
| **timeout_seconds** | Request Timeout | 60s | Prevents hung connections from consuming resources indefinitely. |
| **rollback_ttft_ms** | TTFT Threshold for Auto-Rollback (ms) | 1500ms | If a canary model exceeds this TTFT, it is automatically rolled back. |
| **rollback_cooldown_seconds** | Canary Disable Duration After Rollback | 300s | After rollback fires, the canary is blocked for this many seconds to prevent flapping. |

#### Feature Flags (`FeatureFlags`)

Feature flags are binary on/off toggles that enable or disable specific platform capabilities per profile.

| Flag | Full Form | Default | Effect When Enabled |
|---|---|---|---|
| **enable_cache** | Semantic Cache | ✅ ON | Incoming requests are hash-checked against prior responses. Cache hits skip inference entirely. |
| **enable_prompt_compression** | Prompt Compression | ❌ OFF | Automatically compress verbose prompts before sending to reduce input token count and cost. |
| **enable_agentic_loop** | Agentic Multi-Step Loop | ❌ OFF | Enables the LLM to make multiple sub-calls (tool use, chain of thought) within one session. |
| **enable_streaming** | Token Streaming | ✅ ON | LLM streams tokens back as they are generated rather than waiting for the full response. Reduces perceived TTFT. |
| **enable_auto_routing** | Automatic Model Routing | ✅ ON | System automatically selects the model based on prompt complexity analysis. |
| **enable_speculative_decoding** | Speculative Decoding | ❌ OFF | Experimental feature: uses a smaller draft model to speed up generation on the primary model. |
| **enable_canary** | Canary Deployment | ❌ OFF | Routes a configurable percentage of traffic to an experimental model for live testing. |
| **enable_rollback** | Automatic Canary Rollback | ❌ OFF | Triggers automatic rollback to the baseline model if canary performance degrades. |

#### Routing Policy (`RoutingPolicy`)

| Parameter | Default | Significance |
|---|---|---|
| **primary_model** | llama-3.1-8b-instant | The main model used for inference requests under this profile. |
| **fallback_model** | llama-3.1-8b-instant | Model to use if the primary is unavailable or fails. |
| **auto_route** | true | Whether to let the routing engine override the primary model based on prompt complexity. |
| **canary_model** | null | The experimental model to route canary traffic to. |
| **canary_provider** | null | Provider for the canary model (can differ from primary). |
| **canary_traffic_percent** | 5% | What percentage of requests go to the canary model. Deterministic bucketing by user ID + prompt hash. |

#### Budget Policy (`BudgetPolicy`)

| Parameter | Default | Significance |
|---|---|---|
| **daily_budget_usd** | $50.00 | Hard limit for total daily inference spend. Requests are rejected once this is reached. |
| **monthly_budget_usd** | $1,000.00 | Soft monthly ceiling. Warning notifications trigger at the warning threshold. |
| **warning_threshold_percent** | 80% | When spend reaches 80% of the daily limit, the system can surface warnings. |

#### Agent Controls (`AgentControls`)

Relevant only when `enable_agentic_loop` is ON. These prevent runaway agent cost.

| Parameter | Default | Significance |
|---|---|---|
| **max_calls_per_session** | 20 | Maximum LLM sub-calls an agent can make in one session. Circuit breaker for infinite loops. |
| **max_cost_per_session_usd** | $0.50 | Agent session budget cap. Aborted if exceeded. |
| **max_duration_seconds** | 300s (5 min) | Agent session timeout. Prevents stuck agents from consuming resources. |
| **timeout_behavior** | "stop" | What to do when limits are reached: "stop" (abort) or "degrade" (return partial result). |

#### Traffic Split & Rollback Triggers

| Parameter | Significance |
|---|---|
| **primary_percent** | What % of traffic goes to the primary model (e.g., 95%) |
| **canary_percent** | What % of traffic goes to the canary (e.g., 5%). Must sum to 100 with primary. |
| **ttft_ms_threshold** | Auto-rollback fires if canary TTFT exceeds this value |
| **cost_multiplier_threshold** | Rollback fires if canary cost is >1.3× the primary model's cost |
| **error_rate_threshold** | Rollback fires if canary error rate exceeds 5% |
| **check_window_seconds** | How frequently rollback conditions are evaluated (every 60 seconds) |

---

### 6.3 Routing Gateway

**What it is:** A live test interface for sending a single inference request through the full 8-stage pipeline and observing the complete execution trace.

**Significance:** This is the primary debugging tool for policies. If a policy change isn't behaving as expected, engineers can fire a test request here and see exactly which stage applied which rule.

**Parameters:**

| Parameter | Description |
|---|---|
| **LLM Provider** | Which provider to target for this test request |
| **Model Override** | Optionally force a specific model; otherwise, auto-routing applies |
| **Payload / Prompt** | The test input text |

**Execution Trace Output:**
After running, every pipeline stage appears in chronological order with emoji-coded log messages:

| Emoji | Stage | Example Log |
|---|---|---|
| 🛡️ | Governance | "Policy 'BALANCED' applied." |
| 💰 | Chargeback | "Department 'engineering' will be billed." |
| 🤖 | Agent Session | "Initialized with limits (Calls: 20, Cost: $0.50)" |
| 🧠 | Prompt Intelligence | "Workload='coding' Complexity='high' Confidence=92% — imperative verb 'implement' detected" |
| ⚙️ | Parameters | "temperature=0.10 max_tokens=2048 (tuned for 'coding' workload)" |
| ⚖️ | Policy | "Guardrails passed (Est. Max Cost: $0.0001)." |
| 💰 | Budget | "Approved. Sufficient daily funds available." |
| 🔀 | Routing | "Provider 'Groq' · Model 'llama-3.3-70b-versatile' — 'coding' workload with 'high' complexity → premium tier" |
| 🔍 | Cache | "Cache Miss. Proceeding to inference layer." |
| ⚡ | Cache Hit | "Semantic hit found. Bypassing LLM generation." |
| 🗣️ | Prompt Compression | "Prompt compressed (Estimated -60% tokens)." |
| 🧪 | Canary | "Canary route active (5%): provider 'Gemini' model 'gemini-2.5-flash'." |
| 🧯 | Canary Cooldown | "Canary disabled by rollback cooldown (240s remaining)." |
| ⤴️ | Rollback | "Auto-rollback triggered: TTFT exceeded threshold. Canary disabled for 300s." |
| 📦 | Agent Call | "Agent Call #1: Cost $0.000082 (Total: $0.000082)" |
| 🔍 | RAG Breakdown | "Retrieval $0.002000 + LLM $0.000082" |
| ✅ | Success | "Inference complete. TTFT: 1243ms, Cost: $0.000082" |

---

## 7. Page 4 — Benchmarks

> **Significance:** The Benchmarks page provides reproducible, structured performance testing of any model/provider combination. Unlike the comparison panel (which tests a single custom prompt), benchmarks run standardized test suites with multiple prompts across predefined categories, producing statistically meaningful performance metrics.

---

### 7.1 What Benchmarks Are For

| Use Case | Why Benchmarks Help |
|---|---|
| Provider evaluation | Compare Groq vs. Gemini vs. OpenRouter on identical prompts |
| Model upgrade validation | Ensure a new model version doesn't degrade performance vs. the baseline |
| SLA validation | Verify average TTFT and cost meet service level targets before production rollout |
| Quantization trade-off analysis | Measure actual (not theoretical) accuracy/speed impact of INT8 vs. INT4 |
| Cost forecasting | Run a controlled sample to project monthly spend at scale |

---

### 7.2 Benchmark Configuration Parameters

| Parameter | Options | Significance |
|---|---|---|
| **Provider** | Groq / Gemini / OpenAI / etc. | Which provider to run the benchmark against |
| **Model Name** | Specific model or auto-selected | The model variant to benchmark. If blank, the engine picks the best available model for the provider. |
| **Optimization Profile** | balanced / performance / cost_saver | Determines temperature, max_tokens, and routing behavior during the benchmark run |
| **Test Suites** | smoke / mmlu-lite / hellaswag-lite (multi-select) | Which benchmark suites to include (see below) |
| **Sample Size** | 1–10 prompts per suite | How many prompts from each suite to run. Larger samples = more statistical reliability. |

---

### 7.3 Benchmark Suites Explained

| Suite Name | Full Form | Prompt Type | Measures |
|---|---|---|---|
| **smoke** | Smoke Test Suite | Quick sanity checks on LLM ops concepts | Basic functionality, latency floor |
| **mmlu-lite** | Massive Multitask Language Understanding (Lite) | Knowledge and reasoning questions | Model reasoning capability, accuracy |
| **hellaswag-lite** | HellaSwag Benchmark (Lite) | Sentence completion and logical continuation | Common-sense reasoning, narrative coherence |

**Example Prompts per Suite:**
- **Smoke:** "What is TTFT and why does it matter for chat UX?"
- **MMLU-Lite:** "In one paragraph, explain the trade-off between precision and recall."
- **HellaSwag-Lite:** "Complete the scenario: A canary deployment is useful because..."

---

### 7.4 Benchmark Job Results

After execution, each benchmark job produces:

#### Summary Metrics

| Metric | Full Form | Significance |
|---|---|---|
| **Total Cases** | Total test prompts run | Volume of data points |
| **Passed Cases** | Successfully completed inferences | Success rate indicator |
| **Failed Cases** | Errors or timeouts | Reliability indicator — high failures = provider issues |
| **Avg TTFT (ms)** | Average Time To First Token | Primary speed benchmark across all test cases |
| **Avg TPOT (ms)** | Average Time Per Output Token | Throughput benchmark |
| **Avg Total Latency (ms)** | Average End-to-End Latency | Overall responsiveness |
| **Total Cost (USD)** | Cumulative cost for all benchmark runs | Cost at the tested sample size, scalable to production estimates |

#### Per-Case Results

Each individual prompt result shows:
- Suite name and prompt text
- Pass/Fail status
- TTFT, TPOT, Total Latency for that specific prompt
- Cost for that specific call
- Which provider/model actually served it

---

### 7.5 Benchmark Job History

All benchmark jobs are persisted (in-memory during the session) and displayed in a sortable history table. Jobs show status (`running`, `completed`, `failed`) and can be re-inspected at any time during the session.

---

## 8. How the Platform Selects the Best Model

This section describes the complete model selection logic — from routing to comparison scoring.

---

### 8.1 Routing Engine: Auto-Selection Logic

When a request arrives and `enable_auto_routing` is ON, the routing engine evaluates the prompt in three tiers:

**Tier 1 — Profile Override:**
- `cost_saver` profile → always routes to `llama-3.1-8b-instant` (cheapest)
- `performance` profile → always routes to `llama-3.3-70b-versatile` (most capable)

**Tier 2 — Manual Tier Override:**
If the request specifies a routing tier explicitly:
- `tier_1_premium` → `llama-3.3-70b-versatile`
- `tier_2_balanced` → `llama-3.1-8b-instant`
- `tier_3_low_cost` → `llama-3.1-8b-instant`

**Tier 3 — Prompt Intelligence Routing (Automatic):**
The Prompt Intelligence Engine classifies the workload first. Routing then uses **workload type + complexity** as primary signals (legacy keyword/word-count checks are the fallback within the engine):

| Condition | Model Tier Selected |
|---|---|
| Workload type = `research`, `planning`, `coding`, `debugging`, `agent_workflow`, `code_review` | Premium (70B) |
| Complexity = `high` for any workload | Premium (70B) |
| Word count > 400 | Premium (70B) |
| `max_tokens` > 3000 | Premium (70B) |
| All other cases | Balanced / cost-efficient (8B) |

The routing decision is recorded verbatim in the trace, e.g.: `"🔀 Routing: Provider 'Groq' · Model 'llama-3.3-70b-versatile' — 'coding' workload with 'high' complexity → premium tier selected"`

**Provider-Model Compatibility Guardrail:** If the selected model is not available from the target provider, the routing engine automatically falls back to the provider's first available model — preventing hard failures.

---

### 8.2 Comparison Analysis: How the Best Model is Chosen

When running a multi-model comparison, the winner is determined by a **11-point composite scoring system**:

```
Score = 0

IF model has lowest TTFT          → +2 points   (Speed matters most for UX)
IF model has lowest Cost           → +2 points   (Cost matters most for FinOps)
IF model has highest Accuracy      → +2 points   (Quality matters most for output)
IF model has lowest Total Latency  → +1 point    (Secondary latency measure)
IF model has lowest VRAM           → +1 point    (Infrastructure efficiency)
IF model's Outlier Risk = SAFE     → +1 point    (Production reliability)

Maximum possible score = 11 points
```

The model with the **highest total score** is the Overall Winner and drives the recommendation text.

**Tie-Breaking:** In case of equal scores, the model appearing first in the comparison order is selected (first slot wins the tie).

---

### 8.3 Recommendation Text Logic

The recommendation paragraph is generated dynamically based on the winner's specific strengths:

1. **If winner is fastest** → Calls out exact TTFT value and labels it "ideal for latency-critical applications"
2. **If winner is cheapest** → States exact cost and frames it as "minimizing operational expenses"
3. **If winner is most accurate** → States accuracy percentage and frames it as "ensuring quality output"
4. **If winner is low outlier risk** → Frames it as "suitable for production workloads"
5. **For 2-model comparisons** → Adds specific percentage deltas vs. the other model (e.g., "21.8% lower latency", "90% cost savings")

---

## 9. Role-Based Access Control (RBAC)

The platform includes a **Role Selector** in the top navigation bar, allowing teams to simulate different user permissions.

| Role | Intended For | Access Level |
|---|---|---|
| 👁️ **Viewer** | Executives, stakeholders | Read-only: see dashboards, no configuration changes |
| 👤 **User** | Application developers | Can run gateway requests and comparisons |
| 👨‍💻 **Developer** | AI engineers | Can run benchmarks and modify prompts |
| ⚙️ **MLOps** | Ops engineers | Can edit policies and manage routing configs |
| 👑 **Admin** | Platform owners | Full access: delete profiles, modify budget limits, override all settings |

---

## 10. API Endpoints Reference

All endpoints are available at `http://localhost:8000/api/v1/`.

| Endpoint | Method | Description |
|---|---|---|
| `/gateway/generate` | POST | Run a single inference request through the full 10-stage pipeline |
| `/gateway/providers` | GET | List all configured providers, their enabled status, and available models |
| `/gateway/health` | GET | Runtime controller health status |
| `/gateway/dashboard` | GET | Runtime dashboard statistics |
| `/dashboard/metrics` | GET | Full FinOps dashboard: KPIs, agent metrics, RAG breakdown, canary stats, chargeback by department |
| `/experiments/compare` | POST | Run A/B comparison between two variants |
| `/experiments/compare-batch` | POST | Run multi-model comparison (2–6 models simultaneously) |
| `/experiments/variants` | GET | List all model variants in the registry |
| `/registry/variants` | GET | Full model catalog with specs |
| `/advisor/insights` | GET | System optimization insights and platform health grade |
| `/advisor/recommend` | POST | Zero-inference AI Solution Advisor — recommends models/providers for a described scenario |
| `/benchmarks/run` | POST | Start a benchmark job |
| `/benchmarks/jobs` | GET | List all benchmark jobs |
| `/benchmarks/jobs/{id}` | GET | Get a specific benchmark job result |
| `/governance/profiles` | GET | List all inference profiles |
| `/governance/profiles/{name}` | GET/PUT/DELETE | CRUD on a specific profile |
| `/governance/profiles/{name}/feature-flags` | PATCH | Toggle a feature flag on a profile |
| `/budget/status` | GET | Current spend vs. daily/monthly limits |

**Interactive API Documentation:** Available at `http://localhost:8000/docs` (Swagger UI)

---

## 11. Backend Engines & Their Roles

| Engine | File | Role |
|---|---|---|
| **RuntimeController** | `core/runtime_controller.py` | Orchestrates all 10 pipeline stages for every request. The central coordinator. |
| **RoutingEngine** | `core/routing_engine.py` | Determines which model to use based on profile, tier, and Prompt Intelligence classification. |
| **PromptClassifier** | `core/prompt_classifier.py` | Zero-inference workload classification engine. Assigns workload type, complexity, safety risk, and recommended parameters to every prompt. |
| **CacheEngine** | `core/cache_engine.py` | MD5-hash based semantic cache. In-memory; Redis-ready for production. |
| **BudgetEngine** | `core/budget_engine.py` | Tracks cumulative spend. Enforces daily limits. Manages agent session budgets with circuit-breaker pattern. |
| **PolicyEngine** | `core/policy_engine.py` | Validates temperature, cost-per-request, and other runtime constraints. |
| **GovernanceEngine** | `core/governance_engine.py` | CRUD for inference profiles. Validates profile rules. Maintains persistent audit trail. |
| **BenchmarkEngine** | `core/benchmark_engine.py` | Runs structured benchmark suites. Persists job results. Computes summary stats. |
| **ModelRegistry** | `core/model_registry.py` | Catalog of all quantized model variants with full specs and pricing. |
| **LLMClient (UnifiedLLMEngine)** | `core/llm_client.py` | Adapter layer for all providers (Groq, Gemini, OpenAI, xAI, Mistral, DeepSeek, OpenRouter, NVIDIA NIM, Alibaba, local). Normalizes responses into a unified format. |
| **InfraCollectors** | `core/infra_collectors.py` | Collects infrastructure/deployment node health data. |
| **PlatformState** | `core/platform_state.py` | Shared in-memory state for real-time KPI aggregation. |
| **AnalyticsDB** | `db/session.py` | In-memory log store for telemetry data (last 100 requests). |
| **BenchmarkDB** | `db/session.py` | In-memory dictionary store for benchmark job persistence. |
| **GovernanceStore** | `db/governance_store.py` | Persistent storage for inference profiles and audit logs. |

---

## 12. Prompt Intelligence Engine

> **What it is:** A zero-inference, rule-based classification engine (`core/prompt_classifier.py`) that runs on every incoming prompt **before** any LLM call is made. It identifies the workload type, complexity, safety risk, and optimal parameters in microseconds.

---

### 12.1 How It Works

1. The prompt text is matched against 19+ keyword pattern sets (in priority order)
2. The highest-confidence workload type is selected
3. A parameter tuning map maps the workload type to optimal `temperature` and `max_tokens`
4. A complexity score is derived from word count, keyword density, and sentence structure
5. Safety keywords are checked for risk flagging

No external API call is made. Total classification time is < 1ms.

---

### 12.2 Workload Types

| Workload Type | Trigger Examples | Optimal Temperature | Preferred Model Tier |
|---|---|---|---|
| `chat` | "hello", "how are you", casual greetings | 0.7 | 8B |
| `coding` | "write a function", "implement", "generate code" | 0.10 | 70B |
| `code_review` | "review this code", "refactor", "best practices" | 0.15 | 70B |
| `debugging` | "debug", "fix this error", "stack trace" | 0.05 | 70B |
| `sql` | "sql query", "select from", "join table" | 0.05 | 8B |
| `json_generation` | "json output", "structured output", "return json" | 0.00 | 8B |
| `translation` | "translate", "in french", "to english" | 0.20 | 8B |
| `summarization` | "summarize", "tldr", "key points" | 0.30 | 8B |
| `extraction` | "extract", "pull out", "identify", "parse" | 0.05 | 8B |
| `sentiment_analysis` | "sentiment", "positive or negative", "tone of" | 0.10 | 8B |
| `classification` | "classify", "categorize", "what category" | 0.10 | 8B |
| `creative_writing` | "write a story", "poem", "blog post" | 1.00 | 70B |
| `research` | "explain in detail", "deep dive", "compare and contrast" | 0.50 | 70B |
| `planning` | "create a plan", "roadmap", "architecture plan" | 0.50 | 70B |
| `rag` | "based on the document", "from the context" | 0.20 | 8B |
| `agent_workflow` | "agent", "multi-step", "tool use", "orchestrate" | 0.30 | 70B |
| `question_answer` | "what is", "who is", "tell me about" | 0.40 | 8B |
| `advisory` | "which model", "best llm for", "recommend a model" | 0.30 | 70B |
| `unknown` | No strong pattern match | 0.70 | 8B |

---

### 12.3 Parameter Auto-Tuning

After classification, the RuntimeController applies these rules:

- **Temperature:** `min(classifier_recommended_temp, profile_temperature × 1.5)` — Profile is the governance ceiling; classifier fills the optimal value within that range.
- **Max Tokens:** `min(classifier_recommended_max_tokens, profile_max_tokens × 2)` — Profile cap is respected; classifier can request more tokens when the workload justifies it.

**Example:** A `coding` prompt sets temperature=0.10 (deterministic) and max_tokens=2048 (enough for full functions). A `summarization` prompt sets temperature=0.30 and max_tokens=400 (short, concise output).

---

### 12.4 Safety Risk Detection

The classifier also evaluates the prompt for content risk:
- `safe` — No concerning patterns
- `moderate` — Some sensitive keywords present
- `high` — Patterns associated with harmful content generation detected → `🚨 Safety` warning appears in the execution trace

---

## 13. AI Solution Advisor

> **What it is:** A zero-inference advisory system accessible at `/api/v1/advisor/recommend`. It analyzes a free-text business scenario and returns ranked model recommendations, parameter guidance, and deployment advice — with no LLM call.

---

### 13.1 How to Use It

**Endpoint:** `POST /api/v1/advisor/recommend`

**Request Body:**
```json
{
  "scenario": "I want to build a customer support chatbot that handles billing questions. Expected volume: 50K requests/day.",
  "constraints": "prefer low cost, avoid INT4"
}
```

**What it returns:**
- `detected_workload` — Workload type detected (e.g., `chat`)
- `complexity` — Complexity level
- `key_requirements` — What this workload needs (e.g., `["conversational fluency", "low latency", "cost efficiency"]`)
- `recommended_parameters` — Optimal `temperature` and `max_tokens`
- `model_recommendations` — Ranked list (up to 4) of model variants with:
  - Rank, model ID, provider
  - `why` — Justification for recommendation
  - `strengths` / `weaknesses`
  - `estimated_cost_per_1k_requests`
  - `estimated_ttft_ms`
  - `confidence` score
- `deployment_advice` — Provider/infrastructure guidance for this workload
- `warnings` — Any constraint violations or risk flags
- `classification_confidence` — Overall confidence score

---

### 13.2 Workload-to-Model Mapping

The Advisor uses internal requirement rules to filter and rank variants:

| Workload | Needs 70B | Avoid INT4 | Key Focus |
|---|---|---|---|
| `coding`, `code_review`, `debugging` | Yes | Yes | Accuracy, determinism |
| `research`, `planning`, `agent_workflow` | Yes | Yes | Reasoning depth |
| `creative_writing`, `advisory` | Yes | No | Creativity, breadth |
| `sql`, `json_generation`, `extraction` | No | Yes | Structured output |
| `chat`, `summarization`, `translation` | No | No | Speed, cost |
| `rag`, `question_answer`, `sentiment` | No | No | Faithfulness, speed |

---

### 13.3 Deployment Advice Rules

| Workload | Advice Summary |
|---|---|
| `coding` / `debugging` | API-first (Groq) for speed; self-host only for proprietary code |
| `sql` / `json_generation` | API-first with JSON mode; temperature=0 strictly |
| `translation` | Gemini Flash recommended — strongest non-English performance |
| `research` | 70B models only; Gemini 1.5 Pro for very long documents |
| `rag` | API-first + vector DB (Pinecone/Weaviate); temperature ≤ 0.3 |
| `agent_workflow` | Ensure function-calling support; add cost circuit breakers |
| `chat` | 8B models sufficient; Groq for sub-500ms TTFT; enable semantic cache |

---

## 14. Configuration & Environment Variables

The platform reads all configuration from a `.env` file (or system environment variables) via `app/config.py`.

### 14.1 Provider API Keys

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | **Yes** | Primary provider. Platform will not start without this. |
| `GEMINI_API_KEY` | No | Enables Gemini provider (gemini-2.5-flash, gemini-1.5-flash) |
| `OPENAI_API_KEY` | No | Enables OpenAI provider (gpt-5 family, o3, o4-mini) |
| `ANTHROPIC_API_KEY` | No | Placeholder — adapter not yet implemented |
| `XAI_API_KEY` | No | Enables xAI Grok (grok-4, grok-3) |
| `DEEPSEEK_API_KEY` | No | Enables DeepSeek (deepseek-v3, deepseek-r1, deepseek-coder) |
| `MISTRAL_API_KEY` | No | Enables Mistral (mistral-large, codestral, mixtral-8x7b-instruct) |
| `OPENROUTER_API_KEY` | No | Enables OpenRouter unified gateway |
| `NVIDIA_NIM_API_KEY` | No | Enables NVIDIA NIM hosted inference |
| `ALIBABA_API_KEY` | No | Enables Alibaba Qwen models (qwen-plus, qwen-max, qwen-turbo) |

### 14.2 Provider Base URLs (Defaults)

| Variable | Default Value | Notes |
|---|---|---|
| `XAI_BASE_URL` | `https://api.x.ai/v1` | Override for proxied deployments |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | — |
| `MISTRAL_BASE_URL` | `https://api.mistral.ai/v1` | — |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | — |
| `ALIBABA_BASE_URL` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | — |
| `OPENAI_BASE_URL` | `None` | Set to use OpenAI-compatible endpoints |
| `NVIDIA_NIM_BASE_URL` | `None` | Required if using NVIDIA NIM |

### 14.3 Local / Self-Hosted Provider URLs

| Variable | Default Value | Notes |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Enabled automatically if `/models` is reachable |
| `VLLM_BASE_URL` | `None` | Set to enable vLLM backend |
| `TGI_BASE_URL` | `None` | Set to enable Hugging Face TGI |
| `LLAMACPP_BASE_URL` | `None` | Set to enable llama.cpp server |
| `VLLM_METRICS_URL` | `None` | Optional Prometheus metrics URL for vLLM |
| `TGI_METRICS_URL` | `None` | Optional Prometheus metrics URL for TGI |

---

*Document updated: 2026-07-02 | Platform: Compunnel AIOps Control | Version: 1.1*
