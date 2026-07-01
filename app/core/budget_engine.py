from datetime import datetime, timedelta
from typing import Optional
from app.db.session import analytics_db
from app.schemas.budget import BudgetStatus
from app.core.exceptions import BudgetExceededException

# NEW: Agent Budget Exceptions
class AgentBudgetExceededException(BudgetExceededException):
    """Raised when agent session exceeds cost or call limits"""
    pass

class AgentMaxCallsExceededException(AgentBudgetExceededException):
    """Raised when agent exceeds max call count"""
    pass

class AgentSessionTimeout(AgentBudgetExceededException):
    """Raised when agent session exceeds max duration"""
    pass


class AgentSession:
    """
    Tracks a single agent's execution within a request session.
    Implements circuit breaker pattern to prevent cost explosions.
    """
    def __init__(self, session_id: str, max_calls: int = 20, max_cost_usd: float = 0.50, max_duration_seconds: int = 300):
        self.session_id = session_id
        self.call_count = 0
        self.total_cost_usd = 0.0
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self.max_duration_seconds = max_duration_seconds
        self.start_time = datetime.utcnow()
        self.termination_reason = None

    def is_active(self) -> bool:
        """Check if session is still active (not exceeded limits)"""
        if self.call_count >= self.max_calls:
            self.termination_reason = "max_calls_reached"
            return False
        if self.total_cost_usd >= self.max_cost_usd:
            self.termination_reason = "budget_exceeded"
            return False
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        if elapsed >= self.max_duration_seconds:
            self.termination_reason = "timeout"
            return False
        return True

    def record_call(self, cost_usd: float) -> bool:
        """Record an agent call. Return True if successful, False if budget exceeded."""
        if not self.is_active():
            return False
        self.call_count += 1
        self.total_cost_usd += cost_usd
        return self.is_active()

    def check_budget(self) -> None:
        """Raise exception if session exceeds limits"""
        if self.call_count >= self.max_calls:
            raise AgentMaxCallsExceededException(
                f"Agent session exceeded max calls ({self.max_calls}). Terminating."
            )
        if self.total_cost_usd >= self.max_cost_usd:
            raise AgentBudgetExceededException(
                f"Agent session exceeded max cost (${self.max_cost_usd}). Terminating."
            )
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        if elapsed >= self.max_duration_seconds:
            raise AgentSessionTimeout(
                f"Agent session exceeded max duration ({self.max_duration_seconds}s). Terminating."
            )


class BudgetEngine:
    """
    Tracks inference spend and enforces budget policies.
    Supports both request-level and agent-level budget controls.
    """
    def __init__(self):
        self.daily_limit = 50.0 # Default fallback
        self.monthly_limit = 1000.0
        self._agent_sessions = {}  # session_id -> AgentSession

    def check_budget_status(self) -> BudgetStatus:
        logs = analytics_db.get_all()
        total_spend = sum(l.get("total_cost_usd", 0) for l in logs)
        
        return BudgetStatus(
            total_spent=total_spend,
            daily_limit=self.daily_limit,
            is_exceeded=(total_spend >= self.daily_limit)
        )

    def validate_request(self, estimated_cost: float):
        status = self.check_budget_status()
        if status.total_spent + estimated_cost > self.daily_limit:
            raise BudgetExceededException("Request rejected: Daily budget limit reached.")

    # NEW: Agent session management
    def create_agent_session(self, session_id: str, max_calls: int = 20, 
                            max_cost_usd: float = 0.50, max_duration_seconds: int = 300) -> AgentSession:
        """Create a new agent session with configured limits"""
        session = AgentSession(session_id, max_calls, max_cost_usd, max_duration_seconds)
        self._agent_sessions[session_id] = session
        return session

    def get_agent_session(self, session_id: str) -> Optional[AgentSession]:
        """Retrieve existing agent session"""
        return self._agent_sessions.get(session_id)

    def check_agent_budget(self, session_id: str) -> bool:
        """Check if agent session is still active. Raises exception if limits exceeded."""
        session = self.get_agent_session(session_id)
        if not session:
            return True  # No session = no limits
        session.check_budget()
        return True

    def record_agent_call(self, session_id: str, cost_usd: float) -> bool:
        """Record an agent call cost. Return True if successful."""
        session = self.get_agent_session(session_id)
        if not session:
            return True
        success = session.record_call(cost_usd)
        if not success:
            raise AgentBudgetExceededException(
                f"Agent budget exceeded. Calls: {session.call_count}/{session.max_calls}, "
                f"Cost: ${session.total_cost_usd:.6f}/${session.max_cost_usd}"
            )
        return True

    def end_agent_session(self, session_id: str) -> AgentSession:
        """Finalize agent session and return summary"""
        session = self.get_agent_session(session_id)
        if session:
            del self._agent_sessions[session_id]
        return session


budget_engine = BudgetEngine()