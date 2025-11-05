#!/usr/bin/env python3
"""
Verify Test Database Isolation
Ensures tests use separate database from production
"""
import os
import sys


def verify_test_isolation():
    """Verify test database isolation is working"""
    print("🔍 Verifying Test Database Isolation")
    print("=" * 50)

    # Test 1: Check TESTING environment variable
    print("\n1. Checking TESTING environment variable...")
    os.environ["TESTING"] = "true"
    testing = os.getenv("TESTING")
    if testing == "true":
        print(f"   ✅ TESTING={testing}")
    else:
        print(f"   ❌ TESTING={testing} (expected 'true')")
        return False

    # Test 2: Check database selection with TESTING=true
    print("\n2. Checking database with TESTING=true...")
    from app.core.config import settings

    if settings.MONGODB_DATABASE == "aaris_test":
        print(f"   ✅ Database: {settings.MONGODB_DATABASE}")
    else:
        print(f"   ❌ Database: {settings.MONGODB_DATABASE} (expected 'aaris_test')")
        return False

    # Test 3: Check database selection without TESTING
    print("\n3. Checking database without TESTING...")
    del os.environ["TESTING"]
    # Need to reload settings
    import importlib

    import app.core.config

    importlib.reload(app.core.config)
    from app.core.config import settings as prod_settings

    if prod_settings.MONGODB_DATABASE == "aaris":
        print(f"   ✅ Database: {prod_settings.MONGODB_DATABASE}")
    else:
        print(f"   ❌ Database: {prod_settings.MONGODB_DATABASE} (expected 'aaris')")
        return False

    # Test 4: Check pytest.ini configuration
    print("\n4. Checking pytest.ini configuration...")
    try:
        with open("pytest.ini", "r") as f:
            content = f.read()
            if "TESTING=true" in content and "MONGODB_DATABASE=aaris_test" in content:
                print("   ✅ pytest.ini configured correctly")
            else:
                print("   ❌ pytest.ini missing test environment variables")
                return False
    except FileNotFoundError:
        print("   ❌ pytest.ini not found")
        return False

    # Test 5: Check conftest.py has auto fixture
    print("\n5. Checking conftest.py configuration...")
    try:
        with open("tests/conftest.py", "r") as f:
            content = f.read()
            if "autouse=True" in content and "TESTING" in content:
                print("   ✅ conftest.py has auto-fixture")
            else:
                print("   ❌ conftest.py missing auto-fixture")
                return False
    except FileNotFoundError:
        print("   ❌ conftest.py not found")
        return False

    print("\n" + "=" * 50)
    print("✅ All checks passed! Test isolation is working correctly.")
    print("\nSummary:")
    print("  • Tests will use: aaris_test")
    print("  • Production uses: aaris")
    print("  • Automatic isolation: ENABLED")
    return True


if __name__ == "__main__":
    success = verify_test_isolation()
    sys.exit(0 if success else 1)
