"""
Database Session & Persistence Layer
Supports SQLite (default) + PostgreSQL with SQLAlchemy ORM
Maintains backward compatibility with in-memory fallback
"""

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import create_engine, event, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
import uuid

# Import models
from app.db.models import (
    Base, InferenceLog, BenchmarkJob, BenchmarkResult, 
    GovernanceProfile, CacheEntry, AuditLog, SystemMetadata
)

# ========================================
# DATABASE CONFIGURATION
# ========================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./llm_inference_ops.db"  # Default to SQLite in project root
)

# Create engine based on database type
if "postgresql" in DATABASE_URL:
    # PostgreSQL for production
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Test connections before using
    )
else:
    # SQLite for development/testing
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def init_db():
    """Initialize database & create tables"""
    print(f"🗄️  Initializing database: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def get_db_session() -> Session:
    """Get a direct database session"""
    return SessionLocal()


# Initialize on module import
try:
    init_db()
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")


# ========================================
# ANALYTICS DATABASE (Telemetry Logs)
# ========================================

class AnalyticsDB:
    """Persistent analytics storage using SQLite/PostgreSQL"""
    
    def __init__(self):
        self.db = get_db_session()
    
    def add_log(self, metrics: Dict):
        """Store inference telemetry"""
        try:
            log_entry = InferenceLog(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                # Copy all metrics to database columns
                **{k: v for k, v in metrics.items() 
                   if k in ['user_id', 'department_id', 'tenant_id', 'user_role',
                           'model_used', 'provider_used', 'optimization_profile',
                           'ttft_ms', 'tpot_ms', 'total_latency_ms', 
                           'input_tokens', 'output_tokens', 'total_cost_usd',
                           'cache_hit', 'agent_calls', 'agent_total_cost_usd',
                           'agent_termination_reason', 'routed_via_canary',
                           'canary_rolled_back', 'model_version_tag',
                           'retrieval_cost_usd', 'retrieval_latency_ms', 
                           'llm_cost_usd', 'rag_cost_percent', 'trace']}
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            print(f"❌ Error adding inference log: {e}")
            self.db.rollback()
    
    def get_all(self) -> List[Dict]:
        """Retrieve all logs"""
        try:
            logs = self.db.query(InferenceLog)\
                .order_by(desc(InferenceLog.timestamp))\
                .limit(1000)\
                .all()
            return [self._log_to_dict(log) for log in logs]
        except Exception as e:
            print(f"❌ Error fetching logs: {e}")
            return []
    
    def get_by_department(self, department_id: str) -> List[Dict]:
        """Get logs for specific department"""
        try:
            logs = self.db.query(InferenceLog)\
                .filter(InferenceLog.department_id == department_id)\
                .order_by(desc(InferenceLog.timestamp))\
                .all()
            return [self._log_to_dict(log) for log in logs]
        except Exception as e:
            print(f"❌ Error fetching department logs: {e}")
            return []
    
    def get_cost_breakdown(self, department_id: Optional[str] = None):
        """Get cost breakdown by department or all"""
        try:
            query = self.db.query(InferenceLog)
            if department_id:
                query = query.filter(InferenceLog.department_id == department_id)
            logs = query.all()
            
            breakdown = {}
            for log in logs:
                dept = log.department_id or "unassigned"
                if dept not in breakdown:
                    breakdown[dept] = {"requests": 0, "cost_usd": 0.0}
                breakdown[dept]["requests"] += 1
                breakdown[dept]["cost_usd"] += log.total_cost_usd or 0.0
            
            return breakdown
        except Exception as e:
            print(f"❌ Error getting cost breakdown: {e}")
            return {}
    
    @staticmethod
    def _log_to_dict(log: InferenceLog) -> Dict:
        """Convert database log to dictionary"""
        return {
            'id': log.id,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'user_id': log.user_id,
            'department_id': log.department_id,
            'tenant_id': log.tenant_id,
            'user_role': log.user_role,
            'model_used': log.model_used,
            'provider_used': log.provider_used,
            'optimization_profile': log.optimization_profile,
            'ttft_ms': log.ttft_ms,
            'tpot_ms': log.tpot_ms,
            'total_latency_ms': log.total_latency_ms,
            'input_tokens': log.input_tokens,
            'output_tokens': log.output_tokens,
            'total_cost_usd': log.total_cost_usd,
            'cache_hit': log.cache_hit,
            'agent_calls': log.agent_calls,
            'agent_total_cost_usd': log.agent_total_cost_usd,
            'agent_termination_reason': log.agent_termination_reason,
            'routed_via_canary': log.routed_via_canary,
            'canary_rolled_back': log.canary_rolled_back,
            'model_version_tag': log.model_version_tag,
            'retrieval_cost_usd': log.retrieval_cost_usd,
            'retrieval_latency_ms': log.retrieval_latency_ms,
            'llm_cost_usd': log.llm_cost_usd,
            'rag_cost_percent': log.rag_cost_percent,
            'trace': log.trace,
        }


# ========================================
# BENCHMARK DATABASE (Jobs & Results)
# ========================================

class BenchmarkDB:
    """Persistent benchmark storage"""
    
    def __init__(self):
        self.db = get_db_session()
    
    def create_job(self, payload: Dict) -> Dict:
        """Create benchmark job"""
        try:
            job = BenchmarkJob(
                id=payload.get('job_id', str(uuid.uuid4())),
                name=payload.get('name'),
                description=payload.get('description'),
                status=payload.get('status', 'pending'),
                test_cases=payload.get('test_cases', 0),
                model_configs=payload.get('model_configs', []),
                optimization_profile=payload.get('optimization_profile', 'balanced'),
                user_id=payload.get('user_id'),
                tags=payload.get('tags', []),
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return self._job_to_dict(job)
        except Exception as e:
            print(f"❌ Error creating benchmark job: {e}")
            self.db.rollback()
            return payload
    
    def update_job(self, job_id: str, patch: Dict) -> Optional[Dict]:
        """Update benchmark job"""
        try:
            job = self.db.query(BenchmarkJob).filter(BenchmarkJob.id == job_id).first()
            if not job:
                return None
            
            for key, value in patch.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            job.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(job)
            return self._job_to_dict(job)
        except Exception as e:
            print(f"❌ Error updating benchmark job: {e}")
            self.db.rollback()
            return None
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get benchmark job"""
        try:
            job = self.db.query(BenchmarkJob).filter(BenchmarkJob.id == job_id).first()
            return self._job_to_dict(job) if job else None
        except Exception as e:
            print(f"❌ Error getting benchmark job: {e}")
            return None
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs (newest first)"""
        try:
            jobs = self.db.query(BenchmarkJob)\
                .order_by(desc(BenchmarkJob.created_at))\
                .all()
            return [self._job_to_dict(job) for job in jobs]
        except Exception as e:
            print(f"❌ Error listing benchmark jobs: {e}")
            return []
    
    def add_result(self, job_id: str, result: Dict) -> Dict:
        """Add benchmark result"""
        try:
            db_result = BenchmarkResult(
                id=str(uuid.uuid4()),
                job_id=job_id,
                case_index=result.get('case_index', 0),
                prompt=result.get('prompt'),
                expected_output=result.get('expected_output'),
                model_used=result.get('model_used'),
                provider_used=result.get('provider_used'),
                output=result.get('output'),
                ttft_ms=result.get('ttft_ms'),
                tpot_ms=result.get('tpot_ms'),
                total_latency_ms=result.get('total_latency_ms'),
                input_tokens=result.get('input_tokens'),
                output_tokens=result.get('output_tokens'),
                total_cost_usd=result.get('total_cost_usd'),
                passed=result.get('passed'),
                accuracy_retention=result.get('accuracy_retention'),
            )
            self.db.add(db_result)
            self.db.commit()
            return result
        except Exception as e:
            print(f"❌ Error adding benchmark result: {e}")
            self.db.rollback()
            return result
    
    @staticmethod
    def _job_to_dict(job: BenchmarkJob) -> Dict:
        """Convert job to dictionary"""
        return {
            'job_id': job.id,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            'name': job.name,
            'description': job.description,
            'status': job.status,
            'test_cases': job.test_cases,
            'passed_cases': job.passed_cases,
            'failed_cases': job.failed_cases,
            'model_configs': job.model_configs,
            'optimization_profile': job.optimization_profile,
            'avg_ttft_ms': job.avg_ttft_ms,
            'avg_tpot_ms': job.avg_tpot_ms,
            'total_cost_usd': job.total_cost_usd,
            'user_id': job.user_id,
            'tags': job.tags,
        }


# ========================================
# GLOBAL INSTANCES
# ========================================

analytics_db = AnalyticsDB()
benchmark_db = BenchmarkDB()

benchmark_db = BenchmarkDB()