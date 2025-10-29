from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import io

from app.services.pdf_generator import pdf_generator

router = APIRouter()


@router.get("/download/review/{review_id}")
async def download_review_pdf(review_id: str):
    """Download review report as PDF"""
    try:
        # Get review data (this would typically come from database)
        review_data = await get_review_data(review_id)
        
        if not review_data:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate_pdf_report(
            review_content=review_data["content"],
            submission_info=review_data["submission"]
        )
        
        # Create filename using {file_name}_reviewed format
        original_filename = review_data["submission"].get("title", "manuscript")
        # Remove extension and create safe filename
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        safe_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_name}_reviewed.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


def get_review_data(review_id: str) -> Dict[str, Any]:
    """Retrieve review data from database"""
    # This would typically query your database
    # For now, return mock data structure
    return {
        "content": "Mock review content",
        "submission": {
            "title": "Sample Academic Paper",
            "authors": "John Doe, Jane Smith",
            "review_id": review_id
        }
    }
