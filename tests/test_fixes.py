#!/usr/bin/env python3
"""
Quick test script to verify the error fixes work correctly.
"""
import asyncio
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


async def test_langchain_service():
    """Test LangChain service with token limits."""
    print("Testing LangChain service...")

    try:
        from app.services.langchain_service import langchain_service

        # Test with a large prompt that would exceed token limits
        large_prompt = (
            "Analyze this academic paper: " + "This is sample content. " * 2000
        )

        result = await langchain_service.invoke_with_rag(
            large_prompt,
            provider="groq",
            context={"domain": "computer_science", "title": "Test Paper"},
        )

        print(f"✅ LangChain service test passed. Result length: {len(result)}")
        return True

    except Exception as e:
        print(f"❌ LangChain service test failed: {e}")
        return False


async def test_llm_service():
    """Test basic LLM service with token limits."""
    print("Testing LLM service...")

    try:
        from app.services.llm_service import llm_service

        # Test with a large prompt
        large_prompt = "Summarize this content: " + "Sample text. " * 1000

        result = await llm_service.generate_content(large_prompt, "groq")

        print(f"✅ LLM service test passed. Result length: {len(result)}")
        return True

    except Exception as e:
        print(f"❌ LLM service test failed: {e}")
        return False


async def test_embedding_creation():
    """Test embedding creation with error handling."""
    print("Testing embedding creation...")

    try:
        from app.services.langchain_service import langchain_service

        # Test with sample content
        content = "This is a sample academic paper content for testing embeddings."
        metadata = {"title": "Test Paper", "domain": "computer_science"}

        result = await langchain_service.create_document_embeddings(content, metadata)

        print(f"✅ Embedding creation test passed. Created {len(result)} embeddings")
        return True

    except Exception as e:
        print(f"❌ Embedding creation test failed: {e}")
        return False


async def test_semantic_search():
    """Test semantic search with error handling."""
    print("Testing semantic search...")

    try:
        from app.services.langchain_service import langchain_service

        # Test semantic search
        query = "machine learning algorithms"

        results = await langchain_service.semantic_search(query, k=3)

        print(f"✅ Semantic search test passed. Found {len(results)} results")
        return True

    except Exception as e:
        print(f"❌ Semantic search test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Running error fix tests...\n")

    tests = [
        test_llm_service,
        test_langchain_service,
        test_embedding_creation,
        test_semantic_search,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()

    passed = sum(results)
    total = len(results)

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Error fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
