"""
Database Models for LLM Inference Ops Platform
Persistent storage for:
- Inference telemetry & metrics
- Benchmark jobs & results
- Governance profiles
- Cache entries
- Audit logs
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()


class InferenceLog(Base):
    """Telemetry log for each inference request"""
    __tablename__ = "inference_logs"
    
    id = Column(String(36), primary_key=True)  # UUID
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Request info
    user_id = Column(String(255), index=True)
    department_id = Column(String(255), index=True)
    tenant_id = Column(String(255), index=True)
    user_role = Column(String(50))
    
    # Model & routing
    model_used = Column(String(255), index=True)
    provider_used = Column(String(255), index=True)
    optimization_profile = Column(String(255), index=True)
    workload_type = Column(String(50), index=True)  # prompt classification result
    
    # Metrics
    ttft_ms = Column(Float)
    tpot_ms = Column(Float)
    total_latency_ms = Column(Float)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_cost_usd = Column(Float, index=True)
    
    # Cache
    cache_hit = Column(Boolean, default=False)
    
    # Agent metrics
    agent_calls = Column(Integer, default=0)
    agent_total_cost_usd = Column(Float, default=0.0)
    agent_termination_reason = Column(String(50))
    
    # Canary & RAG
    routed_via_canary = Column(Boolean, default=False)
    canary_rolled_back = Column(Boolean, default=False)
    model_version_tag = Column(String(50))
    
    retrieval_cost_usd = Column(Float, default=0.0)
    retrieval_latency_ms = Column(Float, default=0.0)
    llm_cost_usd = Column(Float, default=0.0)
    rag_cost_percent = Column(Float, default=0.0)
    
    # Audit
    trace = Column(JSON)  # List of trace messages
    
    __table_args__ = (
        Index('idx_timestamp_dept', 'timestamp', 'department_id'),
        Index('idx_timestamp_model', 'timestamp', 'model_used'),
        Index('idx_cost_timestamp', 'total_cost_usd', 'timestamp'),
    )


class BenchmarkJob(Base):
    """Benchmark job definition"""
    __tablename__ = "benchmark_jobs"
    
    id = Column(String(36), primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    name = Column(String(255), index=True)
    description = Column(Text)
    status = Column(String(50), index=True)  # pending, running, completed, failed
    
    # Job config
    test_cases = Column(Integer)  # Number of test cases
    model_configs = Column(JSON)  # List of model configs to benchmark
    optimization_profile = Column(String(255))
    
    # Results aggregation
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    avg_ttft_ms = Column(Float)
    avg_tpot_ms = Column(Float)
    total_cost_usd = Column(Float, index=True)
    
    # Metadata
    user_id = Column(String(255), index=True)
    tags = Column(JSON)  # List of tags for filtering
    
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )


class BenchmarkResult(Base):
    """Individual benchmark result"""
    __tablename__ = "benchmark_results"
    
    id = Column(String(36), primary_key=True)  # UUID
    job_id = Column(String(36), ForeignKey('benchmark_jobs.id'), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Test case
    case_index = Column(Integer)
    prompt = Column(Text)
    expected_output = Column(Text)
    
    # Result
    model_used = Column(String(255), index=True)
    provider_used = Column(String(255))
    output = Column(Text)
    
    # Metrics
    ttft_ms = Column(Float)
    tpot_ms = Column(Float)
    total_latency_ms = Column(Float)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_cost_usd = Column(Float)
    
    # Evaluation
    passed = Column(Boolean)
    accuracy_retention = Column(Float)  # 0.0 - 1.0
    
    __table_args__ = (
        Index('idx_job_created', 'job_id', 'created_at'),
        Index('idx_job_model', 'job_id', 'model_used'),
    )


class GovernanceProfile(Base):
    """Runtime governance profile"""
    __tablename__ = "governance_profiles"
    
    id = Column(String(36), primary_key=True)  # UUID
    profile_name = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Full profile config (stored as JSON)
    config = Column(JSON)  # Complete InferenceProfile schema
    
    # Metadata
    is_default = Column(Boolean, default=False, index=True)
    description = Column(Text)


class CacheEntry(Base):
    """Semantic cache storage"""
    __tablename__ = "cache_entries"
    
    id = Column(String(36), primary_key=True)  # SHA256 hash of prompt
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Cache key
    prompt_hash = Column(String(64), unique=True, index=True)
    model_used = Column(String(255), index=True)
    
    # Cached response
    response_content = Column(Text)
    response_metrics = Column(JSON)  # Cached metrics
    
    # TTL & eviction
    ttl_seconds = Column(Integer, default=86400)  # 24 hours default
    hit_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_model_accessed', 'model_used', 'accessed_at'),
    )


class AuditLog(Base):
    """Audit trail for policy changes"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)  # UUID
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    action = Column(String(255), index=True)  # e.g., "profile_updated", "policy_changed"
    details = Column(Text)
    
    # Actor info
    user_id = Column(String(255), index=True)
    user_role = Column(String(50))
    
    # Resource
    resource_type = Column(String(50), index=True)  # "profile", "policy", "agent", etc.
    resource_id = Column(String(255), index=True)
    
    # Change tracking
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    __table_args__ = (
        Index('idx_timestamp_user', 'timestamp', 'user_id'),
        Index('idx_resource_timestamp', 'resource_type', 'resource_id', 'timestamp'),
    )


class DepartmentQuota(Base):
    """Department spending quotas & limits"""
    __tablename__ = "department_quotas"
    
    id = Column(String(36), primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Department
    department_id = Column(String(255), unique=True, index=True)
    
    # Quotas
    monthly_budget_usd = Column(Float)  # Monthly spend limit
    daily_budget_usd = Column(Float)    # Daily spend limit
    request_limit_per_day = Column(Integer)  # Daily request count
    
    # Tracking
    current_month_spend = Column(Float, default=0.0)
    current_day_spend = Column(Float, default=0.0)
    current_day_requests = Column(Integer, default=0)
    
    # Alerts
    alert_threshold_percent = Column(Float, default=80.0)  # Alert at 80% of budget


class SystemMetadata(Base):
    """System-level metadata & configuration"""
    __tablename__ = "system_metadata"
    
    key = Column(String(255), primary_key=True)
    value = Column(Text)  # JSON-serialized
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Examples:
    # key: "last_db_migration", value: "20260626_001"
    # key: "system_version", value: "1.0.0"
    # key: "total_requests_processed", value: "123456"
