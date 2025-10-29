#!/usr/bin/env python3
"""
Simple script to test the API endpoints and debug the Final Report issue.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.mongodb_service import mongodb_service
from app.models.schemas import TaskStatus

async def test_submissions():
    """Test function to check submissions in the database."""
    print("🔍 Checking submissions in database...")
    
    try:
        # Get all submissions from the database
        submissions_collection = mongodb_service.submissions
        submissions = []
        
        async for doc in submissions_collection.find():
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            submissions.append(doc)
        
        print(f"📊 Found {len(submissions)} submissions:")
        
        for submission in submissions:
            print(f"\n📄 Submission ID: {submission['id']}")
            print(f"   Title: {submission.get('title', 'N/A')}")
            print(f"   Status: {submission.get('status', 'N/A')}")
            print(f"   Created: {submission.get('created_at', 'N/A')}")
            print(f"   Completed: {submission.get('completed_at', 'N/A')}")
            print(f"   Has final_report: {'Yes' if submission.get('final_report') else 'No'}")
            
            if submission.get('final_report'):
                report_length = len(submission['final_report'])
                print(f"   Report length: {report_length} characters")
                print(f"   Report preview: {submission['final_report'][:100]}...")
            
            # Check if this submission has completed status
            if submission.get('status') == TaskStatus.COMPLETED.value:
                print(f"   ✅ This submission is marked as COMPLETED")
                
                # Test the API endpoint logic
                print(f"   🧪 Testing API response for this submission...")
                
                from app.services.disclaimer_service import disclaimer_service
                
                disclaimer_info = disclaimer_service.get_api_disclaimer()
                
                api_response = {
                    "submission_id": submission['id'],
                    "title": submission["title"],
                    "final_report": submission.get("final_report", ""),
                    "completed_at": submission.get("completed_at"),
                    "status": submission["status"],
                    "disclaimer": disclaimer_info.get("disclaimer", "")
                }
                
                print(f"   📤 API Response structure:")
                for key, value in api_response.items():
                    if key == 'final_report' and value:
                        print(f"      {key}: {len(value)} characters")
                    else:
                        print(f"      {key}: {value}")
            else:
                print(f"   ❌ This submission is NOT completed (status: {submission.get('status')})")
        
        if not submissions:
            print("❌ No submissions found in database!")
            print("💡 Try uploading a manuscript first through the web interface.")
            
    except Exception as e:
        print(f"❌ Error checking submissions: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function."""
    print("🚀 AARIS API Debug Tool")
    print("=" * 50)
    
    await test_submissions()
    
    print("\n" + "=" * 50)
    print("🏁 Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())