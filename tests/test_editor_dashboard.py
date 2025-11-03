"""Tests for Editor Dashboard functionality"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.api.editor_dashboard_routes import (
    get_editor_stats,
    list_all_submissions,
    get_submission_details,
    make_editorial_decision,
    reprocess_submission,
    get_submission_analytics,
    get_domain_distribution,
    get_review_performance,
)
from app.models.roles import UserRole


@pytest.fixture
def mock_editor_user():
    """Mock editor user"""
    return {
        "user_id": "editor123",
        "email": "editor@journal.com",
        "role": UserRole.EDITOR.value,
    }


@pytest.fixture
def mock_db():
    """Mock database"""
    db = MagicMock()
    db.submissions = MagicMock()
    db.agent_tasks = MagicMock()
    db.audit_logs = MagicMock()
    return db


@pytest.mark.asyncio
async def test_get_editor_stats(mock_editor_user, mock_db):
    """Test getting editor dashboard statistics"""
    mock_db.submissions.count_documents = AsyncMock(side_effect=[150, 12, 8, 125, 5, 3, 18])
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        stats = await get_editor_stats(mock_editor_user)
    
    assert stats["total_submissions"] == 150
    assert stats["pending_review"] == 12
    assert stats["in_review"] == 8
    assert stats["completed"] == 125
    assert stats["failed"] == 5
    assert stats["today_submissions"] == 3
    assert stats["this_week"] == 18


@pytest.mark.asyncio
async def test_list_all_submissions(mock_editor_user, mock_db):
    """Test listing all submissions"""
    mock_submissions = [
        {"_id": "sub1", "title": "Test 1", "status": "completed"},
        {"_id": "sub2", "title": "Test 2", "status": "processing"},
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=mock_submissions)
    
    mock_db.submissions.find = MagicMock(return_value=mock_cursor)
    mock_db.submissions.count_documents = AsyncMock(return_value=2)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await list_all_submissions(mock_editor_user, skip=0, limit=50)
    
    assert len(result["submissions"]) == 2
    assert result["total"] == 2
    assert result["submissions"][0]["_id"] == "sub1"


@pytest.mark.asyncio
async def test_get_submission_details(mock_editor_user, mock_db):
    """Test getting submission details"""
    mock_submission = {
        "_id": "sub123",
        "title": "Test Submission",
        "status": "completed",
    }
    mock_tasks = [
        {"_id": "task1", "agent_type": "methodology", "status": "completed"},
        {"_id": "task2", "agent_type": "literature", "status": "completed"},
    ]
    
    mock_db.submissions.find_one = AsyncMock(return_value=mock_submission)
    
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_tasks)
    mock_db.agent_tasks.find = MagicMock(return_value=mock_cursor)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await get_submission_details("sub123", mock_editor_user)
    
    assert result["_id"] == "sub123"
    assert result["title"] == "Test Submission"
    assert len(result["agent_tasks"]) == 2


@pytest.mark.asyncio
async def test_get_submission_details_not_found(mock_editor_user, mock_db):
    """Test getting non-existent submission"""
    mock_db.submissions.find_one = AsyncMock(return_value=None)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        with pytest.raises(HTTPException) as exc_info:
            await get_submission_details("nonexistent", mock_editor_user)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_make_editorial_decision(mock_editor_user, mock_db):
    """Test making editorial decision"""
    from app.api.editor_dashboard_routes import EditorialDecision
    
    mock_submission = {"_id": "sub123", "title": "Test"}
    mock_db.submissions.find_one = AsyncMock(return_value=mock_submission)
    mock_db.submissions.update_one = AsyncMock()
    
    decision = EditorialDecision(
        decision="accept",
        comments="Excellent research",
        notify_author=True,
    )
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        with patch("app.api.editor_dashboard_routes.audit_logger.log_event", new_callable=AsyncMock):
            result = await make_editorial_decision("sub123", decision, mock_editor_user)
    
    assert result["message"] == "Editorial decision recorded"
    assert result["decision"]["decision"] == "accept"
    assert result["decision"]["comments"] == "Excellent research"
    assert result["decision"]["editor_id"] == "editor123"


@pytest.mark.asyncio
async def test_reprocess_submission(mock_editor_user, mock_db):
    """Test reprocessing failed submission"""
    mock_submission = {"_id": "sub123", "status": "failed"}
    mock_db.submissions.find_one = AsyncMock(return_value=mock_submission)
    mock_db.submissions.update_one = AsyncMock()
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        with patch("app.api.editor_dashboard_routes.audit_logger.log_event", new_callable=AsyncMock):
            result = await reprocess_submission("sub123", mock_editor_user)
    
    assert result["message"] == "Submission queued for reprocessing"


@pytest.mark.asyncio
async def test_get_submission_analytics(mock_editor_user, mock_db):
    """Test getting submission analytics"""
    mock_analytics = [
        {"_id": "2024-12-01", "count": 5, "completed": 3, "failed": 1},
        {"_id": "2024-12-02", "count": 8, "completed": 6, "failed": 0},
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_analytics)
    mock_db.submissions.aggregate = MagicMock(return_value=mock_cursor)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await get_submission_analytics(mock_editor_user, days=30)
    
    assert len(result["analytics"]) == 2
    assert result["period_days"] == 30


@pytest.mark.asyncio
async def test_get_domain_distribution(mock_editor_user, mock_db):
    """Test getting domain distribution"""
    mock_domains = [
        {"_id": "Computer Science", "count": 45},
        {"_id": "Medical Sciences", "count": 32},
        {"_id": "Psychology", "count": 18},
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_domains)
    mock_db.submissions.aggregate = MagicMock(return_value=mock_cursor)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await get_domain_distribution(mock_editor_user)
    
    assert len(result["domains"]) == 3
    assert result["domains"][0]["_id"] == "Computer Science"
    assert result["domains"][0]["count"] == 45


@pytest.mark.asyncio
async def test_get_review_performance(mock_editor_user, mock_db):
    """Test getting review performance metrics"""
    mock_performance = [
        {
            "_id": None,
            "avg_time_ms": 180000,
            "min_time_ms": 120000,
            "max_time_ms": 300000,
            "total_reviews": 125,
        }
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_performance)
    mock_db.submissions.aggregate = MagicMock(return_value=mock_cursor)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await get_review_performance(mock_editor_user)
    
    assert result["performance"]["avg_time_ms"] == 180000
    assert result["performance"]["total_reviews"] == 125


@pytest.mark.asyncio
async def test_require_editor_with_admin(mock_db):
    """Test that admin can access editor dashboard"""
    from app.api.editor_dashboard_routes import require_editor
    
    admin_user = {
        "user_id": "admin123",
        "role": UserRole.ADMIN.value,
    }
    
    # Should not raise exception
    result = require_editor(admin_user)
    assert result == admin_user


@pytest.mark.asyncio
async def test_require_editor_with_author():
    """Test that author cannot access editor dashboard"""
    from app.api.editor_dashboard_routes import require_editor
    
    author_user = {
        "user_id": "author123",
        "role": UserRole.AUTHOR.value,
    }
    
    with pytest.raises(HTTPException) as exc_info:
        require_editor(author_user)
    
    assert exc_info.value.status_code == 403
    assert "Editor access required" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_editorial_decision_validation():
    """Test editorial decision model validation"""
    from app.api.editor_dashboard_routes import EditorialDecision
    
    # Valid decision
    decision = EditorialDecision(
        decision="accept",
        comments="Well written",
        notify_author=True,
    )
    assert decision.decision == "accept"
    assert decision.notify_author is True
    
    # Default notify_author
    decision2 = EditorialDecision(
        decision="reject",
        comments="Needs improvement",
    )
    assert decision2.notify_author is True


@pytest.mark.asyncio
async def test_filtering_by_status(mock_editor_user, mock_db):
    """Test filtering submissions by status"""
    mock_submissions = [
        {"_id": "sub1", "status": "completed"},
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=mock_submissions)
    
    mock_db.submissions.find = MagicMock(return_value=mock_cursor)
    mock_db.submissions.count_documents = AsyncMock(return_value=1)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await list_all_submissions(
            mock_editor_user,
            skip=0,
            limit=50,
            status="completed",
        )
    
    # Verify find was called with status filter
    call_args = mock_db.submissions.find.call_args[0][0]
    assert call_args["status"] == "completed"


@pytest.mark.asyncio
async def test_filtering_by_domain(mock_editor_user, mock_db):
    """Test filtering submissions by domain"""
    mock_submissions = [
        {"_id": "sub1", "detected_domain": "Computer Science"},
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=mock_submissions)
    
    mock_db.submissions.find = MagicMock(return_value=mock_cursor)
    mock_db.submissions.count_documents = AsyncMock(return_value=1)
    
    with patch("app.api.editor_dashboard_routes.mongodb_service.get_database", return_value=mock_db):
        result = await list_all_submissions(
            mock_editor_user,
            skip=0,
            limit=50,
            domain="Computer Science",
        )
    
    # Verify find was called with domain filter
    call_args = mock_db.submissions.find.call_args[0][0]
    assert call_args["detected_domain"] == "Computer Science"
