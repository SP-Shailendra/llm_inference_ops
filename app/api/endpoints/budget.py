from fastapi import APIRouter
from app.core.budget_engine import budget_engine

router = APIRouter(prefix="/budget", tags=["Budget Management"])

@router.get("/status", summary="Get current budget consumption")
async def get_budget_status():
    return budget_engine.check_budget_status()