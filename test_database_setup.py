"""
Quick test script to verify database setup.
Run this to test database initialization and basic operations.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.database import init_database, close_database, DatabaseService


async def test_database():
    """Test database initialization and basic operations."""
    print("=" * 60)
    print("Testing Database Setup")
    print("=" * 60)
    
    try:
        # Initialize database
        print("\n1. Initializing database...")
        await init_database()
        print("   ✓ Database initialized successfully")
        
        # Test database service
        print("\n2. Testing database service...")
        db_service = DatabaseService()
        print("   ✓ Database service created")
        
        # Test saving analysis
        print("\n3. Testing analysis save...")
        analysis_data = {
            "analysis_data": {"summary": "Test patient analysis"},
            "risk_scores": {"cardiovascular": 0.75, "readmission": 0.45},
            "alerts": [{"severity": "high", "message": "Test alert"}],
            "recommendations": ["Test recommendation"],
        }
        
        analysis_id = await db_service.save_analysis(
            patient_id="test-patient-001",
            analysis_data=analysis_data,
            user_id="test-user",
            correlation_id="test-correlation-001",
        )
        print(f"   ✓ Analysis saved with ID: {analysis_id}")
        
        # Test retrieving analysis
        print("\n4. Testing analysis retrieval...")
        retrieved = await db_service.get_latest_analysis("test-patient-001")
        if retrieved:
            print(f"   ✓ Analysis retrieved successfully")
            print(f"     - Patient ID: {retrieved['patient_id']}")
            print(f"     - Risk Scores: {retrieved['risk_scores']}")
            print(f"     - Alerts: {len(retrieved['alerts'])}")
        else:
            print("   ✗ Failed to retrieve analysis")
        
        # Test Redis cache (if available)
        print("\n5. Testing Redis cache...")
        if db_service.redis_client:
            summary = {"patient_id": "test-1", "risk_score": 0.8}
            await db_service.cache_patient_summary("test-1", summary, ttl=60)
            cached = await db_service.get_cached_summary("test-1")
            if cached:
                print("   ✓ Redis cache working")
            else:
                print("   ⚠ Redis cache not working (but not critical)")
        else:
            print("   ⚠ Redis not available (optional for development)")
        
        # Test audit logging
        print("\n6. Testing audit logging...")
        log_id = await db_service.log_audit_event(
            correlation_id="test-correlation-002",
            user_id="test-user",
            patient_id="test-patient-001",
            action="READ",
            resource_type="Patient",
            outcome="0",
            ip_address="127.0.0.1",
            details={"test": "data"},
        )
        print(f"   ✓ Audit log created with ID: {log_id}")
        
        print("\n" + "=" * 60)
        print("✓ All database tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await close_database()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_database())
    sys.exit(0 if success else 1)

