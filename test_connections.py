"""
Connection Diagnostic Tool for AI Healthcare Project
Tests all critical connections and reports issues.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

async def test_database_connection() -> Tuple[bool, str]:
    """Test database connection. Assumes database is already initialized."""
    try:
        from backend.database.connection import get_database_url, get_db_session
        
        db_url = get_database_url()
        print(f"  Database URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        
        # Test a simple query (database should already be initialized)
        async with get_db_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        
        return True, "Database connection successful"
    except RuntimeError as e:
        if "not initialized" in str(e):
            return False, "Database not initialized. Call init_database() first."
        return False, f"Database connection failed: {str(e)}"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

async def test_redis_connection() -> Tuple[bool, str]:
    """Test Redis connection. Assumes database is already initialized."""
    try:
        from backend.database.connection import get_redis_url, get_redis_client
        
        redis_url = get_redis_url()
        print(f"  Redis URL: {redis_url}")
        
        # Get Redis client (should already be initialized)
        redis_client = get_redis_client()
        if redis_client is None:
            return False, "Redis client not initialized (connection failed during startup)"
        
        # Test connection
        await redis_client.ping()
        return True, "Redis connection successful"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)} (This is optional - app will continue without Redis)"

def test_fhir_server() -> Tuple[bool, str]:
    """Test FHIR server connection."""
    try:
        import httpx
        
        fhir_url = os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir")
        print(f"  FHIR Server URL: {fhir_url}")
        
        # Try to connect to FHIR server
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{fhir_url}/metadata", follow_redirects=True)
            if response.status_code == 200:
                return True, "FHIR server connection successful"
            else:
                return False, f"FHIR server returned status {response.status_code}"
    except Exception as e:
        return False, f"FHIR server connection failed: {str(e)}"

def test_environment_variables() -> Tuple[bool, List[str]]:
    """Check for required/important environment variables."""
    issues = []
    
    # Check for database URL (optional - defaults to SQLite)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        issues.append("DATABASE_URL not set (will use SQLite fallback)")
    
    # Check for Redis URL (optional)
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        issues.append("REDIS_URL not set (will use default localhost:6379)")
    
    # Check for FHIR server URL
    fhir_url = os.getenv("FHIR_SERVER_URL")
    if not fhir_url:
        issues.append("FHIR_SERVER_URL not set (will use default localhost:8080)")
    
    # Check for LLM API key
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not openai_key and not anthropic_key:
        issues.append("No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    
    return len(issues) == 0, issues

def test_file_permissions() -> Tuple[bool, List[str]]:
    """Test file system permissions."""
    issues = []
    
    # Check if database file can be created/accessed
    db_path = project_root / "healthcare_ai.db"
    try:
        # Try to create/access the database directory
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Try to touch the file
        db_path.touch(exist_ok=True)
    except Exception as e:
        issues.append(f"Cannot access database file: {str(e)}")
    
    return len(issues) == 0, issues

async def main():
    """Run all connection tests."""
    print("=" * 60)
    print("AI Healthcare Project - Connection Diagnostic Tool")
    print("=" * 60)
    print()
    
    results = {}
    database_initialized = False
    
    try:
        # Test 1: Environment Variables
        print("1. Checking Environment Variables...")
        env_ok, env_issues = test_environment_variables()
        results["Environment Variables"] = (env_ok, env_issues)
        if env_ok:
            print("  [OK] All environment variables configured")
        else:
            print("  [WARN] Environment variable issues:")
            for issue in env_issues:
                print(f"    - {issue}")
        print()
        
        # Test 2: File Permissions
        print("2. Checking File Permissions...")
        file_ok, file_issues = test_file_permissions()
        results["File Permissions"] = (file_ok, file_issues)
        if file_ok:
            print("  [OK] File permissions OK")
        else:
            print("  [ERROR] File permission issues:")
            for issue in file_issues:
                print(f"    - {issue}")
        print()
        
        # Initialize database once before running database/Redis tests
        print("Initializing database connections...")
        from backend.database.connection import init_database
        await init_database()
        database_initialized = True
        print("  [OK] Database initialized")
        print()
        
        # Test 3: Database Connection
        print("3. Testing Database Connection...")
        db_ok, db_msg = await test_database_connection()
        results["Database"] = (db_ok, [db_msg])
        if db_ok:
            print(f"  [OK] {db_msg}")
        else:
            print(f"  [ERROR] {db_msg}")
        print()
        
        # Test 4: Redis Connection
        print("4. Testing Redis Connection...")
        redis_ok, redis_msg = await test_redis_connection()
        results["Redis"] = (redis_ok, [redis_msg])
        if redis_ok:
            print(f"  [OK] {redis_msg}")
        else:
            print(f"  [WARN] {redis_msg}")
        print()
        
        # Test 5: FHIR Server
        print("5. Testing FHIR Server Connection...")
        fhir_ok, fhir_msg = test_fhir_server()
        results["FHIR Server"] = (fhir_ok, [fhir_msg])
        if fhir_ok:
            print(f"  [OK] {fhir_msg}")
        else:
            print(f"  [WARN] {fhir_msg}")
        print()
        
        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        critical_failures = []
        warnings = []
        
        for name, (ok, messages) in results.items():
            if name == "Database" and not ok:
                critical_failures.append(f"{name}: {messages[0]}")
            elif name == "Redis" and not ok:
                warnings.append(f"{name}: {messages[0]} (optional)")
            elif name == "FHIR Server" and not ok:
                warnings.append(f"{name}: {messages[0]} (may be needed for full functionality)")
            elif not ok:
                warnings.append(f"{name}: {', '.join(messages)}")
        
        if critical_failures:
            print("\n[ERROR] CRITICAL ISSUES (must be fixed):")
            for failure in critical_failures:
                print(f"  - {failure}")
        
        if warnings:
            print("\n[WARN] WARNINGS (may affect functionality):")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not critical_failures and not warnings:
            print("\n[OK] All connections are working correctly!")
        elif not critical_failures:
            print("\n[OK] Core connections are working. Some optional services are unavailable.")
        else:
            print("\n[ERROR] Please fix the critical issues above before continuing.")
        
        print()
        
        # Recommendations
        if critical_failures or warnings:
            print("=" * 60)
            print("RECOMMENDATIONS")
            print("=" * 60)
            
            if not os.path.exists(".env"):
                print("\n1. Create a .env file with your configuration:")
                print("   cp .env.example .env")
                print("   # Then edit .env with your settings")
            
            if any("Database" in str(f) for f in critical_failures):
                print("\n2. Database connection issues:")
                print("   - For SQLite (default): Ensure write permissions in project directory")
                print("   - For PostgreSQL: Check DATABASE_URL format:")
                print("     DATABASE_URL=postgresql://user:password@localhost:5432/healthcare_ai")
                print("   - Ensure database server is running")
            
            if any("Redis" in str(w) for w in warnings):
                print("\n3. Redis is optional but recommended for caching:")
                print("   - Install Redis: https://redis.io/download")
                print("   - Or set REDIS_URL to your Redis instance")
                print("   - App will work without Redis, but caching will be disabled")
            
            if any("FHIR" in str(w) for w in warnings):
                print("\n4. FHIR server connection:")
                print("   - Start FHIR server: docker-compose up fhir")
                print("   - Or set FHIR_SERVER_URL to your FHIR endpoint")
                print("   - Some features require FHIR server to be available")
            
            print()
    
    finally:
        # Clean up database connections
        if database_initialized:
            try:
                from backend.database.connection import close_database
                await close_database()
                print("Database connections closed")
            except Exception as e:
                print(f"Warning: Error closing database connections: {e}")

if __name__ == "__main__":
    asyncio.run(main())
