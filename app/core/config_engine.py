from app.core.governance_engine import governance_engine
from app.schemas.config import InferenceProfile


class ConfigEngine:
    """
    Compatibility layer.

    Existing modules still import config_engine.get_profile().

    Internally, all requests are delegated to the Governance Engine,
    which is now the single source of truth.

    This class will eventually be removed once all modules directly
    consume GovernanceEngine.
    """

    def get_profile(self, name: str) -> InferenceProfile:
        return governance_engine.get_profile(name)

    def list_profiles(self):
        return governance_engine.list_profiles()

    def create_profile(self, profile: InferenceProfile):
        governance_engine.validate_profile(profile)
        return governance_engine.create_profile(profile)

    def update_profile(self, profile_name: str, profile: InferenceProfile):
        governance_engine.validate_profile(profile)
        return governance_engine.update_profile(profile_name, profile)

    def delete_profile(self, profile_name: str):
        return governance_engine.delete_profile(profile_name)

    def update_feature_flag(
        self,
        profile_name: str,
        feature_name: str,
        value: bool
    ):
        return governance_engine.update_feature_flag(
            profile_name,
            feature_name,
            value
        )

    def audit_logs(self):
        return governance_engine.get_audit_logs()


config_engine = ConfigEngine()