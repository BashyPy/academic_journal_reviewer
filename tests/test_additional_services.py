"""More tests for coverage"""

# pylint: disable=import-outside-toplevel,protected-access,no-member,too-few-public-methods
# pylint: disable=no-name-in-module

from io import BytesIO
from unittest.mock import patch

import pytest


class TestDocumentParser:
    """Test document parser service"""

    def test_parse_pdf(self, sample_pdf_content):
        from app.services.document_parser import document_parser

        r = document_parser.parse_document(sample_pdf_content, "test.pdf")
        assert "content" in r

    def test_parse_docx(self, sample_docx_content):
        from app.services.document_parser import document_parser

        r = document_parser.parse_document(sample_docx_content, "test.docx")
        assert "content" in r

    def test_detect_file_type(self):
        from app.services.document_parser import document_parser

        assert document_parser._detect_file_type(b"%PDF", "test.pdf") == "pdf"

    def test_extract_pdf_text(self, sample_pdf_content):
        from app.services.document_parser import document_parser

        t = document_parser._extract_text_from_pdf(BytesIO(sample_pdf_content))
        assert isinstance(t, str)


class TestDomainDetector:
    """Test domain detector service"""

    def test_detect_domain(self):
        from app.services.domain_detector import domain_detector

        d = domain_detector.detect_domain("machine learning algorithm neural network")
        assert d is not None

    def test_get_weights(self):
        from app.services.domain_detector import domain_detector

        w = domain_detector.get_domain_weights("medical")
        assert "methodology" in w

    def test_extract_keywords(self):
        from app.services.domain_detector import domain_detector

        k = domain_detector._extract_keywords("test text with keywords")
        assert isinstance(k, list)


class TestPDFGenerator:
    """Test PDF generator service"""

    def test_generate_pdf(self):
        from app.services.pdf_generator import pdf_generator

        sub = {"title": "Test", "file_metadata": {"original_filename": "test.pdf"}}
        pdf = pdf_generator.generate_review_pdf(sub, "# Report\nTest content")
        assert pdf is not None


class TestIssueDeduplicator:
    """Test issue deduplicator service"""

    def test_deduplicate(self):
        from app.services.issue_deduplicator import issue_deduplicator

        issues = [{"issue": "Test 1"}, {"issue": "Test 1"}, {"issue": "Test 2"}]
        r = issue_deduplicator.deduplicate(issues)
        assert len(r) <= len(issues)

    def test_similarity(self):
        from app.services.issue_deduplicator import issue_deduplicator

        s = issue_deduplicator._calculate_similarity("test", "test")
        assert abs(s - 1.0) < 0.01


class TestAuthMiddleware:
    """Test auth middleware"""

    @pytest.mark.asyncio
    async def test_verify_api_key(self):
        from app.middleware.auth import verify_api_key

        with patch("app.services.user_service.user_service.get_user_by_api_key") as m:
            m.return_value = {"email": "a@b.com", "active": True, "email_verified": True}
            r = await verify_api_key("key")
            assert r is not None


class TestPermissions:
    """Test permissions middleware"""

    def test_check_permission(self):
        from app.middleware.permissions import check_permission

        assert check_permission({"role": "admin"}, "manage_users")

    def test_require_permission(self):
        from app.middleware.permissions import require_permission

        decorator = require_permission("view_submissions")
        assert decorator is not None


class TestRoles:
    """Test roles model"""

    def test_role_permissions(self):
        from app.models.roles import Role, get_role_permissions, has_permission

        perms = get_role_permissions(Role.ADMIN)
        assert "manage_users" in perms
        assert has_permission(Role.ADMIN, "manage_users")


class TestConfig:
    """Test configuration"""

    def test_get_llm_config(self):
        from app.core.config import settings

        c = settings.get_llm_config("openai")
        assert c is not None


class TestLogger:
    """Test logger utility"""

    def test_all_levels(self):
        from app.utils.logger import get_logger

        logger = get_logger("test")
        logger.info("info")
        logger.warning("warn")
        logger.error(Exception("err"))
        logger.info("data", additional_info={"k": "v"})


class TestDisclaimerService:
    """Test disclaimer service"""

    def test_get_disclaimers(self):
        from app.services.disclaimer_service import disclaimer_service

        api = disclaimer_service.get_api_disclaimer()
        assert "disclaimer" in api
        ui = disclaimer_service.get_ui_disclaimer()
        assert "title" in ui


class TestRequestSigning:
    """Test request signing middleware"""

    def test_generate_signature(self):
        from app.middleware.request_signing import generate_signature

        s = generate_signature("data", "secret")
        assert len(s) > 0

    def test_verify_signature(self):
        from app.middleware.request_signing import generate_signature, verify_signature

        sig = generate_signature("data", "secret")
        assert verify_signature("data", sig, "secret")
