from pydantic import BaseModel

class BudgetStatus(BaseModel):
    total_spent: float
    daily_limit: float
    is_exceeded: bool