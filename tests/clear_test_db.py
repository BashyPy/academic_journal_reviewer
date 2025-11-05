#!/usr/bin/env python3
"""
Clear Test Database Script
Safely clears the test database without affecting production
"""
import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient


async def clear_test_database():
    """Clear the test database"""
    # Safety check - only allow clearing test database
    db_name = os.getenv("MONGODB_DATABASE", "aaris_test")

    if db_name == "aaris":
        print("❌ ERROR: Cannot clear production database!")
        print("   Set MONGODB_DATABASE=aaris_test to clear test database")
        sys.exit(1)

    if not db_name.endswith("_test"):
        print(f"⚠️  WARNING: Database name '{db_name}' doesn't end with '_test'")
        response = input("Are you sure you want to clear this database? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    try:
        client = AsyncIOMotorClient(mongodb_url)

        # List collections before clearing
        db = client[db_name]
        collections = await db.list_collection_names()

        if not collections:
            print(f"✅ Database '{db_name}' is already empty")
            return

        print(f"📋 Collections in '{db_name}':")
        for col in collections:
            count = await db[col].count_documents({})
            print(f"   - {col}: {count} documents")

        # Confirm deletion
        print(f"\n⚠️  About to clear database: {db_name}")
        response = input("Continue? (yes/no): ")

        if response.lower() != "yes":
            print("Aborted.")
            return

        # Drop database
        await client.drop_database(db_name)
        print(f"✅ Successfully cleared database: {db_name}")

    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    # Set test environment
    os.environ["TESTING"] = "true"
    os.environ.setdefault("MONGODB_DATABASE", "aaris_test")

    print("🧹 Test Database Cleanup Tool")
    print("=" * 50)

    asyncio.run(clear_test_database())
