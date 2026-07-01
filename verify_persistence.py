#!/usr/bin/env python3
"""Verify persistence layer initialization"""

from app.db.governance_store import governance_profile_store
from app.db.session import analytics_db, benchmark_db, get_db_session
from app.db.models import InferenceLog, GovernanceProfile, AuditLog

print("\n" + "="*60)
print("🗄️  PERSISTENCE LAYER VERIFICATION")
print("="*60)

# 1. Check governance profiles
print("\n✅ Governance Profiles:")
profiles = governance_profile_store.list_profiles()
for p in profiles:
    profile_name = p.get("profile_name") if isinstance(p, dict) else p.profile_name
    print(f"   - {profile_name}")

# 2. Check database session
print("\n✅ Database Connection:")
db_session = get_db_session()
try:
    profile_count = db_session.query(GovernanceProfile).count()
    print(f"   - SQLAlchemy Session: ✓ Active")
    print(f"   - Profiles in DB: {profile_count}")
finally:
    db_session.close()

# 3. Check analytics DB
print("\n✅ Analytics Database:")
all_logs = analytics_db.get_all()
print(f"   - Inference Logs: {len(all_logs)} records")

# 4. Check benchmark DB
print("\n✅ Benchmark Database:")
all_jobs = benchmark_db.list_jobs()
print(f"   - Benchmark Jobs: {len(all_jobs)} jobs")

print("\n" + "="*60)
print("✅ PERSISTENCE LAYER INITIALIZED SUCCESSFULLY!")
print("="*60)
print("\nNext: Make some API calls to generate telemetry")
print("Then restart the app - data should persist!")
print("="*60 + "\n")
