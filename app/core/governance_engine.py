from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException

from app.schemas.config import InferenceProfile
from app.db.governance_store import governance_profile_store


class GovernanceEngine:
    """
    Enterprise Runtime Governance Engine
    Now uses persistent storage instead of in-memory
    """

    def __init__(self):
        self.store = governance_profile_store
        # Load default profiles from persistent store
        self._load_default_profiles()

    # ---- DEFAULT PROFILES ----

    def _load_default_profiles(self):
        """Ensure default profiles exist in database"""
        # This is handled by governance_profile_store._initialize_defaults()
        # which runs on import
        pass

    # ---- PROFILE CRUD ----

    def list_profiles(self):
        """List all profiles from persistent storage"""
        profiles_dict = self.store.list_profiles()
        return [InferenceProfile(**p) if isinstance(p, dict) else p for p in profiles_dict]

    def get_profile(self, profile_name: str) -> InferenceProfile:
        """Get profile from persistent storage"""
        profile_dict = self.store.get_profile(profile_name)
        if not profile_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Profile '{profile_name}' not found."
            )
        return InferenceProfile(**profile_dict) if isinstance(profile_dict, dict) else profile_dict

    def create_profile(self, profile: InferenceProfile):
        """Create profile in persistent storage"""
        # Check if exists
        if self.store.get_profile(profile.profile_name):
            raise HTTPException(status_code=409, detail="Profile already exists.")
        
        # Validate
        self.validate_profile(profile)
        
        # Store
        result = self.store.create_profile(profile)
        return result

    def update_profile(self, profile_name: str, profile: InferenceProfile):
        """Update profile in persistent storage"""
        existing = self.store.get_profile(profile_name)
        if not existing:
            raise HTTPException(status_code=404, detail="Profile not found.")
        
        # Validate
        self.validate_profile(profile)
        
        # Store
        result = self.store.update_profile(profile_name, profile)
        return result

    def delete_profile(self, profile_name: str):
        """Delete profile from persistent storage"""
        success = self.store.delete_profile(profile_name)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found.")
        return {"message": f"{profile_name} deleted successfully."}

    # ---- FEATURE FLAGS ----

    def update_feature_flag(self, profile_name: str, feature_name: str, value: bool):
        """Toggle feature flag in profile"""
        profile = self.get_profile(profile_name)
        
        if not hasattr(profile.features, feature_name):
            raise HTTPException(status_code=400, detail=f"Unknown feature '{feature_name}'")
        
        # Update in-memory
        setattr(profile.features, feature_name, value)
        
        # Save to persistent storage
        result = self.store.update_feature_flag(profile_name, feature_name, value)
        return result

    # ---- AUDIT ----

    def log_audit(self, action: str, details: str, user_id: Optional[str] = None):
        """Log audit action"""
        # Handled by governance_profile_store._log_audit
        pass

    def get_audit_logs(self):
        """Get audit trail from persistent storage"""
        return self.store.get_audit_logs()

    # ---- VALIDATION ----

    def validate_profile(self, profile: InferenceProfile):
        """Validate profile against enterprise governance rules"""
        
        # 1. Runtime Safety Limits
        if profile.runtime.temperature < 0 or profile.runtime.temperature > 2:
            raise HTTPException(status_code=400, detail="Temperature must be between 0 and 2.")
        
        if profile.runtime.max_tokens <= 0:
            raise HTTPException(status_code=400, detail="Invalid max_tokens.")

        if hasattr(profile.runtime, 'rollback_ttft_ms') and profile.runtime.rollback_ttft_ms <= 0:
            raise HTTPException(status_code=400, detail="rollback_ttft_ms must be positive.")

        # 2. Hard FinOps Cost Governance
        if profile.runtime.max_cost_per_request and profile.runtime.max_cost_per_request > 0.5:
            raise HTTPException(
                status_code=403, 
                detail="Security Policy: Max cost per request exceeds enterprise governance limit ($0.50)."
            )

        # 3. Agent Budget Validation
        if profile.agent:
            if profile.agent.max_calls_per_session < 1:
                raise HTTPException(status_code=400, detail="max_calls_per_session must be >= 1")
            if profile.agent.max_cost_per_session_usd <= 0:
                raise HTTPException(status_code=400, detail="max_cost_per_session_usd must be > 0")

        # 4. Traffic Split Validation
        if profile.traffic_split:
            if (profile.traffic_split.primary_percent + profile.traffic_split.canary_percent) != 100:
                raise HTTPException(status_code=400, detail="Traffic split percentages must sum to 100")

        return True


# Global instance
governance_engine = GovernanceEngine()

