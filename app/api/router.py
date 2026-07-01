from fastapi import APIRouter
from app.api.endpoints import gateway, dashboard, experiments, advisor
from app.api.endpoints import benchmarks

api_router = APIRouter()

# Register the endpoints
api_router.include_router(gateway.router, prefix="/gateway", tags=["Core Gateway"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["FinOps Dashboard"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["Experimentation Lab"])
api_router.include_router(advisor.router, prefix="/advisor", tags=["Hybrid Advisor"])
api_router.include_router(benchmarks.router, prefix="/benchmarks", tags=["Benchmark Pipeline"])
from app.api.endpoints import governance

api_router.include_router(governance.router)