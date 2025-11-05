"""Tests for Reviewer Dashboard functionality"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId


@pytest.fixture
def reviewer_user():
    """Mock reviewer user"""
    return {
        "user_id": "reviewer123",
        "email": "reviewer@test.com",
        "name": "Test Reviewer",
        "role": "reviewer",
    }


@pytest.fixture
def mock_assignment():
    """Mock review assignment"""
    return {
        "_id": ObjectId(),
        "submission_id": str(ObjectId()),
        "reviewer_id": "reviewer123",
        "status": "pending",
        "assigned_at": datetime.now(),
        "due_date": datetime.now() + timedelta(days=7),
    }


@pytest.fixture
def mock_submission():
    """Mock submission"""
    return {
        "_id": ObjectId(),
        "title": "Test Manuscript",
        "content": "Test content",
        "detected_domain": "Computer Science",
        "status": "completed",
    }


class TestReviewerDashboardStats:
    """Test reviewer dashboard statistics endpoint"""

    @pytest.mark.asyncio
    async def test_get_reviewer_stats_success(self, reviewer_user):
        """Test successful retrieval of reviewer statistics"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            # Mock count_documents
            mock_db_instance.review_assignments.count_documents = AsyncMock(
                side_effect=[10, 3, 2, 5]
            )

            # Mock aggregate for average time
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[{"avg_time_ms": 86400000}])  # 24 hours
            mock_db_instance.review_assignments.aggregate = MagicMock(return_value=mock_cursor)

            from app.api.reviewer_dashboard_routes import get_reviewer_stats

            result = await get_reviewer_stats(reviewer_user)

            assert result["total_assigned"] == 10
            assert result["pending_reviews"] == 3
            assert result["in_progress"] == 2
            assert result["completed_reviews"] == 5
            assert abs(result["avg_review_time_hours"] - 24.0) < 0.01

    @pytest.mark.asyncio
    async def test_get_reviewer_stats_no_completed(self, reviewer_user):
        """Test stats when no reviews completed"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            mock_db_instance.review_assignments.count_documents = AsyncMock(
                side_effect=[5, 5, 0, 0]
            )

            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db_instance.review_assignments.aggregate = MagicMock(return_value=mock_cursor)

            from app.api.reviewer_dashboard_routes import get_reviewer_stats

            result = await get_reviewer_stats(reviewer_user)

            assert result["avg_review_time_hours"] == 0


class TestReviewerAssignments:
    """Test reviewer assignments endpoints"""

    @pytest.mark.asyncio
    async def test_get_assignments_success(self, reviewer_user, mock_assignment, mock_submission):
        """Test successful retrieval of assignments"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            # Mock find
            mock_cursor = MagicMock()
            mock_cursor.sort = MagicMock(return_value=mock_cursor)
            mock_cursor.skip = MagicMock(return_value=mock_cursor)
            mock_cursor.limit = MagicMock(return_value=mock_cursor)
            mock_cursor.to_list = AsyncMock(return_value=[mock_assignment])
            mock_db_instance.review_assignments.find = MagicMock(return_value=mock_cursor)

            # Mock count
            mock_db_instance.review_assignments.count_documents = AsyncMock(return_value=1)

            # Mock submission lookup
            mock_db_instance.submissions.find_one = AsyncMock(return_value=mock_submission)

            from app.api.reviewer_dashboard_routes import get_reviewer_assignments

            result = await get_reviewer_assignments(reviewer_user, skip=0, limit=20, status=None)

            assert result["total"] == 1
            assert len(result["assignments"]) == 1
            assert result["assignments"][0]["submission_title"] == "Test Manuscript"

    @pytest.mark.asyncio
    async def test_get_assignments_with_status_filter(self, reviewer_user):
        """Test assignments with status filter"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            mock_cursor = MagicMock()
            mock_cursor.sort = MagicMock(return_value=mock_cursor)
            mock_cursor.skip = MagicMock(return_value=mock_cursor)
            mock_cursor.limit = MagicMock(return_value=mock_cursor)
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db_instance.review_assignments.find = MagicMock(return_value=mock_cursor)
            mock_db_instance.review_assignments.count_documents = AsyncMock(return_value=0)

            from app.api.reviewer_dashboard_routes import get_reviewer_assignments

            _ = await get_reviewer_assignments(reviewer_user, skip=0, limit=20, status="pending")

            # Verify status filter was applied
            call_args = mock_db_instance.review_assignments.find.call_args[0][0]
            assert call_args["status"] == "pending"


class TestReviewActions:
    """Test review action endpoints"""

    @pytest.mark.asyncio
    async def test_start_review_success(self, reviewer_user, mock_assignment):
        """Test successfully starting a review"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            mock_result = MagicMock()
            mock_result.matched_count = 1
            mock_db_instance.review_assignments.update_one = AsyncMock(return_value=mock_result)

            from app.api.reviewer_dashboard_routes import start_review

            assignment_id = str(mock_assignment["_id"])
            await start_review(assignment_id, reviewer_user)

    @pytest.mark.asyncio
    async def test_start_review_not_found(self, reviewer_user):
        """Test starting review that doesn't exist"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            mock_result = MagicMock()
            mock_result.matched_count = 0
            mock_db_instance.review_assignments.update_one = AsyncMock(return_value=mock_result)

            from fastapi import HTTPException

            from app.api.reviewer_dashboard_routes import start_review

            with pytest.raises(HTTPException) as exc_info:
                await start_review(str(ObjectId()), reviewer_user)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_review_success(self, reviewer_user, mock_assignment):
        """Test successfully submitting a review"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            # Mock find_one for assignment lookup
            mock_db_instance.review_assignments.find_one = AsyncMock(return_value=mock_assignment)

            # Mock update_one for submission
            mock_result = MagicMock()
            mock_result.modified_count = 1
            mock_db_instance.review_assignments.update_one = AsyncMock(return_value=mock_result)

            from app.api.reviewer_dashboard_routes import submit_review

            review_data = {
                "methodology_score": 8,
                "literature_score": 7,
                "clarity_score": 9,
                "ethics_score": 8,
                "overall_score": 8,
                "strengths": "Well-designed study",
                "weaknesses": "Minor issues",
                "comments": "Good work overall",
                "recommendation": "revise",
            }

            assignment_id = str(mock_assignment["_id"])
            await submit_review(assignment_id, review_data, reviewer_user)

    @pytest.mark.asyncio
    async def test_submit_review_already_completed(self, reviewer_user, mock_assignment):
        """Test submitting review that's already completed"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            completed_assignment = mock_assignment.copy()
            completed_assignment["status"] = "completed"
            mock_db_instance.review_assignments.find_one = AsyncMock(
                return_value=completed_assignment
            )

            from fastapi import HTTPException

            from app.api.reviewer_dashboard_routes import submit_review

            review_data = {"recommendation": "accept"}

            with pytest.raises(HTTPException) as exc_info:
                await submit_review(str(mock_assignment["_id"]), review_data, reviewer_user)

            assert exc_info.value.status_code == 400


class TestReviewerAnalytics:
    """Test reviewer analytics endpoints"""

    @pytest.mark.asyncio
    async def test_get_review_timeline(self, reviewer_user):
        """Test review timeline analytics"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            timeline_data = [{"_id": "2024-01-15", "count": 2}, {"_id": "2024-01-16", "count": 1}]

            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=timeline_data)
            mock_db_instance.review_assignments.aggregate = MagicMock(return_value=mock_cursor)

            from app.api.reviewer_dashboard_routes import get_review_timeline

            result = await get_review_timeline(reviewer_user, days=30)

            assert result["period_days"] == 30
            assert len(result["timeline"]) == 2

    @pytest.mark.asyncio
    async def test_get_review_domains(self, reviewer_user, mock_assignment, mock_submission):
        """Test domain distribution analytics"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[mock_assignment])
            mock_db_instance.review_assignments.find = MagicMock(return_value=mock_cursor)

            mock_db_instance.submissions.find_one = AsyncMock(return_value=mock_submission)

            from app.api.reviewer_dashboard_routes import get_review_domains

            result = await get_review_domains(reviewer_user)

            assert len(result["domains"]) > 0
            assert result["domains"][0]["_id"] == "Computer Science"

    @pytest.mark.asyncio
    async def test_get_reviewer_performance(self, reviewer_user):
        """Test performance metrics"""
        with patch("app.api.reviewer_dashboard_routes.mongodb_service") as mock_db:
            mock_db.get_database = AsyncMock()
            mock_db_instance = MagicMock()
            mock_db.get_database.return_value = mock_db_instance

            performance_data = {
                "avg_time_ms": 86400000,
                "min_time_ms": 43200000,
                "max_time_ms": 172800000,
            }

            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[performance_data])
            mock_db_instance.review_assignments.aggregate = MagicMock(return_value=mock_cursor)

            from app.api.reviewer_dashboard_routes import get_reviewer_performance

            result = await get_reviewer_performance(reviewer_user)

            assert result["performance"]["avg_time_ms"] == 86400000


class TestAccessControl:
    """Test role-based access control"""

    @pytest.mark.asyncio
    async def test_require_reviewer_with_reviewer_role(self):
        """Test access with reviewer role"""
        from app.api.reviewer_dashboard_routes import require_reviewer

        user = {"user_id": "test", "role": "reviewer"}
        result = await require_reviewer(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_require_reviewer_with_editor_role(self):
        """Test access with editor role"""
        from app.api.reviewer_dashboard_routes import require_reviewer

        user = {"user_id": "test", "role": "editor"}
        result = await require_reviewer(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_require_reviewer_with_author_role(self):
        """Test access denied for author role"""
        from fastapi import HTTPException

        from app.api.reviewer_dashboard_routes import require_reviewer

        user = {"user_id": "test", "role": "author"}

        with pytest.raises(HTTPException) as exc_info:
            await require_reviewer(user)

        assert exc_info.value.status_code == 403
