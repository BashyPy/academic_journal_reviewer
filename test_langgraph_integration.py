#!/usr/bin/env python3
"""
Test script to verify LangGraph integration works correctly.
"""

import asyncio
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, 'app')

from app.services.langgraph_workflow import langgraph_workflow


async def test_langgraph_integration():
    """Test the LangGraph workflow with sample data."""
    
    # Sample submission data
    test_submission = {
        "_id": "test_submission_123",
        "title": "Sample Research Paper.pdf",
        "content": """
        Abstract
        
        This paper presents a novel approach to machine learning in healthcare applications.
        We propose a new algorithm that improves diagnostic accuracy by 15% compared to
        existing methods. Our methodology involves collecting data from 500 patients
        across three hospitals and applying deep learning techniques.
        
        Introduction
        
        Healthcare diagnostics have been revolutionized by artificial intelligence.
        Previous studies have shown promising results, but accuracy remains a challenge.
        This work addresses the gap by introducing a hybrid approach that combines
        traditional statistical methods with modern neural networks.
        
        Methodology
        
        We collected data from January 2023 to December 2023. The dataset includes
        demographic information, medical history, and diagnostic images. We used
        a convolutional neural network architecture with attention mechanisms.
        The model was trained using cross-validation with 80% training and 20% testing.
        
        Results
        
        Our approach achieved 92% accuracy on the test set, compared to 80% for
        baseline methods. The improvement was statistically significant (p < 0.001).
        We observed consistent performance across different patient demographics.
        
        Discussion
        
        The results demonstrate the effectiveness of our hybrid approach. The attention
        mechanism allows the model to focus on relevant features, improving interpretability.
        However, the study has limitations including the single-center design and
        limited follow-up period.
        
        Conclusion
        
        We present a novel machine learning approach for healthcare diagnostics that
        significantly improves accuracy. Future work should validate these findings
        in multi-center studies and explore real-world deployment challenges.
        """,
        "file_metadata": {
            "pages": 8,
            "file_type": "pdf",
            "original_filename": "Sample Research Paper.pdf",
            "file_size": 2048576
        },
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }
    
    print("🚀 Testing LangGraph workflow integration...")
    print(f"📄 Processing: {test_submission['title']}")
    print(f"📊 Content length: {len(test_submission['content'])} characters")
    
    try:
        # Execute the workflow
        final_report = await langgraph_workflow.execute_review(test_submission)
        
        print("\n✅ LangGraph workflow completed successfully!")
        print(f"📝 Report length: {len(final_report)} characters")
        print("\n📋 Final Report Preview:")
        print("=" * 50)
        print(final_report[:500] + "..." if len(final_report) > 500 else final_report)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ LangGraph workflow failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 LangGraph Integration Test")
    print("=" * 40)
    
    success = asyncio.run(test_langgraph_integration())
    
    if success:
        print("\n🎉 Integration test PASSED!")
        print("✨ The application is ready to use LangGraph and LangChain implementations.")
    else:
        print("\n💥 Integration test FAILED!")
        print("🔧 Please check the error messages above and fix any issues.")
    
    sys.exit(0 if success else 1)