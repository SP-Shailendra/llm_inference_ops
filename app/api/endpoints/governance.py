from typing import List

from fastapi import APIRouter, HTTPException

from app.core.governance_engine import governance_engine
from app.schemas.config import InferenceProfile, AgentControls

router = APIRouter(
    prefix="/governance",
    tags=["Runtime Governance"]
)


# ==========================================================
# Profiles
# ==========================================================

@router.get(
    "/profiles",
    summary="List all runtime profiles"
)
async def list_profiles():

    return {
        "profiles": governance_engine.list_profiles()
    }


@router.get(
    "/profile/{profile_name}",
    summary="Get a runtime profile"
)
async def get_profile(profile_name: str):

    profile = governance_engine.get_profile(profile_name)

    return profile


@router.post(
    "/profile",
    summary="Create a runtime profile"
)
async def create_profile(
    profile: InferenceProfile
):

    governance_engine.validate_profile(profile)

    return governance_engine.create_profile(profile)


@router.put(
    "/profile/{profile_name}",
    summary="Replace runtime profile"
)
async def update_profile(
    profile_name: str,
    profile: InferenceProfile
):

    governance_engine.validate_profile(profile)

    return governance_engine.update_profile(
        profile_name,
        profile
    )


@router.delete(
    "/profile/{profile_name}",
    summary="Delete runtime profile"
)
async def delete_profile(
    profile_name: str
):

    return governance_engine.delete_profile(
        profile_name
    )


# ==========================================================
# Feature Flags
# ==========================================================

@router.patch(
    "/profile/{profile_name}/feature",
    summary="Toggle runtime feature flag"
)
async def update_feature_flag(
    profile_name: str,
    feature_name: str,
    enabled: bool
):

    return governance_engine.update_feature_flag(
        profile_name,
        feature_name,
        enabled
    )


# ==========================================================
# Agent Controls (NEW)
# ==========================================================

@router.get(
    "/profile/{profile_name}/agent",
    summary="Get agent budget controls for profile"
)
async def get_agent_controls(profile_name: str):
    """Returns agent call/cost/duration limits for a profile"""
    profile = governance_engine.get_profile(profile_name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found")
    
    return {
        "profile_name": profile_name,
        "agent": profile.agent.model_dump() if hasattr(profile, 'agent') else {}
    }


@router.patch(
    "/profile/{profile_name}/agent",
    summary="Update agent budget controls"
)
async def update_agent_controls(
    profile_name: str,
    controls: AgentControls
):
    """Update agent circuit breaker limits (max calls, cost, duration)"""
    profile = governance_engine.get_profile(profile_name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found")
    
    # Validate limits
    if controls.max_calls_per_session < 1:
        raise HTTPException(status_code=400, detail="max_calls_per_session must be >= 1")
    if controls.max_cost_per_session_usd <= 0:
        raise HTTPException(status_code=400, detail="max_cost_per_session_usd must be > 0")
    if controls.max_duration_seconds < 1:
        raise HTTPException(status_code=400, detail="max_duration_seconds must be >= 1")
    
    # Update profile
    profile.agent = controls
    governance_engine.update_profile(profile_name, profile)
    
    governance_engine.log_audit(
        "agent_controls_updated",
        f"Updated agent limits for profile '{profile_name}'"
    )
    
    return {
        "profile_name": profile_name,
        "agent": controls.model_dump(),
        "status": "updated"
    }


# ==========================================================
# Audit History
# ==========================================================

@router.get(
    "/audit",
    summary="Governance audit history"
)
async def audit_history():

    return {
        "total_events": len(
            governance_engine.get_audit_logs()
        ),
        "events": governance_engine.get_audit_logs()
    }


# ==========================================================
# Runtime Health
# ==========================================================

@router.get(
    "/health",
    summary="Runtime governance health"
)
async def governance_health():

    profiles = governance_engine.list_profiles()

    return {
        "status": "healthy",
        "runtime_profiles": len(profiles),
        "default_profile": "balanced",
        "audit_events": len(
            governance_engine.get_audit_logs()
        )
    }