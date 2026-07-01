# LLM Inference Ops Platform

FastAPI-based control plane for multi-provider LLM inference with routing, observability, governance, caching, and A/B experimentation.

## Highlights

- Unified gateway for provider and model overrides.
- Dynamic provider catalog endpoint for frontend dropdowns.
- Provider health-aware availability for local OpenAI-compatible backends.
- Built-in telemetry: TTFT, TPOT, cost, token usage, cache hit rate.
- Experimentation lab for side-by-side variant or model comparison.
- Benchmark pipeline with persisted jobs, suite execution, and trend/export views.
- Governance profile APIs for runtime feature flags and policy controls.
- Live dashboard polling and infrastructure snapshot in UI.

## Current Provider Support

### Native adapters
- Groq
- Gemini (via `google-genai`)

### OpenAI-compatible adapter path
- OpenAI
- xAI
- Mistral
- DeepSeek
- OpenRouter
- NVIDIA NIM
- Alibaba
- Ollama (local, no API key)
- vLLM (local)
- Hugging Face TGI (local)
- llama.cpp (local)

Notes:
- A provider is listed as enabled only when its required key/config is present.
- Local providers are enabled only if `base_url/models` is reachable.
- Anthropic is currently listed in catalog as placeholder (native adapter not yet implemented).

## Project Structure

```text
main.py
app/
	api/endpoints/      # Gateway, dashboard, experiments, governance, advisor
	core/               # Runtime controller, routing, cache, llm adapters, platform state
	schemas/            # Request/response/config models
	static/             # Dashboard UI
tests/
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- At least one provider credential and/or local provider endpoint
- `GROQ_API_KEY` is required by current settings model

### 2. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell
pip install -r requirements.txt
```

### 3. Create `.env`

Example minimal `.env`:

```env
# Required by current app settings
GROQ_API_KEY=your_groq_key

# Database configuration (optional, defaults to SQLite)
# DATABASE_URL=sqlite:///./llm_inference_ops.db
# DATABASE_URL=postgresql://user:password@localhost:5432/llm_inference_ops

# Optional cloud providers
GEMINI_API_KEY=
OPENAI_API_KEY=
XAI_API_KEY=
MISTRAL_API_KEY=
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
NVIDIA_NIM_API_KEY=
ALIBABA_API_KEY=

# Optional custom base URLs
OPENAI_BASE_URL=
XAI_BASE_URL=https://api.x.ai/v1
MISTRAL_BASE_URL=https://api.mistral.ai/v1
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
NVIDIA_NIM_BASE_URL=
ALIBABA_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1

# Local OpenAI-compatible providers
OLLAMA_BASE_URL=http://localhost:11434/v1
VLLM_BASE_URL=
TGI_BASE_URL=
LLAMACPP_BASE_URL=
```

### 4. Run API server

```bash
uvicorn main:app --reload
```

Server defaults:
- API root: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Dashboard UI: `http://127.0.0.1:8000/dashboard-ui`

## Persistence & Data Storage

The platform includes a complete **SQLAlchemy ORM persistence layer** that automatically saves all data across restarts.

### What's Persistent
- **Inference Telemetry**: All API requests logged with metrics (TTFT, cost, tokens, agent calls, etc.)
- **Governance Profiles**: Runtime policies and feature flag configurations
- **Benchmark Jobs**: Test runs and individual test results
- **Semantic Cache**: LLM prompt cache with hit tracking
- **Audit Trail**: Complete history of policy changes
- **Department Quotas**: Per-department budget tracking and spend

### Database Configuration

**Default: SQLite** (single-file, no setup required)
```bash
# Automatically creates ./llm_inference_ops.db
# Perfect for development and single-instance deployments
```

**Production: PostgreSQL** (recommended for multi-instance)
```env
# Set in .env:
DATABASE_URL=postgresql://user:password@localhost:5432/llm_inference_ops
```

### Verify Persistence

```bash
# Check current data in database
python verify_detailed.py

# Expected output:
# ✅ Recent Inference Logs (2+ entries showing department chargeback)
# ✅ Cost Breakdown by Department
# ✅ Governance Profiles (3 defaults: balanced, performance, cost_saver)
```

**See [PERSISTENCE_LAYER.md](PERSISTENCE_LAYER.md) for complete documentation.**

## Main API Endpoints

### Gateway
- `POST /api/v1/gateway/generate`
- `GET /api/v1/gateway/providers`
- `GET /api/v1/gateway/health`
- `GET /api/v1/gateway/dashboard`

### Dashboard and Advisor
- `GET /api/v1/dashboard/metrics`
- `GET /api/v1/advisor/insights`

### Experiments
- `GET /api/v1/experiments/variants`
- `POST /api/v1/experiments/compare`

### Benchmarks
- `POST /api/v1/benchmarks/run`
- `GET /api/v1/benchmarks/jobs`
- `GET /api/v1/benchmarks/jobs/{job_id}`

### Governance
- `GET /api/v1/governance/profiles`
- `GET /api/v1/governance/profile/{profile_name}`
- `POST /api/v1/governance/profile`
- `PUT /api/v1/governance/profile/{profile_name}`
- `PATCH /api/v1/governance/profile/{profile_name}/feature`
- `DELETE /api/v1/governance/profile/{profile_name}`
- `GET /api/v1/governance/audit`
- `GET /api/v1/governance/health`

## Frontend Notes

- The UI provider/model selectors are populated from `GET /api/v1/gateway/providers`.
- Disabled providers include a reason and are excluded from selectable dropdowns.
- Gateway and compare failures surface backend `detail` directly in alerts for faster diagnosis.
- Benchmarks tab supports running suite jobs, viewing persisted job history, and inspecting per-case results.
- Benchmarks tab includes recent-job trends (TTFT, pass rate, cost) and CSV/JSON export actions.

## Troubleshooting

- Provider not visible in UI:
	- Check API key/base URL in `.env`.
	- For local providers, verify `<base_url>/models` returns a response.
- Gateway or compare fails:
	- Check response details in UI alert and server logs.
	- Confirm selected model exists for the chosen provider.
- No metrics on dashboard:
	- Run a few generate/compare requests to create logs.

## Testing

If tests are present and `pytest` is installed:

```bash
pytest -q
```

## Status

Active development. Core routing, provider abstraction, dynamic provider catalog, governance APIs, live dashboard telemetry, and benchmark pipeline skeleton are in place.