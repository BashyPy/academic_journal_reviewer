#!/usr/bin/env python3
"""Simple system test to verify components are working."""

import asyncio
import sys

from app.core.config import settings
from app.services.langchain_service import langchain_service
from app.services.mongodb_service import mongodb_service


async def test_mongodb():
    """Test MongoDB connection."""
    try:
        # Test basic connection
        await mongodb_service.db.command("ping")
        print("✓ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        return False


def test_llm_models():
    """Test LLM model initialization."""
    try:
        models = langchain_service.models
        working_models = []

        for provider, model in models.items():
            if not isinstance(model, type(langchain_service.models.get("dummy", None))):
                working_models.append(provider)

        if working_models:
            print(f"✓ LLM models initialized: {', '.join(working_models)}")
            return True
        else:
            print("✗ No working LLM models found")
            return False
    except Exception as e:
        print(f"✗ LLM model test failed: {e}")
        return False


def test_config():
    """Test configuration."""
    print(f"MongoDB URL: {settings.MONGODB_URL}")
    print(f"Default LLM: {settings.DEFAULT_LLM}")
    print(f"GROQ API Key: {'Set' if settings.GROQ_API_KEY else 'Not set'}")
    print(f"OpenAI API Key: {'Set' if settings.OPENAI_API_KEY else 'Not set'}")
    return True


async def main():
    """Run all tests."""
    print("=== AARIS System Test ===")

    print("\n1. Configuration:")
    test_config()

    print("\n2. MongoDB:")
    mongodb_ok = await test_mongodb()

    print("\n3. LLM Models:")
    llm_ok = test_llm_models()

    print(f"\n=== Results ===")
    print(f"MongoDB: {'OK' if mongodb_ok else 'FAIL'}")
    print(f"LLM Models: {'OK' if llm_ok else 'FAIL'}")

    if mongodb_ok and llm_ok:
        print("✓ System ready")
        sys.exit(0)
    else:
        print("✗ System has issues")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
