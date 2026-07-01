# Phase 1 Implementation: Enterprise Features

## Status: IN PROGRESS ✅

### Agent Budget Controls + Canary Deployments

---

## ✅ COMPLETED (Step 1-4)

### 1. Enhanced Config Schema (`app/schemas/config.py`)
- ✅ Added `AgentControls` class with:
  - `enable_agent_loop: bool`
  - `max_calls_per_session: int = 20`
  - `max_cost_per_session_usd: float = 0.50`
  - `max_duration_seconds: int = 300`
  - `timeout_behavior: str` (stop | degrade)

- ✅ Added `TrafficSplit` class for canary routing:
  - `primary_model, primary_percent`
  - `canary_model, canary_percent`

- ✅ Added `RollbackTriggers` class for auto-rollback:
  - `ttft_ms_threshold: float = 1500`
  - `cost_multiplier_threshold: float = 1.3`
  - `error_rate_threshold: float = 0.05`

- ✅ Updated `InferenceProfile` to include:
  - `agent: AgentControls`
  - `traffic_split: Optional[TrafficSplit]`
  - `rollback_triggers: Optional[RollbackTriggers]`

---

### 2. Enhanced Response Schema (`app/schemas/response.py`)
- ✅ Added agent tracking to `InferenceMetrics`:
  - `agent_calls: int = 0`
  - `agent_total_cost_usd: float = 0.0`
  - `agent_termination_reason: Optional[str]`
  
- ✅ Added canary tracking:
  - `routed_via_canary: bool = False`
  - `model_version_tag: Optional[str] = None`

---

### 3. Enhanced Budget Engine (`app/core/budget_engine.py`)
- ✅ Added `AgentSession` class:
  - Tracks call count, total cost, duration
  - `is_active()` checks all limits
  - `record_call()` increments counters
  - `check_budget()` raises exceptions on threshold breach
  - `termination_reason` tracking

- ✅ Added custom exceptions:
  - `AgentBudgetExceededException`
  - `AgentMaxCallsExceededException`
  - `AgentSessionTimeout`

- ✅ Enhanced `BudgetEngine` with:
  - `create_agent_session()` - Initialize session with limits
  - `get_agent_session()` - Retrieve session
  - `check_agent_budget()` - Validate active limits
  - `record_agent_call()` - Log call cost
  - `end_agent_session()` - Finalize and cleanup

---

## 📋 TODO (Steps 5-8)

### 5. Update Runtime Controller (`app/core/runtime_controller.py`)
**Task:** Integrate agent session tracking into inference pipeline

Files to modify:
```python
# In generate_with_routing() method:
1. Before agent loop:
   - Create AgentSession from profile.agent config
   - session_id = request_id or uuid
   
2. In agent call loop (if enable_agentic_loop=true):
   - Call budget_engine.check_agent_budget(session_id)
   - Record call: budget_engine.record_agent_call(session_id, estimated_cost)
   - Catch AgentBudgetExceededException → terminate early
   
3. After completion:
   - End session: agent_session = budget_engine.end_agent_session(session_id)
   - Populate response metrics:
     * agent_calls = agent_session.call_count
     * agent_total_cost_usd = agent_session.total_cost_usd
     * agent_termination_reason = agent_session.termination_reason
```

**Estimated effort:** 1-2 hours

---

### 6. Update Governance Endpoints (`app/api/endpoints/governance.py`)
**Task:** Expose agent controls in profile CRUD

Changes needed:
```python
1. GET /api/v1/governance/profiles/{name}
   - Return profile.agent field with current limits
   
2. PUT /api/v1/governance/profiles/{name}
   - Accept updates to profile.agent
   - Validate: max_calls >= 1, max_cost_usd > 0
   
3. POST /api/v1/governance/profiles
   - Support agent config in payload
```

**Estimated effort:** 30 minutes

---

### 7. Update Dashboard (`app/api/endpoints/dashboard.py`)
**Task:** Add agent cost breakdown to metrics endpoint

New metrics to expose:
```python
{
  "agent_metrics": {
    "total_agent_calls": 42,
    "total_agent_cost_usd": 1.23,
    "avg_calls_per_request": 2.1,
    "avg_cost_per_call_usd": 0.029,
    "requests_terminated_by_budget": 3
  }
}
```

**Estimated effort:** 1 hour

---

### 8. Update UI (`app/static/index.html`)
**Task:** Add agent budget status badge and controls

Components to add:
```html
1. In Observability tab KPI section:
   - New card: "Agent Calls Today" with count
   - New card: "Agent Cost Today" with spend
   
2. In Policies tab (Profile Editor):
   - New section: "Agent Controls"
   - Toggle: enable_agentic_loop
   - Input: max_calls_per_session
   - Input: max_cost_per_session_usd
   - Input: max_duration_seconds
   
3. In comparison results:
   - Show agent_calls and agent_cost_usd if > 0
```

**Estimated effort:** 2-3 hours

---

## Phase 1b: Canary Deployments (Next Sprint)

Once Agent Budget is complete, we'll implement:

### 9. Routing Engine Updates (`app/core/routing_engine.py`)
- Implement weighted model selection based on `traffic_split` percentages
- Use deterministic hashing (hash of request_id % 100) to ensure consistent routing per session
- Track selected variant in response metrics

### 10. Runtime Controller Canary Logic
- After inference completes, check rollback triggers
- If TTFT/cost/error exceeds threshold, flip traffic_split back to 100/0
- Log rollback event with reason and timestamp
- Cooldown period to prevent flip-flop (e.g., 5 minutes)

### 11. Governance Profiles for Canary
- Support editing `traffic_split` and `rollback_triggers` in profile CRUD
- Validate: traffic percentages sum to 100
- Audit trail for canary changes

### 12. UI Canary Controls
- New Policies tab section: "Canary Deployment"
- Toggle: enable_canary
- Model selector: primary, canary
- Percent slider: 0-100 (traffic to canary)
- Rollback trigger display with current thresholds

---

## Testing Checklist

### Unit Tests
- [ ] Agent session creation with various limits
- [ ] Budget checks trigger correctly
- [ ] Termination reasons recorded properly
- [ ] Config parsing with new fields

### Integration Tests
- [ ] Agent session lifecycle (create → record calls → end)
- [ ] Multiple concurrent agent sessions
- [ ] Budget exceptions propagate correctly
- [ ] Profile CRUD with agent controls

### E2E Tests
- [ ] Gateway request with agent loop enabled
- [ ] Agent budget exceeded → graceful termination
- [ ] Metrics returned with agent fields populated
- [ ] Dashboard shows agent cost breakdown

---

## Deployment Notes

1. **Backward Compatibility:** Old profiles without `agent` config will use defaults
2. **Database Migration:** No schema changes needed (config stored in JSON)
3. **Monitoring:** Alert on `AgentBudgetExceededException` in logs
4. **Documentation:** Update API docs to show new config fields and metrics

---

## Next Steps

1. ✅ Implement Steps 5-8 (Runtime, Governance, Dashboard, UI)
2. ✅ Run unit + integration tests
3. ✅ Deploy Phase 1a (Agent Budget Controls)
4. ✅ Plan Phase 1b (Canary Deployments)

**Estimated Total Time:** 1-2 weeks with parallel work
