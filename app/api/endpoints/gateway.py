from fastapi import APIRouter, HTTPException
import logging

from app.schemas.request import InferenceRequest
from app.schemas.response import InferenceResponse
from app.core.runtime_controller import runtime_controller

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/generate",
    response_model=InferenceResponse,
    summary="Enterprise Runtime Gateway"
)
async def generate_text(request: InferenceRequest):
    """
    Enterprise Runtime Gateway

    Responsibilities
    ----------------
    ✓ Validate incoming request
    ✓ Forward request to Runtime Controller
    ✓ Return response

    All orchestration is delegated to RuntimeController.
    """

    try:
        return await runtime_controller.execute(request)

    except HTTPException:
        raise

    except Exception as ex:
        logger.exception("Gateway execution failed")

        raise HTTPException(
            status_code=500,
            detail=f"Gateway Error: {str(ex)}"
        )


@router.get(
    "/providers",
    summary="Available LLM providers and models"
)
async def providers():
    """
    Returns provider/model options based on configured API keys.
    """
    from app.core.llm_client import llm_engine

    return {
        "providers": llm_engine.list_providers()
    }


@router.get(
    "/health",
    summary="Runtime Controller Health"
)
async def health():
    """
    Returns the Runtime Controller health status.
    """
    return runtime_controller.health()


@router.get(
    "/dashboard",
    summary="Runtime Dashboard Summary"
)
async def dashboard():
    """
    Returns runtime dashboard statistics.
    """
    return runtime_controller.dashboard()