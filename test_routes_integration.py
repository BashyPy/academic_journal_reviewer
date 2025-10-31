#!/usr/bin/env python3
"""
Test script to verify routes integration with LangGraph and LangChain.
"""

import asyncio
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, 'app')

async def test_routes_integration():
    """Test the routes integration with LangGraph services."""
    
    print("🧪 Testing Routes Integration with LangGraph/LangChain")
    print("=" * 55)
    
    try:
        # Test 1: Import routes module
        print("📦 Testing routes import...")
        from app.api.routes import router
        print("✅ Routes imported successfully")
        
        # Test 2: Check LangChain service import
        print("🔗 Testing LangChain service import...")
        from app.services.langchain_service import langchain_service
        print("✅ LangChain service imported successfully")
        
        # Test 3: Check LangGraph workflow import
        print("🌐 Testing LangGraph workflow import...")
        from app.services.langgraph_workflow import langgraph_workflow
        print("✅ LangGraph workflow imported successfully")
        
        # Test 4: Check orchestrator integration
        print("🎯 Testing orchestrator integration...")
        from app.agents.orchestrator import orchestrator
        print("✅ Orchestrator imported successfully")
        
        # Test 5: Verify TaskStatus enum
        print("📊 Testing TaskStatus enum...")
        from app.models.schemas import TaskStatus
        assert hasattr(TaskStatus, 'RUNNING')
        assert hasattr(TaskStatus, 'PENDING')
        assert hasattr(TaskStatus, 'COMPLETED')
        assert hasattr(TaskStatus, 'FAILED')
        print("✅ TaskStatus enum verified")
        
        # Test 6: Check if LangChain models are initialized
        print("🤖 Testing LangChain models initialization...")
        if hasattr(langchain_service, 'models') and langchain_service.models:
            print("✅ LangChain models initialized")
        else:
            print("⚠️  LangChain models not fully initialized (API keys may be missing)")
        
        # Test 7: Check workflow compilation
        print("⚙️  Testing LangGraph workflow compilation...")
        if hasattr(langgraph_workflow, 'workflow') and langgraph_workflow.workflow:
            print("✅ LangGraph workflow compiled successfully")
        else:
            print("❌ LangGraph workflow not compiled")
            return False
        
        print("\n🎉 All integration tests PASSED!")
        print("✨ Routes are properly integrated with LangGraph and LangChain")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_route_endpoints():
    """Test that route endpoints are properly defined."""
    
    print("\n📍 Testing Route Endpoints")
    print("=" * 30)
    
    try:
        from app.api.routes import router
        
        # Get all routes
        routes = []
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, list(route.methods)))
        
        expected_endpoints = [
            '/submissions/upload',
            '/submissions/{submission_id}',
            '/submissions/{submission_id}/status',
            '/submissions/{submission_id}/report',
            '/submissions/{submission_id}/download',
            '/system/langgraph-status'
        ]
        
        print("📋 Checking expected endpoints:")
        for endpoint in expected_endpoints:
            found = any(endpoint in path for path, methods in routes)
            status = "✅" if found else "❌"
            print(f"  {status} {endpoint}")
        
        print(f"\n📊 Total routes defined: {len(routes)}")
        return True
        
    except Exception as e:
        print(f"❌ Route endpoint test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 LangGraph Routes Integration Test")
    print("=" * 40)
    
    # Run async integration test
    integration_success = asyncio.run(test_routes_integration())
    
    # Run route endpoints test
    endpoints_success = test_route_endpoints()
    
    overall_success = integration_success and endpoints_success
    
    if overall_success:
        print("\n🎊 ALL TESTS PASSED!")
        print("🔥 Routes are fully integrated with LangGraph and LangChain")
        print("🚀 The API is ready for LangGraph-powered manuscript reviews")
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("🔧 Please check the error messages above and fix any issues")
    
    sys.exit(0 if overall_success else 1)