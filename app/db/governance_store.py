"""
Governance Profile Persistence Layer
Load/save profiles from SQLite/PostgreSQL instead of memory
"""

from typing import Optional, Dict, List
import json
import uuid
from datetime import datetime
from app.db.session import get_db_session
from app.db.models import GovernanceProfile, AuditLog
from app.schemas.config import InferenceProfile


class GovernanceProfileStore:
    """Persistent governance profile storage"""
    
    def __init__(self):
        self.db = get_db_session()
        self._default_profiles = self._get_default_profiles()
        self._initialize_defaults()
    
    def get_profile(self, profile_name: str) -> Optional[Dict]:
        """Get profile by name"""
        try:
            profile = self.db.query(GovernanceProfile)\
                .filter(GovernanceProfile.profile_name == profile_name)\
                .first()
            
            if profile:
                return json.loads(profile.config) if isinstance(profile.config, str) else profile.config
            return None
        except Exception as e:
            print(f"❌ Error getting profile: {e}")
            return None
    
    def list_profiles(self) -> List[Dict]:
        """List all profiles"""
        try:
            profiles = self.db.query(GovernanceProfile).all()
            return [json.loads(p.config) if isinstance(p.config, str) else p.config 
                    for p in profiles]
        except Exception as e:
            print(f"❌ Error listing profiles: {e}")
            return []
    
    def create_profile(self, profile: InferenceProfile) -> Dict:
        """Create new profile"""
        try:
            profile_data = profile.model_dump()
            db_profile = GovernanceProfile(
                id=str(uuid.uuid4()),
                profile_name=profile_data.get('profile_name'),
                config=profile_data,
                description=profile_data.get('description'),
                is_default=False,
            )
            self.db.add(db_profile)
            self.db.commit()
            
            # Log to audit trail
            self._log_audit('profile_created', 'profile', db_profile.id, None, profile_data)
            
            return profile_data
        except Exception as e:
            print(f"❌ Error creating profile: {e}")
            self.db.rollback()
            return None
    
    def update_profile(self, profile_name: str, profile: InferenceProfile) -> Optional[Dict]:
        """Update existing profile"""
        try:
            db_profile = self.db.query(GovernanceProfile)\
                .filter(GovernanceProfile.profile_name == profile_name)\
                .first()
            
            if not db_profile:
                return None
            
            old_config = json.loads(db_profile.config) if isinstance(db_profile.config, str) else db_profile.config
            new_config = profile.model_dump()
            
            db_profile.config = new_config
            db_profile.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Log to audit trail
            self._log_audit('profile_updated', 'profile', db_profile.id, old_config, new_config)
            
            return new_config
        except Exception as e:
            print(f"❌ Error updating profile: {e}")
            self.db.rollback()
            return None
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete profile"""
        try:
            db_profile = self.db.query(GovernanceProfile)\
                .filter(GovernanceProfile.profile_name == profile_name)\
                .first()
            
            if not db_profile:
                return False
            
            old_config = json.loads(db_profile.config) if isinstance(db_profile.config, str) else db_profile.config
            
            self.db.delete(db_profile)
            self.db.commit()
            
            # Log to audit trail
            self._log_audit('profile_deleted', 'profile', db_profile.id, old_config, None)
            
            return True
        except Exception as e:
            print(f"❌ Error deleting profile: {e}")
            self.db.rollback()
            return False
    
    def update_feature_flag(self, profile_name: str, feature_name: str, enabled: bool) -> Optional[Dict]:
        """Toggle feature flag in profile"""
        try:
            db_profile = self.db.query(GovernanceProfile)\
                .filter(GovernanceProfile.profile_name == profile_name)\
                .first()
            
            if not db_profile:
                return None
            
            config = json.loads(db_profile.config) if isinstance(db_profile.config, str) else db_profile.config
            
            if 'features' not in config:
                config['features'] = {}
            
            old_value = config['features'].get(feature_name)
            config['features'][feature_name] = enabled
            
            db_profile.config = config
            db_profile.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Log to audit trail
            self._log_audit('feature_toggled', 'feature', feature_name, 
                          {'enabled': old_value}, {'enabled': enabled})
            
            return config
        except Exception as e:
            print(f"❌ Error updating feature flag: {e}")
            self.db.rollback()
            return None
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """Get audit trail"""
        try:
            from app.db.models import AuditLog
            from sqlalchemy import desc
            
            logs = self.db.query(AuditLog)\
                .order_by(desc(AuditLog.timestamp))\
                .limit(limit)\
                .all()
            
            return [{
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'user_id': log.user_id,
                'details': log.details,
            } for log in logs]
        except Exception as e:
            print(f"❌ Error getting audit logs: {e}")
            return []
    
    def _log_audit(self, action: str, resource_type: str, resource_id: str, 
                   old_value: Optional[Dict], new_value: Optional[Dict]):
        """Log action to audit trail"""
        try:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=new_value,
                details=f"{action} on {resource_type} {resource_id}",
            )
            self.db.add(audit_log)
            self.db.commit()
        except Exception as e:
            print(f"⚠️ Warning: Could not log audit: {e}")
    
    def _get_default_profiles(self) -> Dict:
        """Default governance profiles"""
        return {
            'balanced': {
                'profile_name': 'balanced',
                'description': 'Balanced cost/performance (default)',
                'features': {
                    'enable_cache': True,
                    'enable_prompt_compression': False,
                    'enable_agentic_loop': True,
                    'enable_streaming': False,
                    'enable_auto_routing': True,
                    'enable_speculative_decoding': False,
                    'enable_canary': True,
                    'enable_rollback': True,
                },
                'runtime': {
                    'temperature': 0.7,
                    'max_tokens': 1024,
                    'rollback_ttft_ms': 1500.0,
                    'max_cost_per_request': 0.10,
                },
                'routing': {
                    'strategy': 'auto',
                    'tier': 'tier_2_balanced',
                    'fallback_model': 'llama-3.1-8b-instant',
                },
                'agent': {
                    'enable_agent_loop': True,
                    'max_calls_per_session': 20,
                    'max_cost_per_session_usd': 0.50,
                    'max_duration_seconds': 300,
                    'timeout_behavior': 'terminate',
                },
                'traffic_split': {
                    'primary_model': 'llama-3.1-8b-instant',
                    'primary_percent': 95,
                    'canary_model': 'llama-3.3-70b-versatile',
                    'canary_percent': 5,
                },
                'rollback_triggers': {
                    'ttft_ms_threshold': 1500.0,
                    'cost_multiplier_threshold': 1.3,
                    'error_rate_threshold': 0.05,
                    'check_window_seconds': 60,
                },
            },
            'performance': {
                'profile_name': 'performance',
                'description': 'Optimized for speed (higher cost)',
                'features': {
                    'enable_cache': True,
                    'enable_prompt_compression': False,
                    'enable_agentic_loop': False,
                    'enable_streaming': True,
                    'enable_auto_routing': True,
                    'enable_speculative_decoding': True,
                    'enable_canary': False,
                    'enable_rollback': False,
                },
                'runtime': {
                    'temperature': 0.3,
                    'max_tokens': 2048,
                    'rollback_ttft_ms': 800.0,
                    'max_cost_per_request': 0.25,
                },
                'routing': {
                    'strategy': 'tier_1_premium',
                    'tier': 'tier_1_premium',
                    'fallback_model': 'llama-3.3-70b-versatile',
                },
                'agent': {
                    'enable_agent_loop': False,
                    'max_calls_per_session': 5,
                    'max_cost_per_session_usd': 1.00,
                    'max_duration_seconds': 60,
                    'timeout_behavior': 'terminate',
                },
            },
            'cost_saver': {
                'profile_name': 'cost_saver',
                'description': 'Optimized for cost (lower speed)',
                'features': {
                    'enable_cache': True,
                    'enable_prompt_compression': True,
                    'enable_agentic_loop': False,
                    'enable_streaming': False,
                    'enable_auto_routing': True,
                    'enable_speculative_decoding': False,
                    'enable_canary': False,
                    'enable_rollback': False,
                },
                'runtime': {
                    'temperature': 0.5,
                    'max_tokens': 512,
                    'rollback_ttft_ms': 3000.0,
                    'max_cost_per_request': 0.02,
                },
                'routing': {
                    'strategy': 'tier_3_low_cost',
                    'tier': 'tier_3_low_cost',
                    'fallback_model': 'llama-3.1-8b-instant',
                },
                'agent': {
                    'enable_agent_loop': False,
                    'max_calls_per_session': 3,
                    'max_cost_per_session_usd': 0.10,
                    'max_duration_seconds': 120,
                    'timeout_behavior': 'terminate',
                },
            },
        }
    
    def _initialize_defaults(self):
        """Ensure default profiles exist in database"""
        try:
            for profile_name, config in self._default_profiles.items():
                existing = self.db.query(GovernanceProfile)\
                    .filter(GovernanceProfile.profile_name == profile_name)\
                    .first()
                
                if not existing:
                    profile = GovernanceProfile(
                        id=str(uuid.uuid4()),
                        profile_name=profile_name,
                        config=config,
                        description=config.get('description'),
                        is_default=True,
                    )
                    self.db.add(profile)
            
            self.db.commit()
            print("✅ Governance profiles initialized")
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize default profiles: {e}")
            self.db.rollback()


# Global instance
governance_profile_store = GovernanceProfileStore()
